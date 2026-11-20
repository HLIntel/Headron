#!/usr/bin/env python3
"""Planted case: a gate killed at verify's timeout has no verdict, so it is NOT RUN, never a FAIL or a lesson."""

from __future__ import annotations

from types import ModuleType


def timeout_case(module: ModuleType) -> None:
    """verify said FAIL where branchstate said NOT RUN for the same overrun, and learn() counted it as a cause."""
    import verify

    saved = verify.TIMEOUT
    verify.TIMEOUT = 1
    try:
        slow = verify.run_gate({"id": "t", "argv": ["python", "-c", "import time; time.sleep(5)"]})
    finally:
        verify.TIMEOUT = saved
    if slow["verdict"] != "NOT RUN" or "timed out" not in slow["why"]:
        raise SystemExit(f"FAIL verify read a gate past its timeout as {slow['verdict']}: {slow.get('why')!r}")
    if verify.verdict_code([slow]) != 2:
        raise SystemExit("FAIL a timed-out gate did not hold verify at exit 2 (incomplete is not done)")
    # THE RECORD'S OWN BUDGET: a gate declaring timeout_ms is held to it, not to the runner's default.
    declared = verify.run_gate({"id": "t", "argv": ["python", "-c", "import time; time.sleep(5)"], "timeout_ms": 1000})
    if declared["verdict"] != "NOT RUN" or declared.get("seconds") != 1:
        raise SystemExit(f"FAIL a gate declaring timeout_ms: 1000 was not stopped at 1 s: {declared!r}")
    import declcheck

    for bad in (0, -1, "900", True, 1.5):
        if not declcheck.gate_timeout_errors({"id": "t", "timeout_ms": bad}):
            raise SystemExit(f"FAIL declcheck accepted timeout_ms {bad!r}, which verify would read as its default")
    if declcheck.gate_timeout_errors({"id": "t", "timeout_ms": 1000}) or declcheck.gate_timeout_errors({"id": "t"}):
        raise SystemExit("FAIL declcheck refused a valid or absent timeout_ms")
    module.CASES.append(
        (
            "a gate past verify's timeout is NOT RUN and holds the run at exit 2",
            "a load-induced overrun read as FAIL, blamed on the change and counted as a lesson",
        )
    )
    print("  ok    a timed-out gate is NOT RUN, never a FAIL; a declared timeout_ms is its budget")


def run(module: ModuleType) -> None:
    timeout_case(module)
