#!/usr/bin/env python3
"""Regression cases for one-artifact handoff capsules."""
from __future__ import annotations


def run(module) -> None:
    """Register the handoff capsule contract into atlas_test's counted cases."""
    import handoff

    record = handoff.capsule("scripts/intake.py", "tighten prompt routing")
    expected = ["languages/python/README.md", "languages/python/OPERATING.md", "languages/python/tools.yaml"]
    if record["scope"] != ["scripts/intake.py"] or record["route"]["language"] != "python" \
            or record["context"] != expected or not all(row["command"] for row in record["acceptance"]):
        raise SystemExit(f"FAIL handoff widened or lost its artifact edge: {record}")
    try:
        handoff.capsule("missing.py")
    except ValueError:
        pass
    else:
        raise SystemExit("FAIL handoff accepted an artifact outside the declared tree")
    module.CASES.append(("handoff binds one artifact to route evidence, bounded context and acceptance commands",
                         "a multi-agent brief that gives a repository dump or leaves the recipient to infer its gates"))
    print("  ok    handoff carries one artifact's route, context and gates")
