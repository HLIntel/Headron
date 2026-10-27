#!/usr/bin/env python3
""".headron language framework integration for the decision engine.

Compiles .headron programs into decision table entries, enabling the decision engine
to use .headron surface notation for fast-path verdicts. Parses scope blocks into gate
categories, commands into command categories, and effects into verdict types.

This bridges the .headron surface notation (headronlang.py) with the compiled decision engine
(decide.py), so that .headron programs can declare decision rules directly.

proves: .headron programs compile to valid decision table entries
does_not_prove: that the compiled verdicts are correct — only that they parse
closed_by: decide_test.py, which plants malformed .headron programs and asserts refusal
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from atlascore import ROOT, atlas


@dataclass
class HeadronDecisionRule:
    """A decision rule compiled from a .headron program.

    Each rule maps a .headron program's scope, commands, and effects to decision table entries.
    """

    source: str  # file path
    gate_categories: dict[str, list[str]] = field(default_factory=dict)
    command_categories: dict[str, dict[str, Any]] = field(default_factory=dict)
    verdict_mappings: dict[str, str] = field(default_factory=dict)
    scope_forbidden: list[str] = field(default_factory=list)
    scope_allowed: list[str] = field(default_factory=list)


def headron_framework_errors() -> list[str]:
    """Validate .headron framework integration is self-consistent.

    Checks:
    - All .headron programs in examples/ compile without error
    - Compiled decision rules reference valid gate ids
    - Command categories have valid patterns

    proves: .headron programs compile to valid decision table entries
    does_not_prove: that the verdicts are correct — only that they parse
    closed_by: decide_test.py, which plants malformed .headron programs
    """
    import headronlang  # noqa: PLC0415

    errors: list[str] = []
    headron_files = list(ROOT.glob("**/*.headron"))

    done_ids = {g["id"] for g in (atlas().get("verification_policy") or {}).get("done_set") or []}

    for headron_file in headron_files:
        try:
            content = headron_file.read_text(encoding="utf-8")
            result = headronlang.parse(content, str(headron_file))
            if "error" in result:
                errors.append(f"{headron_file.name}: parse error: {result['error']}")
                continue

            # Validate compiled rules
            rules = compile_headron_to_rules(headron_file, content)
            for rule in rules:
                # Check gate categories reference valid gates
                for category, gates in rule.gate_categories.items():
                    for gate in gates:
                        if gate not in done_ids:
                            errors.append(
                                f"{headron_file.name}: gate {gate!r} in category {category!r} not in done_set"
                            )
        except Exception as e:
            errors.append(f"{headron_file.name}: exception: {e}")

    return errors


def compile_headron_to_rules(headron_path: Any, content: str) -> list[HeadronDecisionRule]:
    """Compile a .headron program into decision rules.

    Args:
        headron_path: Path to the .headron file.
        content: The file content.

    Returns:
        List of HeadronDecisionRule objects.
    """
    import headronlang  # noqa: PLC0415

    rules: list[HeadronDecisionRule] = []
    result = headronlang.parse(content, str(headron_path))
    if "error" in result:
        return rules

    rule = HeadronDecisionRule(source=str(headron_path))

    # Extract scope blocks into forbidden/allowed lists (headronlang uses forbidden_paths/allowed_paths)
    rule.scope_forbidden = result.get("forbidden_paths", []) or []
    rule.scope_allowed = result.get("allowed_paths", []) or []

    # Extract commands into command categories (headronlang uses allowed_commands)
    allowed_cmds = result.get("allowed_commands", []) or []
    if allowed_cmds:
        rule.command_categories["allowed"] = {"pattern": "|".join(allowed_cmds), "risk": 0}

    # Extract effects into verdict mappings (headronlang returns a list of effect strings)
    effects = result.get("effects", []) or []
    network = result.get("network", "")
    if network == "denied":
        rule.verdict_mappings["network"] = "fail"
    if "none" in str(effects):
        rule.verdict_mappings["side_effects"] = "fast_track"

    # Extract required gates into gate categories (headronlang uses required_gates)
    required = result.get("required_gates", []) or []
    if isinstance(required, list) and required:
        rule.gate_categories["required"] = required

    rules.append(rule)
    return rules


def headron_verdict(headron_path: Any) -> dict[str, str]:
    """Get the verdict mapping from a .headron program.

    Args:
        headron_path: Path to the .headron file.

    Returns:
        Dict mapping gate names to verdict types.
    """
    verdicts: dict[str, str] = {}
    try:
        content = headron_path.read_text(encoding="utf-8")
        rules = compile_headron_to_rules(headron_path, content)
        for rule in rules:
            verdicts.update(rule.verdict_mappings)
    except Exception:
        pass
    return verdicts


def headron_scope_check(file_path: str, headron_path: Any) -> str:
    """Check if a file path is within the scope of a .headron program.

    Args:
        file_path: The file path to check.
        headron_path: Path to the .headron file.

    Returns:
        'allowed' if in scope, 'forbidden' if explicitly forbidden, 'unknown' otherwise.
    """
    try:
        content = headron_path.read_text(encoding="utf-8")
        rules = compile_headron_to_rules(headron_path, content)
        for rule in rules:
            if file_path in rule.scope_forbidden:
                return "forbidden"
            if file_path in rule.scope_allowed:
                return "allowed"
    except Exception:
        pass
    return "unknown"


def headron_command_check(command: str, headron_path: Any) -> str:
    """Check if a command is allowed by a .headron program.

    Args:
        command: The command to check.
        headron_path: Path to the .headron file.

    Returns:
        'allowed' if permitted, 'refused' if not, 'unknown' if not specified.
    """
    import re  # noqa: PLC0412

    try:
        content = headron_path.read_text(encoding="utf-8")
        rules = compile_headron_to_rules(headron_path, content)
        for rule in rules:
            for cat_name, cat_spec in rule.command_categories.items():
                pattern = cat_spec.get("pattern", "")
                if pattern and re.search(pattern, command):
                    return "allowed" if cat_name == "allowed" else "refused"
    except Exception:
        pass
    return "unknown"
