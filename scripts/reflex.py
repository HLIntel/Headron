#!/usr/bin/env python3
"""Command classification primitives — single-pass diff and command classification.

Groups commands into orthogonal categories based on command_categories from decision_tables.
Classifies a diff's metadata (files touched, AST delta depth, dependency scope) against
constraints in one forward pass, producing a verdict vector.

Integrates with callshape.py for forbidden call pattern matching.

proves: a diff or command is classified against all declared categories in one pass
does_not_prove: that the classification is correct for the task — only that the pattern matched
closed_by: reflex_test.py, which plants forbidden paths and asserts isolation
"""

from __future__ import annotations

from typing import Any

from atlascore import atlas
from decide import GateVerdict
from decide import reset_caches as reset_decide_caches


def reset_caches() -> None:
    """Clear all reflex caches."""
    reset_decide_caches()


def classify_command(command: str, context: dict | None = None) -> tuple[str, int]:
    """Classify a shell command against pre-compiled command categories.

    Returns (category, risk_level) for the first matching pattern.
    Delegates to decide.command_verdict for the actual classification.

    proves: a command is classified against declared patterns in one pass
    does_not_prove: that the classification is correct for the task context
    closed_by: reflex_test.py, which plants ambiguous commands and asserts refusal
    """
    from decide import command_verdict  # noqa: PLC0415

    return command_verdict(command, context)


def classify_diff(diff_metadata: dict[str, Any]) -> dict[str, str]:
    """Classify a diff's metadata against all gate constraints in one pass.

    Args:
        diff_metadata: dict with keys:
            - files: list of changed file paths
            - ast_delta: estimated AST depth change (optional)
            - dependency_scope: 'none', 'local', 'external' (optional)

    Returns:
        Verdict vector mapping gate names to verdict types.
    """
    verdicts: dict[str, str] = {}
    files = diff_metadata.get("files", [])
    dep_scope = diff_metadata.get("dependency_scope", "none")

    # Check for forbidden paths — isolate if touched
    forbidden = atlas().get("forbidden_calls") or {}
    for file_path in files:
        for rule_name, rule_spec in forbidden.items():
            exempt = (rule_spec or {}).get("exempt_files", [])
            if any(file_path.endswith(f) for f in exempt):
                continue
            roster = (rule_spec or {}).get("roster", [])
            for r in roster:
                if file_path.startswith(str(r)):
                    verdicts[rule_name] = "isolate"
                    break

    # Dependency scope classification
    if dep_scope == "external":
        verdicts["dependency_graph"] = "fail"
    elif dep_scope == "local":
        verdicts["dependency_graph"] = "pass"

    # AST delta classification — large changes need more scrutiny
    ast_delta = diff_metadata.get("ast_delta", 0)
    if ast_delta > 10:
        verdicts["code_shape"] = "isolate"
    elif ast_delta > 5:
        verdicts["code_shape"] = "pass"

    # Default: pass for gates not explicitly classified
    tables = atlas().get("decision_tables") or {}
    for category, gates in (tables.get("gate_categories") or {}).items():
        for gate in gates:
            if gate not in verdicts:
                verdicts[gate] = "pass"

    return verdicts


def classify_change(change_class: str, files: list[str], diff_metadata: dict[str, Any] | None = None) -> GateVerdict:
    """Classify a change by its class and affected files.

    Returns a GateVerdict indicating the overall risk level.

    proves: a change class and file set map to a verdict type
    does_not_prove: that the change is correct — only its risk category
    closed_by: reflex_test.py, which plants a forbidden path and asserts isolate
    """
    if diff_metadata is None:
        diff_metadata = {"files": files}
    elif "files" not in diff_metadata:
        diff_metadata["files"] = files
    verdicts = classify_diff(diff_metadata)

    # If any gate isolates, the whole change is isolated
    if "isolate" in verdicts.values():
        return GateVerdict.ISOLATE

    # If any gate fails, the whole change fails
    if "fail" in verdicts.values():
        return GateVerdict.FAIL

    # Check verification_policy profiles for fast-track eligibility
    profiles = (atlas().get("verification_policy") or {}).get("profiles") or {}
    profile = profiles.get(change_class)
    if not profile:
        return GateVerdict.PASS

    # A source_change with only instant gates can fast-track
    required = (profile if isinstance(profile, dict) else {}).get("required", [])
    if not required:
        return GateVerdict.FAST_TRACK

    return GateVerdict.PASS


def forbidden_path_touched(file_path: str) -> bool:
    """Check if a file path is in a forbidden call roster.

    proves: a file path is checked against forbidden_calls rosters
    does_not_prove: that the file should be excluded — only that it is in a roster
    closed_by: reflex_test.py, which plants a forbidden path touch
    """
    forbidden = atlas().get("forbidden_calls") or {}
    for rule_name, rule_spec in forbidden.items():
        exempt = (rule_spec or {}).get("exempt_files", [])
        if any(file_path.endswith(f) for f in exempt):
            continue
        roster = (rule_spec or {}).get("roster", [])
        for r in roster:
            if file_path.startswith(str(r)):
                return True
    return False
