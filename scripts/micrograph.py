"""A DAG of microprogram steps: run each node once its needs answered ok, within its own and a total budget.

Headron's CI is this graph over its job units (scripts/cipipeline.py, run by scripts/cilocal.py). The graph
never decides what a node does; `start` does. It decides only WHEN a node may start and what a node that never
finished answers, and every such answer fails closed:
  - a node whose need answered anything but ok answers unknown, "blocked by <need>", and never starts;
  - a node past its own timeout_s is stopped and answers unknown, never a pass;
  - once the total budget is spent, every running node is stopped and every waiting one answers unknown.
At most `width` nodes run at once; past the first, a start also needs `admit()` (the machine's spare cores),
so a loaded machine runs them one at a time and still finishes.

proves: a node starts only after every need answered ok, and no node that did not finish reads as ok
does_not_prove: that a node's own answer is right; that is the node's own instrument
closed_by: cilocal_test.py, which plants a cycle, a failed need, a hung node, a spent budget and a loaded machine
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from microprogram import MicroResult


@dataclass(frozen=True)
class Node:
    name: str
    needs: tuple[str, ...] = ()
    timeout_s: float = 0.0


class Running(Protocol):
    """A started node: `poll` is its answer once it has one, `stop` ends it early."""

    def poll(self) -> MicroResult | None: ...

    def stop(self) -> None: ...


def problems(nodes: Sequence[Node]) -> list[str]:
    """Every way the nodes are not a runnable DAG; empty when they are."""
    names = [node.name for node in nodes]
    found = [f"{name!r} declared twice" for name in sorted({n for n in names if names.count(n) > 1})]
    known = set(names)
    for node in nodes:
        found += [f"{node.name} needs undeclared {need!r}" for need in node.needs if need not in known]
        if not node.timeout_s > 0:
            found.append(f"{node.name}: timeout_s {node.timeout_s:g} is not positive; no node runs unbounded")
    by_name = {node.name: node for node in nodes}
    state: dict[str, int] = {}

    def visit(name: str, path: tuple[str, ...]) -> None:
        if state.get(name) == 2 or name not in by_name:
            return
        if state.get(name) == 1:
            found.append("cycle: " + " -> ".join((*path, name)))
            return
        state[name] = 1
        for need in by_name[name].needs:
            visit(need, (*path, name))
        state[name] = 2

    for name in names:
        visit(name, ())
    return found


def order(nodes: Sequence[Node]) -> list[str]:
    """Every node after its needs; among nodes ready together, the declared order."""
    done: list[str] = []
    left = list(nodes)
    while left:
        ready = next(node for node in left if all(need in done for need in node.needs))
        done.append(ready.name)
        left.remove(ready)
    return done


def _unknown(name: str, why: str, next_step: str, elapsed_s: float = 0.0) -> MicroResult:
    return MicroResult(name, "1", "unknown", why, evidence_refs=(why,), next=next_step, elapsed_ms=elapsed_s * 1000)


def run(
    nodes: Sequence[Node],
    start: Callable[[Node, float], Running],
    *,
    budget_s: float,
    width: int = 1,
    admit: Callable[[], bool] = lambda: True,
    clock: Callable[[], float] = time.monotonic,
    wait: Callable[[float], object] = time.sleep,
    poll_s: float = 0.2,
) -> dict[str, MicroResult]:
    """Each node's answer, in declared order. `start(node, timeout_s)` begins one; the graph polls it."""
    if found := problems(nodes):
        raise ValueError("not a runnable DAG: " + "; ".join(found))
    if width < 1 or not budget_s > 0:
        raise ValueError(f"width {width} and budget_s {budget_s:g} must be positive")
    by_name = {node.name: node for node in nodes}
    waiting = order(nodes)
    results: dict[str, MicroResult] = {}
    running: dict[str, tuple[Running, float]] = {}
    began = clock()

    def finish(name: str, result: MicroResult, started: float) -> None:
        results[name] = replace(result, elapsed_ms=(clock() - started) * 1000)

    try:
        while waiting or running:
            moved = False
            for name in list(waiting):
                if failed := [need for need in by_name[name].needs if need in results and not results[need].actionable]:
                    results[name] = _unknown(
                        name, f"blocked by {failed[0]}", f"make {failed[0]} answer ok, then run {name} again"
                    )
                    waiting.remove(name)
                    moved = True
            left = budget_s - (clock() - began)
            if left <= 0:
                for name, (handle, started) in running.items():
                    handle.stop()
                    results[name] = _unknown(
                        name,
                        f"stopped: the total budget {budget_s:g}s was spent",
                        "raise the budget or run it alone",
                        clock() - started,
                    )
                for name in waiting:
                    results[name] = _unknown(
                        name, f"not started: the total budget {budget_s:g}s was spent", "run it alone"
                    )
                running.clear()
                waiting.clear()
                break
            for name in [n for n in waiting if all(need in results for need in by_name[n].needs)]:
                if len(running) >= width or (running and not admit()):
                    break
                running[name] = (start(by_name[name], min(by_name[name].timeout_s, left)), clock())
                waiting.remove(name)
                moved = True
            for name, (handle, started) in list(running.items()):
                if (answer := handle.poll()) is not None:
                    del running[name]
                    finish(name, answer, started)
                    moved = True
                elif clock() - started > by_name[name].timeout_s:
                    handle.stop()
                    del running[name]
                    results[name] = _unknown(
                        name,
                        f"timed out after {by_name[name].timeout_s:g}s",
                        f"find what {name} waits on, or raise its timeout_s with a measurement",
                        clock() - started,
                    )
                    moved = True
            if running and not moved:
                wait(poll_s)
    finally:
        for handle, _ in running.values():
            handle.stop()
    return {node.name: results[node.name] for node in nodes}


def summary(results: Iterable[tuple[str, MicroResult]]) -> str:
    """One line per node: its status, its time and, when not ok, why and what next."""
    lines = []
    for name, result in results:
        seconds = (result.elapsed_ms or 0) / 1000
        tail = "" if result.actionable else f" — {'; '.join(result.evidence_refs)} — next: {result.next}"
        lines.append(f"{result.status.upper():8} {name} ({seconds:.0f}s){tail}")
    return "\n".join(lines)
