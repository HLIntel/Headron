"""Planted public-facts cases (3.54.0): the README and docs/INDEX.md render from the dict `.agent/facts.json` carries.

A site or dashboard reads `.agent/facts.json`; if a page block computed its own figure, the two could disagree.
"""

from __future__ import annotations

import json
from unittest import mock

PLANTED = 987654


def _rows() -> list[tuple[str, str, bool]]:
    import abtest
    import atlasgen
    import knowledge

    real_m, real_g = abtest.measured_figures(), knowledge.glance_figures()
    with mock.patch.object(abtest, "measured_figures", lambda: {**real_m, "planted": PLANTED}):
        measured = abtest.measured_block()
    with mock.patch.object(knowledge, "glance_figures", lambda: {**real_g, "failures": PLANTED}):
        glance = knowledge.glance_block()
    facts = json.loads(atlasgen.public_facts())
    return [
        (
            "the measured-benefits block prints the planted figure from measured_figures",
            "a README block that computes its own figure beside the facts record",
            f"**{PLANTED}** mistake kinds planted" in measured,
        ),
        (
            "the glance line prints the planted figure from glance_figures",
            "a glance line that counts failure shapes itself",
            f"**{PLANTED}** failure shapes" in glance,
        ),
        (
            "the facts record carries the version and every glance and measured key; check owns its drift",
            "a facts file that drops a figure the site reads",
            facts["schema"] == 1 and {"version", *real_g, *real_m} <= set(facts["facts"]),
        ),
    ]


def run(module) -> None:
    for name, kills, ok in _rows():
        if not ok:
            raise SystemExit(f"FAIL {name}\n  kills: {kills}")
        module.CASES.append((name, kills))
        print(f"  ok    {name}")
