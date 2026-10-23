#!/usr/bin/env python3
"""The failure ledger's row-shape rules: the closed key set, and the `signature` regexes `thea failures --match` reads.

SPLIT OUT OF atlasinv.py (failure-ledger redesign): atlasinv crossed MAX_CODE_LINES when the key set was added,
and these rules read one row each, so they need nothing else in that module. Imports nothing from the harness.
"""

from __future__ import annotations


SIGNATURE_MAX = 200


def signature_errors(name: str, spec: dict, seen: dict[str, str]) -> list[str]:
    """`signature` is the error text a shape leaves behind, as regexes `thea failures --match` reads: each compiles,
    stays short, and no two shapes claim the same pattern (a match must name ONE shape)."""
    import re  # noqa: PLC0415

    errors: list[str] = []
    rows = spec.get("signature")
    if rows is None:
        return errors
    if not isinstance(rows, list) or not rows or not all(isinstance(r, str) and r.strip() for r in rows):
        return [f"agent_failure_modes/{name} signature must be a non-empty list of regex strings"]
    for pattern in rows:
        if len(pattern) > SIGNATURE_MAX:
            errors.append(f"agent_failure_modes/{name} signature is over {SIGNATURE_MAX} characters: {pattern[:40]}...")
        try:
            re.compile(pattern)
        except re.error as exc:
            errors.append(f"agent_failure_modes/{name} signature does not compile ({exc}): {pattern[:60]}")
        if seen.setdefault(pattern, name) != name:
            errors.append(f"agent_failure_modes/{name} signature repeats {seen[pattern]}'s: {pattern[:60]}")
    return errors


# THE KEY SET IS CLOSED (failure-ledger redesign). A key nothing reads stops counting without a sound: three
# sightings sat in `second_sighting`, `third_sighting` and `still_open`, keys no summary summed. Each shape
# carries these only. `history` is the text of sightings two and on; `gap` is the limit a guarded shape keeps.
FAILURE_ROW_KEYS = frozenset({"shape", "looks_like", "tell", "prevented_by", "enforced_by", "closed_by",
                              "unenforceable", "sightings", "intake", "signature", "history", "gap"})


def key_errors(name: str, spec: dict) -> list[str]:
    errors = [f"agent_failure_modes/{name} carries {key} — not a ledger key; put its text in `history` or `gap`"
              for key in sorted(set(spec) - FAILURE_ROW_KEYS)]
    history = spec.get("history")
    if history is not None and not (isinstance(history, list) and all(isinstance(h, str) and h.strip() for h in history)):
        errors.append(f"agent_failure_modes/{name} history must be a list of non-empty strings, one per later sighting")
    if spec.get("gap") is not None and not (isinstance(spec["gap"], str) and spec["gap"].strip()):
        errors.append(f"agent_failure_modes/{name} gap must be a non-empty string naming the limit")
    return errors
