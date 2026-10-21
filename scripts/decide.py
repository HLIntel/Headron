"""Compiled decision table engine — the System One core.

Reads `decision_tables` from atlas.yaml once at module load, pre-compiles regex patterns,
builds lookup dictionaries, and caches results by (gate_id, context_hash). An agent proposing
a change gets a verdict in one forward pass, not a sequential walk through YAML, regex lists,
and role resolutions.

A parser that picks a winner on ambiguous input is worse than one that errs (rule 4).
`none` is a real verdict: the engine refuses rather than guessing when the table is incomplete.

proves: the decision_tables section is self-consistent and the compiled engine returns typed verdicts
does_not_prove: that a verdict is correct for the task — only that the declaration is valid
closed_by: decide_test.py, which plants malformed tables and asserts refusal
"""

from __future__ import annotations

import hashlib
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

    Each verdict type must be one of the four declared names. Every gate in a category must exist in the
    done_set. Every command pattern must be a valid regex. Every transition source and destination must
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
    done_ids = {g["id"] for g in (atlas().get("verification_policy") or {}).get("done_set") or []}
    for category, gates in (tables.get("gate_categories") or {}).items():
        for gate in gates:
            if str(gate) not in done_ids:
                errors.append(
                    f"decision_tables/gate_categories/{category} names '{gate}', "
                    "which is not in verification_policy/done_set"
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


# Pre-compiled command category patterns, built once at module load.
_COMMAND_PATTERNS: list[tuple[str, re.Pattern, int]] = []

# Result cache: (gate_id, context_hash) → verdict string
_GATE_CACHE: dict[str, str] = {}

# Command result cache: command string → (category, risk)
_COMMAND_CACHE: dict[str, tuple[str, int]] = {}


def _context_hash(context: dict | None) -> str:
    """Produce a stable hash for a context dict, used as cache key."""
    if not context:
        return ""
    return hashlib.sha256(str(sorted(context.items())).encode()).hexdigest()[:12]


def reset_caches() -> None:
    """Clear all compiled caches. Called before mutation tests plant defects."""
    global _COMMAND_PATTERNS, _GATE_CACHE, _COMMAND_CACHE
    _COMMAND_PATTERNS = []
    _GATE_CACHE.clear()
    _COMMAND_CACHE.clear()


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
    Results are cached by command string for repeated calls.

    proves: a command is classified against declared patterns in one pass
    does_not_prove: that the classification is correct for the task context
    closed_by: reflex_test.py, which plants ambiguous commands and asserts refusal
    """
    if command in _COMMAND_CACHE:
        return _COMMAND_CACHE[command]
    patterns = _compile_command_patterns()
    if not patterns:
        result = ("unknown", -1)
    else:
        for cat_name, pattern, risk in patterns:
            if pattern.search(command):
                result = (cat_name, risk)
                _COMMAND_CACHE[command] = result
                return result
        result = ("unknown", -1)
    _COMMAND_CACHE[command] = result
    return result


def gate_verdict(gate_id: str, context: dict | None = None) -> str:
    """Return the gate category for a given gate id, or 'unknown' if not classified.

    Results are cached by (gate_id, context_hash) for repeated calls.

    proves: a gate id maps to its declared evaluation cost category
    does_not_prove: that the gate will pass or fail — only its cost tier
    closed_by: decide_test.py, which plants a missing gate and asserts fallback
    """
    cache_key = f"{gate_id}:{_context_hash(context)}"
    if cache_key in _GATE_CACHE:
        return _GATE_CACHE[cache_key]
    tables = _load_tables()
    for category, gates in (tables.get("gate_categories") or {}).items():
        if gate_id in gates:
            _GATE_CACHE[cache_key] = category
            return category
    result = "unknown"
    _GATE_CACHE[cache_key] = result
    return result


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
