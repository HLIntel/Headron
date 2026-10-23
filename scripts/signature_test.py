#!/usr/bin/env python3
"""Planted defects for `agent_failure_modes/<shape>/signature`: a pattern that does not compile, and one claimed twice."""

from __future__ import annotations

REFUSAL = "inv:failure_modes_name_their_refusal"


def run(module) -> None:
    first = "  a_quote_that_outlived_its_text:\n    signature:\n      - "
    with module.mutated("atlas.yaml", lambda s: s.replace(first, first + "'(unclosed'\n      - ", 1)):
        module.case(
            "a failure signature that does not compile is refused",
            "a `thea failures --match` that raises on the first pattern it cannot read",
            True,
            "signature",
            by=REFUSAL,
        )
    # THE KEY SET IS CLOSED: a second_sighting-style key that no summary reads is refused, not kept silently.
    header = "  a_quote_that_outlived_its_text:\n"
    with module.mutated("atlas.yaml", lambda s: s.replace(header, header + "    still_open: 'a stray key'\n", 1)):
        module.case(
            "a failure row key outside the closed set is refused",
            "a sighting written to a key that no count sums, so it drops out of every summary",
            True,
            "still_open",
            by=REFUSAL,
        )
    taken = "  a_value_quoted_by_hand:\n    signature:\n      - "
    with module.mutated(
        "atlas.yaml",
        lambda s: s.replace(taken, taken + "'substring not found|String to replace not found'\n      - ", 1),
    ):
        module.case(
            "two shapes claiming one signature are refused",
            "a match that names whichever shape was declared first and hides the other",
            True,
            "signature",
            by=REFUSAL,
        )
