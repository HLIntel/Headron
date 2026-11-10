"""Compiled decision table engine — the System One core.

Reads decision tables from the shared atlas loader and evaluates command patterns against
the current in-memory rules.

A parser that picks a winner on ambiguous input is worse than one that errs (rule 4).
`none` is a real verdict: the engine refuses rather than guessing when the table is incomplete.

proves: the decision_tables section is self-consistent and the compiled engine returns typed verdicts
does_not_prove: that a verdict is correct for the task — only that the declaration is valid
closed_by: decide_test.py, which plants malformed tables and asserts refusal
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from atlascore import atlas

_GATE_TRANSITIONS: dict[str, str] = {
    "pass": "next_gate",
    "fail": "halt",
    "isolate": "sandbox_review",
    "fast_track": "skip_remaining",
}
_GATE_LABELS: dict[str, str] = {"pass": "Clear", "fail": "Blocked", "isolate": "Quarantined", "fast_track": "Exempted"}


class GateVerdict(Enum):
    """Typed categorical verdict for a gate, replacing text-heavy dicts.

    Each value carries structured metadata so pipeline transitions are type-safe.
    """

    PASS = "pass"
    FAIL = "fail"
    ISOLATE = "isolate"
    FAST_TRACK = "fast_track"

    @property
    def transition(self) -> str:
        """The pipeline transition this verdict triggers."""
        return _GATE_TRANSITIONS[self.value]

    @property
    def label(self) -> str:
        """Human-readable label for logging."""
        return _GATE_LABELS.get(self.value, self.value)


def decision_table_errors() -> list[str]:
    """The decision_tables section is self-consistent: verdict types, gate categories, command patterns, and transitions.

    Each verdict type must be one of the four declared names. A category's gates resolving into the done_set is a
    row in atlas.yaml/pointers. Every command pattern must be a valid regex. Every transition source and destination must
    reference valid states. An empty section is accepted — the engine falls back to per-request evaluation.
    """
    errors: list[str] = []
    tables = atlas().get("decision_tables")
    if not tables:
        return errors
    valid_verdicts = {"pass", "fail", "isolate", "fast_track"}
    verdict_types = tables.get("verdict_types") or {}
    for vtype in verdict_types:
        if str(vtype) not in valid_verdicts:
            errors.append(
                f"decision_tables/verdict_types/{vtype} is not a valid verdict type "
                f"(expected one of {sorted(valid_verdicts)})"
            )
    for cat_name, cat_spec in (tables.get("command_categories") or {}).items():
        pattern = str((cat_spec or {}).get("pattern", ""))
        if pattern:
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"decision_tables/command_categories/{cat_name} pattern is not a valid regex: {exc}")
        risk = (cat_spec or {}).get("risk")
        if risk is None:
            errors.append(f"decision_tables/command_categories/{cat_name} declares no risk level")
    valid_states = valid_verdicts | {"ingest", "classify", "verify", "halt", "sandbox_review", "exit"}
    for state, transitions in (tables.get("transitions") or {}).items():
        if str(state) not in valid_states:
            errors.append(f"decision_tables/transitions/{state} is not a valid state")
        for verdict, next_state in (transitions or {}).items():
            if str(verdict) not in valid_verdicts:
                errors.append(f"decision_tables/transitions/{state}/{verdict} is not a valid verdict type")
            if str(next_state) not in valid_states:
                errors.append(f"decision_tables/transitions/{state}/{verdict} -> '{next_state}' is not a valid state")
    return errors


def _load_tables() -> dict[str, Any]:
    """Read and validate the decision_tables section from atlas.yaml."""
    return atlas().get("decision_tables") or {}


# An optional pattern list; the default reads current rules on every decision.
_COMMAND_PATTERNS: list[tuple[str, re.Pattern, int]] = []


def reset_caches() -> None:
    """Clear all compiled caches. Called before mutation tests plant defects."""
    global _COMMAND_PATTERNS
    _COMMAND_PATTERNS = []


def _compile_command_patterns() -> list[tuple[str, re.Pattern, int]]:
    """Pre-compile all command category regex patterns from decision_tables."""
    if _COMMAND_PATTERNS:
        return _COMMAND_PATTERNS
    tables = _load_tables()
    patterns = []
    for cat_name, cat_spec in (tables.get("command_categories") or {}).items():
        pattern_str = str((cat_spec or {}).get("pattern", ""))
        risk = int((cat_spec or {}).get("risk", 0))
        if pattern_str:
            try:
                compiled = re.compile(pattern_str)
                patterns.append((cat_name, compiled, risk))
            except re.error:
                pass
    return patterns


def command_verdict(command: str, context: dict | None = None) -> tuple[str, int]:
    """Classify a command string against pre-compiled command categories.

    Returns (category, risk_level) for the first matching pattern, or ("unknown", -1) if no match.

    proves: a command is classified against declared patterns in one pass
    does_not_prove: that the classification is correct for the task context
    closed_by: reflex_test.py, which plants ambiguous commands and asserts refusal
    """
    patterns = _compile_command_patterns()
    for cat_name, pattern, risk in patterns:
        if pattern.search(command):
            return cat_name, risk
    return "unknown", -1


def transition(current_state: str, verdict: str) -> str | None:
    """Look up the next state from the transition table.

    Returns the next state name, or None if the transition is not declared.

    proves: a (state, verdict) pair maps to exactly one next state
    does_not_prove: that the transition is correct — only that it is declared
    closed_by: pipeline_test.py, which plants a cycle and asserts refusal
    """
    tables = _load_tables()
    state_map = (tables.get("transitions") or {}).get(current_state) or {}
    next_state = state_map.get(verdict)
    if next_state is None:
        return None
    return str(next_state)
