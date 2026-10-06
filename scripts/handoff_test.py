#!/usr/bin/env python3
"""Regression cases for one-artifact handoff capsules."""

from __future__ import annotations


def run(module) -> None:
    """Register the handoff capsule contract into atlas_test's counted cases."""
    import handoff

    record = handoff.capsule("scripts/intake.py", "tighten prompt routing")
    expected = ["languages/python/README.md", "languages/python/OPERATING.md", "languages/python/tools.yaml"]
    if (
        record["scope"] != ["scripts/intake.py"]
        or record["route"]["language"] != "python"
        or record["context"] != expected
        or not all(row["command"] for row in record["acceptance"])
    ):
        raise SystemExit(f"FAIL handoff widened or lost its artifact edge: {record}")
    try:
        handoff.capsule("missing.py")
    except ValueError:
        pass
    else:
        raise SystemExit("FAIL handoff accepted an artifact outside the declared tree")
    module.CASES.append(
        (
            "handoff binds one artifact to route evidence, bounded context and acceptance commands",
            "a multi-agent brief that gives a repository dump or leaves the recipient to infer its gates",
        )
    )
    print("  ok    handoff carries one artifact's route, context and gates")
    pass_cache_case(module)


def pass_cache_case(module) -> None:
    """A clean-checkout PASS is remembered per (tree, gates); a failure is never remembered."""
    import sys
    import tempfile
    import uuid
    from pathlib import Path

    import branchstate

    with tempfile.TemporaryDirectory() as tmp:
        runs, nonce = Path(tmp) / "runs", uuid.uuid4().hex
        tally = f"open({str(runs)!r}, 'a').write('x')"
        good = [[sys.executable, "-c", f"{tally}  # {nonce}"]]
        bad = [[sys.executable, "-c", f"{tally}; raise SystemExit(3)  # {nonce}"]]
        verdicts = [branchstate.clean_checkout_errors(g) for g in (good, good, bad, bad)]
        ran = len(runs.read_text()) if runs.exists() else 0
    if verdicts[:2] != [None, None] or None in verdicts[2:] or ran != 3:
        raise SystemExit(f"FAIL the clean-checkout pass cache: verdicts {verdicts}, gate ran {ran} time(s), want 3")
    module.CASES.append(
        (
            "a clean-checkout pass on an identical tree and gates is not re-run; a failure always is",
            "a re-land after a push or forge refusal that re-queues the whole suite on the tree it already passed",
        )
    )
    print("  ok    a clean-checkout pass is remembered by tree and gates, a failure never")
