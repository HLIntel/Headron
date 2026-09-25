#!/usr/bin/env python3
"""Retry what can succeed, refuse what cannot, and never hammer what is down.

WHY (2.27.0). This repository's documents already said it — patterns/NO-UNBOUNDED.md,
systems/OPERATIONS-UPTIME.md, docs/ENGINEERING-CONCEPTS.md XIV — and its own network code did
none of it. abtest.py abandoned a whole model on ONE timeout, which is how the `deep` arm went
unmeasured. A doctrine the harness does not practise is a declared control with no enforcer.

THE CLASSIFICATION IS THE WHOLE DESIGN, and it has three answers, not two:

  transient   the next attempt can succeed — 408, 425, 429, 5xx except 501, timeouts, resets
  terminal    no retry can change it — 4xx, 501, a malformed answer
  exhausted   402: the WINDOW's budget is gone. Retrying is not slow, it is wasted, and the
              breaker LATCHES rather than cooling down. A 402 is not a 429.

Branches on the declared status code, never on an error message — a message is a rendering.

WHAT IT DOES NOT PROVE. That siblings back off. The breaker is per process, and a vendor sees
the SUM of every process on one credential; publishing a throttle where siblings read it is the
caller's job. It also does not make a non-idempotent call safe to retry — only retry calls whose
repetition is harmless, which is why this takes a function and never wraps a mutation silently.
"""
from __future__ import annotations

import email.utils
import random
import socket
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

TRANSIENT_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
EXHAUSTED_STATUS = frozenset({402})
TRANSIENT_ERRORS = (TimeoutError, socket.timeout, ConnectionError)


class BreakerOpen(RuntimeError):
    """Refused without touching the network: the dependency failed repeatedly, or its budget is gone."""


def classify(status: int | None = None, error: BaseException | None = None) -> str:
    """transient | terminal | exhausted — from a status code, or from an exception carrying one."""
    if status is None and error is not None:
        status = getattr(error, "code", None) or getattr(error, "status", None)
        reason = getattr(error, "reason", None)
        if status is None and isinstance(reason, BaseException):
            error = reason  # urllib wraps a socket timeout inside URLError.reason
    if isinstance(status, int):
        if status in EXHAUSTED_STATUS:
            return "exhausted"
        if status in TRANSIENT_STATUS or (500 <= status < 600 and status != 501):
            return "transient"
        return "terminal"
    return "transient" if isinstance(error, TRANSIENT_ERRORS) else "terminal"


def retry_after(headers: object, cap: float) -> float | None:
    """Seconds the server ASKED for, bounded by `cap`, or None when it asked for nothing usable.

    A server that names its own recovery time knows more than any backoff curve, so it wins.
    Both forms are read — delta-seconds and an HTTP date — and a date in the past means now.
    """
    raw = headers.get("Retry-After") if hasattr(headers, "get") else None
    if not raw:
        return None
    text = str(raw).strip()
    if text.isdigit():
        return min(cap, float(text))
    try:
        when = email.utils.parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    return min(cap, max(0.0, when.timestamp() - time.time()))


def backoff(previous: float, base: float, cap: float, rng: random.Random) -> float:
    """Decorrelated jitter: uniform(base, previous * 3), capped. Retries spread instead of
    arriving as a synchronised wave, which is what knocks a recovering service down again."""
    return min(cap, rng.uniform(base, max(base, previous * 3)))


class Breaker:
    """closed -> open after `threshold` consecutive failures -> half-open after `cooldown`.

    An `exhausted` failure LATCHES it open for the life of the process: the budget returns with
    the window, not after a cooldown, and a half-open probe would spend nothing but credibility.
    """

    def __init__(self, threshold: int, cooldown: float, clock: Callable[[], float] = time.monotonic):
        self.threshold, self.cooldown, self.clock = threshold, cooldown, clock
        self.failures, self.opened_at, self.latched = 0, None, False

    @property
    def state(self) -> str:
        if self.latched:
            return "latched"
        if self.opened_at is None:
            return "closed"
        return "half-open" if self.clock() - self.opened_at >= self.cooldown else "open"

    def allow(self) -> bool:
        return self.state in ("closed", "half-open")

    def record(self, kind: str) -> None:
        """`ok`, or the classification of the failure."""
        if kind == "ok":
            self.failures, self.opened_at = 0, None
            return
        if kind == "exhausted":
            self.latched = True
            return
        self.failures += 1
        if self.failures >= self.threshold or self.state == "half-open":
            self.opened_at = self.clock()


def call(fn: Callable[[], T], *, attempts: int, base: float, cap: float, deadline: float,
         breaker: Breaker | None = None, sleep: Callable[[float], None] = time.sleep,
         rng: random.Random | None = None, clock: Callable[[], float] = time.monotonic) -> T:
    """Run `fn`, retrying ONLY transient failures, within `attempts` AND a wall `deadline`.

    Two bounds, because either alone is unbounded in the other unit: many fast attempts, or a few
    that each sleep for a server's generous Retry-After. A terminal or exhausted failure is
    raised on first sight — retrying it spends the budget the NEXT caller needed.
    """
    rng = rng or random.Random()  # noqa: S311 — jitter, not cryptography
    started, delay, last = clock(), base, None
    for attempt in range(1, attempts + 1):
        if breaker is not None and not breaker.allow():
            raise BreakerOpen(f"breaker {breaker.state}: refused without calling") from last
        try:
            result = fn()
        except Exception as exc:  # classified below; nothing is swallowed
            kind = classify(error=exc)
            if breaker is not None:
                breaker.record(kind)
            if kind != "transient" or attempt == attempts:
                raise
            asked = retry_after(getattr(exc, "headers", None), cap)
            delay = asked if asked is not None else backoff(delay, base, cap, rng)
            if clock() - started + delay > deadline:
                raise
            last = exc
            sleep(delay)
            continue
        if breaker is not None:
            breaker.record("ok")
        return result
    raise RuntimeError("unreachable: the loop returns or raises on its last attempt")
