#!/usr/bin/env python3
"""Planted case: a gate killed at verify's timeout has no verdict, so it is NOT RUN, never a FAIL or a lesson."""

from __future__ import annotations


def timeout_case(module) -> None:
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
    module.CASES.append(
        (
            "a gate past verify's timeout is NOT RUN and holds the run at exit 2",
            "a load-induced overrun read as FAIL, blamed on the change and counted as a lesson",
        )
    )
    print("  ok    a timed-out gate is NOT RUN, never a FAIL")


def run(module) -> None:
    timeout_case(module)
