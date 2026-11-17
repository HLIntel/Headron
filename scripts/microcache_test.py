"""The content cache: a hit needs the same program object, version and context, and is a fresh copy of an "ok" result.

Run by microprogram_test.py (run_never_raises_cases). Each planted program counts its real runs, so a hit is seen as a
run that did not happen.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping
from decimal import Decimal
from typing import Any
from unittest import mock

import effects
import microprogram

NAME = "cache.planted"


class _Counting:
    name = NAME
    version = "1"
    timeout_s = 5.0

    def __init__(self, declared: effects.Declared = effects.PURE, status: str = "ok", sleep: float = 0.0) -> None:
        self.declared, self.status, self.sleep, self.runs = declared, status, sleep, 0

    def run(self, context: Mapping[str, Any]) -> microprogram.MicroResult:
        self.runs += 1
        threading.Event().wait(self.sleep)  # a hung step: nothing ever sets it
        answer = {"seen": repr(sorted(context.items(), key=repr)), "rows": [1, 2]}
        nxt = None if self.status == "ok" else "planted"
        return microprogram.MicroResult(self.name, self.version, self.status, answer, next=nxt)


def _fail(what: str) -> None:
    raise SystemExit(f"FAIL microcache: {what}")


def _runs(program: _Counting, *contexts: Mapping[str, Any]) -> list[microprogram.MicroResult]:
    with mock.patch.dict(microprogram.REGISTRY, {NAME: program}):
        return [microprogram.run(NAME, c) for c in contexts]


def run_cases() -> None:
    microprogram.cache_clear()
    try:
        pure = _Counting()
        first, hit = _runs(pure, {"x": 1}, {"x": 1})
        if pure.runs != 1:
            _fail(f"the same context ran {pure.runs} times; a PURE program's second run was not served")
        if {**first.to_dict(), "elapsed_ms": 0} != {**hit.to_dict(), "elapsed_ms": 0}:
            _fail("a hit differs from the miss it reuses")
        hit.output["rows"].append(3)
        if _runs(pure, {"x": 1})[0].output["rows"] != [1, 2]:
            _fail("changing a hit's output changed the next hit")
        _runs(pure, {"x": 2})
        if pure.runs != 2:
            _fail("a different context was served from the cache")
        pure.version = "2"
        _runs(pure, {"x": 1})
        if pure.runs != 3:
            _fail("a new version was served the old version's answer")
        for left, right in (({"x": Decimal("1")}, {"x": "1"}), ({1: "a"}, {"1": "a"}), ({"x": (1,)}, {"x": [1]})):
            fresh = _Counting()
            a, b = _runs(fresh, left, right)
            if fresh.runs != 2 or a.output == b.output:
                _fail(f"{left!r} and {right!r} were merged into one cache entry")
        writes = _Counting(effects.Declared({"write"}, deterministic=True, cache_policy="content"))
        _runs(writes, {"x": 1}, {"x": 1})
        if writes.runs != 2:
            _fail("a program declaring effects was served from the cache")
        for program in (_Counting(status="refused"), _Counting(sleep=0.3)):
            program.timeout_s = 0.05
            _runs(program, {"x": 1}, {"x": 1})
            if program.runs != 2:
                _fail(f"a {program.status!r}/timed-out result was served from the cache")
        other = _Counting()
        _runs(other, {"x": 2})
        if other.runs != 1:
            _fail("another program object with the same name and version was served the first one's answer")
    finally:
        microprogram.cache_clear()


if __name__ == "__main__":
    run_cases()
    print("microcache: PASS")
