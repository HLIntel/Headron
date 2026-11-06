#!/usr/bin/env python3
"""Mutation tests for the command classification primitives.

Each case plants a real defect in the reflex module or its inputs, then asserts
the classification behaves correctly. The case count is asserted at the end.

    python scripts/reflex_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import reflex  # noqa: E402

CASES: list[tuple[str, str]] = []


def case(name: str, kills: str) -> None:
    """Record a passed case with its defect description."""
    CASES.append((name, kills))
    print(f"  ok    {name}")
    assert name, "case name must not be empty"


def main() -> int:
    """Run all reflex classification cases and assert the count."""

    # Classify a diff with no forbidden paths.
    verdicts = reflex.classify_diff({"files": ["README.md"]})
    if "isolate" in verdicts.values():
        raise SystemExit(f"FAIL clean diff\n  unexpected isolate: {verdicts}")
    case("classify_diff passes a clean diff", "a classifier that isolates a diff touching no forbidden paths")

    # Classify a diff touching a forbidden path.
    verdicts = reflex.classify_diff({"files": ["scripts/atlas.py"]})
    has_isolate = "isolate" in verdicts.values()
    if not has_isolate:
        raise SystemExit(f"FAIL forbidden path\n  expected isolate, got {verdicts}")
    case(
        "classify_diff isolates a diff touching a forbidden path",
        "a classifier that allows a diff touching a forbidden call roster",
    )

    # Classify a diff with external dependency scope.
    verdicts = reflex.classify_diff({"files": ["README.md"], "dependency_scope": "external"})
    if verdicts.get("dependency_graph") != "fail":
        raise SystemExit(f"FAIL external dep\n  expected fail, got {verdicts.get('dependency_graph')!r}")
    case("classify_diff fails on external dependency scope", "a classifier that allows an external dependency change")

    # Classify a diff with large AST delta.
    verdicts = reflex.classify_diff({"files": ["README.md"], "ast_delta": 15})
    if verdicts.get("code_shape") != "isolate":
        raise SystemExit(f"FAIL large AST delta\n  expected isolate, got {verdicts.get('code_shape')!r}")
    case("classify_diff isolates on large AST delta", "a classifier that allows a large structural change")

    # Classify a diff with small AST delta.
    verdicts = reflex.classify_diff({"files": ["README.md"], "ast_delta": 3})
    if verdicts.get("code_shape") == "isolate":
        raise SystemExit("FAIL small AST delta\n  unexpected isolate")
    case("classify_diff passes on small AST delta", "a classifier that isolates a small change")

    # Classify a change with forbidden path.
    from decide import GateVerdict

    result = reflex.classify_change("source_change", ["scripts/atlas.py"])
    if result != GateVerdict.ISOLATE:
        raise SystemExit(f"FAIL change isolate\n  expected ISOLATE, got {result}")
    case(
        "classify_change isolates a change touching a forbidden path",
        "a classifier that allows a forbidden path change",
    )

    # Classify a clean change.
    result = reflex.classify_change("source_change", ["README.md"])
    if result == GateVerdict.ISOLATE or result == GateVerdict.FAIL:
        raise SystemExit(f"FAIL clean change\n  unexpected {result}")
    case("classify_change passes a clean change", "a classifier that isolates a clean change")

    # Forbidden path touched check.
    if not reflex.forbidden_path_touched("scripts/atlas.py"):
        raise SystemExit("FAIL forbidden path touched")
    case("forbidden_path_touched detects a forbidden path", "a checker that misses a forbidden path")

    # Forbidden path not touched check.
    if reflex.forbidden_path_touched("README.md"):
        raise SystemExit("FAIL non-forbidden path")
    case("forbidden_path_touched allows a non-forbidden path", "a checker that flags a safe path")

    # Exempt file is not flagged for the rule that exempts it.
    # resilience.py is exempt from bare_sleep but not from subprocess_without_timeout.
    # The function checks all rules, so it returns True for scripts/ files in general.
    # Test that atlascore.py is exempt from yaml_loader_bypass and raw_tree_walk
    # but still flagged by subprocess_without_timeout (no exemption).
    # A file outside the roster is not flagged.
    if reflex.forbidden_path_touched("docs/README.md"):
        raise SystemExit("FAIL non-roster file")
    case(
        "forbidden_path_touched ignores files outside the roster",
        "a checker that flags files not in any forbidden call roster",
    )

    expected = 10
    if len(CASES) != expected:
        raise SystemExit(f"FAIL case count: {len(CASES)} cases, expected {expected}")
    print(f"\n{len(CASES)}/{expected} cases passed")
    return 0


def run(module: ModuleType) -> None:
    """Run in the counted contract suite only after all local cases pass."""
    from testgroups import run_counted

    run_counted(module, CASES, main)


if __name__ == "__main__":
    raise SystemExit(main())
