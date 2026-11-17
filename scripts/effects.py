#!/usr/bin/env python3
"""What a microprogram may do besides compute: its declared effects, enforced while it runs.

Each registered program declares a `declared = Declared(...)`:
  effects       which of EFFECTS it may cause; empty means it is pure over the context it is handed
  capabilities  the executables it may start; required with "spawn", and nothing else may be started
  deterministic the same context gives the same output
  cache_policy  "none", or "content": a result may be reused for the same context. Legal only for a
                deterministic program with no effects, so a reused answer cannot hide a write or a stale read.

scope(program) runs on the program's own worker thread. An interpreter audit hook (sys.addaudithook) maps
each write, spawn and network event to its effect and raises Undeclared for one the program did not declare,
so the event does not happen. A violation the program catches and swallows is raised again when the scope
closes, so it still ends the run. A program that declares nothing is held to no effects at all.

proves: a program cannot write a file, start a process or open a connection it did not declare, from the
  thread it runs on; declarations are checked for shape and for consistency (validate)
does_not_prove: anything about "read" (every lazy import reads files, so it is declared for later cache keys,
  not blocked); work on threads or processes the program starts (the hook sees only its own thread, and a
  started process runs outside the interpreter); that a "deterministic" program is (the tests run each one
  twice); writes through a C extension that raises no audit event
closed_by: scripts/effects_test.py, which plants an undeclared write, spawn, connect, a swallowed violation,
  an executable outside the capabilities and each inconsistent declaration
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
from collections.abc import Iterator
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from threading import local
from typing import Any

EFFECTS: dict[str, str] = {
    "read": "reads files or state beyond the context it is handed (declared, not enforced)",
    "write": "creates, changes or deletes a file or directory",
    "spawn": "starts a process; only the executables named in capabilities",
    "net": "opens a network connection or resolves a host",
}
ENFORCED = frozenset({"write", "spawn", "net"})
CACHE_POLICIES: dict[str, str] = {
    "none": "never reuse a result",
    "content": "reuse a result for the same program, version and context",
}

_WRITE_BITS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_WRITE_EVENTS = frozenset(
    {
        "os.remove",
        "os.rmdir",
        "os.mkdir",
        "os.rename",
        "os.truncate",
        "os.symlink",
        "os.link",
        "os.chmod",
        "shutil.rmtree",
    }
)
_NET_EVENTS = frozenset({"socket.connect", "socket.getaddrinfo", "socket.sendto"})


@dataclass(frozen=True)
class Declared:
    # Any set of names is accepted and stored as a frozenset; a bare string is refused (it would split into letters).
    effects: AbstractSet[str] = field(default_factory=frozenset)
    capabilities: AbstractSet[str] = field(default_factory=frozenset)
    deterministic: bool = False
    cache_policy: str = "none"

    def __post_init__(self) -> None:
        for name in ("effects", "capabilities"):
            value = getattr(self, name)
            if isinstance(value, str):
                raise TypeError(f"{name} takes a collection of names, not the string {value!r}")
            object.__setattr__(self, name, frozenset(value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "effects": sorted(self.effects),
            "capabilities": sorted(self.capabilities),
            "deterministic": self.deterministic,
            "cache_policy": self.cache_policy,
        }


PURE = Declared(deterministic=True, cache_policy="content")


class Undeclared(PermissionError):
    """A program caused an effect it did not declare. The event was refused."""


def declared_of(program: object) -> Declared:
    """The program's declaration; a program that declares nothing may cause no effect."""
    found = getattr(program, "declared", None)
    return found if isinstance(found, Declared) else Declared()


def validate(program: object) -> list[str]:
    """Each way the program's declaration is missing or contradicts itself; empty when it is sound."""
    name = getattr(program, "name", type(program).__name__)
    found = getattr(program, "declared", None)
    if not isinstance(found, Declared):
        return [f"{name}: declares no effects (set declared = effects.Declared(...))"]
    problems = [f"{name}: unknown effect {e!r}; known: {sorted(EFFECTS)}" for e in sorted(found.effects - set(EFFECTS))]
    if found.cache_policy not in CACHE_POLICIES:
        problems.append(f"{name}: unknown cache_policy {found.cache_policy!r}; known: {sorted(CACHE_POLICIES)}")
    if ("spawn" in found.effects) != bool(found.capabilities):
        problems.append(
            f"{name}: spawn and capabilities go together; effects {sorted(found.effects)}, "
            f"capabilities {sorted(found.capabilities)}"
        )
    if found.cache_policy == "content" and (found.effects or not found.deterministic):
        problems.append(
            f"{name}: cache_policy content needs a deterministic program with no effects; "
            f"deterministic={found.deterministic}, effects {sorted(found.effects)}"
        )
    return problems


@dataclass
class _Scope:
    program: str
    declared: Declared
    enforce: bool
    observed: list[tuple[str, str]] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)


class _Active(local):
    # A class default, so a thread with no scope reads None. getattr(..., None) on a missing thread-local
    # attribute raises and catches AttributeError inside the hook, about 600ns on every audit event of every
    # thread once the hook is installed.
    scope: _Scope | None = None


_ACTIVE = _Active()
_INSTALL_LOCK = threading.Lock()
_installed = False


def _exempt(path: object) -> bool:
    # The null device subprocess opens read-write for DEVNULL.
    text = os.fsdecode(path) if isinstance(path, (str, bytes, os.PathLike)) else ""
    return text == os.devnull


def classify(event: str, args: tuple[Any, ...]) -> tuple[str, str, str] | None:
    """(effect, executable or "", detail) for an audit event that is a write, spawn or network effect; else None."""
    if event == "open":
        path, mode, flags = (tuple(args) + (None, None, None))[:3]
        writes = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and bool(flags & _WRITE_BITS)
        )
        if writes and isinstance(path, (str, bytes, os.PathLike)) and not _exempt(path):
            return "write", "", f"open {os.fsdecode(path)} {mode or flags}"
        return None
    if event in _WRITE_EVENTS:
        target = args[0] if args else ""
        if _exempt(target) or (event == "os.rename" and len(args) > 1 and _exempt(args[1])):
            return None
        return "write", "", f"{event} {target}"
    if event == "subprocess.Popen":
        executable, argv = args[0], args[1]
        first = executable or (argv if isinstance(argv, (str, bytes)) else (list(argv) or [""])[0])
        exe = os.path.basename(os.fsdecode(first).split()[0]) if first else ""
        return "spawn", exe, f"start {exe}"
    if event in ("os.posix_spawn", "os.exec", "os.spawn"):
        exe = os.path.basename(os.fsdecode(args[0])) if args else ""
        return "spawn", exe, f"{event} {exe}"
    if event == "os.system":
        exe = os.path.basename(str(args[0]).split()[0]) if args and str(args[0]).split() else ""
        return "spawn", exe, f"os.system {exe}"
    if event == "os.fork":
        return "spawn", "fork", "os.fork"
    if event in _NET_EVENTS:
        return "net", "", f"{event} {args[1] if event == 'socket.connect' and len(args) > 1 else args[:1]}"
    return None


def _hook(event: str, args: tuple[Any, ...]) -> None:
    scope = _ACTIVE.scope
    if scope is None:
        return
    found = classify(event, args)
    if found is None:
        return
    effect, exe, detail = found
    scope.observed.append((effect, detail))
    if not scope.enforce:
        return
    allowed = effect in scope.declared.effects and (effect != "spawn" or exe in scope.declared.capabilities)
    if allowed:
        return
    why = (
        f"{scope.program} may start only {sorted(scope.declared.capabilities)}; refused {detail}"
        if effect == "spawn" and effect in scope.declared.effects
        else f"{scope.program} declares effects {sorted(scope.declared.effects)}; refused undeclared {effect}: {detail}"
    )
    scope.violations.append(why)
    raise Undeclared(why)


def install() -> None:
    """Add the audit hook once per process. It cannot be removed; on a thread with no scope it returns at once."""
    global _installed
    with _INSTALL_LOCK:
        if not _installed:
            sys.addaudithook(_hook)
            _installed = True


@contextlib.contextmanager
def scope(program: object, enforce: bool = True) -> Iterator[_Scope]:
    """Hold the current thread to the program's declared effects until the block ends.

    With enforce=False it only records what the program did (scope.observed), for measuring a declaration.
    """
    install()
    current = _Scope(str(getattr(program, "name", type(program).__name__)), declared_of(program), enforce)
    outer = _ACTIVE.scope
    _ACTIVE.scope = current
    try:
        yield current
    finally:
        _ACTIVE.scope = outer
    # Reached only when the block did not raise: a violation the program caught must still end the run.
    if current.violations:
        raise Undeclared(current.violations[0])
