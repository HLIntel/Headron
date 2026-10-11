#!/usr/bin/env python3
"""Planted case: an agent that never answered is NOT RUN, never a 0 solved that gets recorded."""

from __future__ import annotations

import contextlib
import io
import pathlib
import tempfile


def agentbench_case(module) -> None:
    """agentbench printed 'solved 0/4 · gates clean 4/4 · $0.000' for four API errors and --record would have kept it."""
    import agentbench

    dead = {
        "solved": False,
        "gates_clean": True,
        "seconds": 5.0,
        "turns": 0,
        "tokens": 0,
        "cost_usd": 0,
        "agent_error": True,
    }
    saved_run, saved_which, saved_root = agentbench.run, agentbench.shutil.which, agentbench.ROOT
    agentbench.run = lambda task, arm, model: dict(dead)
    agentbench.shutil.which = lambda name: "/bin/true"
    out = io.StringIO()
    with tempfile.TemporaryDirectory() as scratch:
        # the unfixed code wrote its zeros to ROOT/benchmarks/agent-latest.json: a plant must never reach the real record
        (pathlib.Path(scratch) / "benchmarks").mkdir()
        agentbench.ROOT = pathlib.Path(scratch)
        try:
            with contextlib.redirect_stdout(out):
                code = agentbench.main(["--record"])
        finally:
            agentbench.run, agentbench.shutil.which, agentbench.ROOT = saved_run, saved_which, saved_root
        recorded = (pathlib.Path(scratch) / "benchmarks" / "agent-latest.json").exists()
    if code != 2 or "NOT RUN" not in out.getvalue() or recorded:
        raise SystemExit(
            f"FAIL agentbench read an API-errored run as a result: exit {code}, recorded={recorded}: {out.getvalue()!r}"
        )
    module.CASES.append(
        (
            "an agent run that errored is NOT RUN at exit 2 and nothing is recorded",
            "a dead API scored as a clean 0 solved, and --record kept it as the benchmark",
        )
    )
    print("  ok    an errored agent run is NOT RUN, never a recorded 0")


def run(module) -> None:
    agentbench_case(module)
