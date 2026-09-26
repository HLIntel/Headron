#!/usr/bin/env python3
"""The time-boxed session, declared once and printed as a clock — `thea cadence [--minutes N]`.

WHY (3.22.0). The nightly sessions carried their schedule as prose inside a scheduled-task file: nothing
checked it, nothing else could read it, and a second copy would drift the day either was edited. It is a
declaration now (atlas.yaml/cadence), so the phases, the reserve and the expiry rule are one source that
`declcheck.cadence_errors` refuses when it stops adding up.

WHAT THE SHAPE IS FROM, and what it is NOT. Researched at 3.22.0:
  - Phases over free agency. Agentless (arXiv:2407.01489) took the top open-source SWE-bench Lite score
    of its time with a FIXED localize -> repair -> validate pipeline, the model not choosing control flow.
  - A verification budget RESERVED at the start, never a residual. "Premature commitment" is the measured
    failure of coding agents — stopping at the first visible signal of progress while tests still fail;
    gating on evidence recovered 4.8-11.8pp on SWE-bench Verified (arXiv:2607.28815).
  - WIP = 1. Throughput is capped, so work-in-progress is the only lever (Little's Law); and Anthropic's
    own multi-agent report says coding has few truly parallelisable parts, unlike research.
  - Most of Scrum does NOT transfer. Its ceremonies coordinate HUMANS; a solo agent simulating a team pays
    the coordination cost and gets none of the independence (MAST, arXiv:2503.13657, measures ~37% of
    multi-agent failures as inter-agent misalignment). Kept: the time-box, an external Definition of Done,
    and the daily scrum's FUNCTION as a clock check. Dropped: roles, estimation, velocity, demos.
  - The box LENGTH is not evidence-backed. A systematic review of agile studies finds no consensus on
    iteration length; 30 minutes is a cost and blast-radius choice, and `reserve_held` is what moves it.
"""
from __future__ import annotations

import json
import sys

from atlascore import atlas


def schedule(minutes: float | None = None) -> dict:
    """The declared phases as a clock for a box of `minutes` — the declaration scaled, never re-typed."""
    spec = atlas().get("cadence") or {}
    box = float(minutes or spec.get("box_minutes") or 30)
    weights = spec.get("phases") or []
    total = sum(float(p.get("weight") or 0) for p in weights) or 1.0
    rows, at = [], 0.0
    for phase in weights:
        span = box * float(phase.get("weight") or 0) / total
        rows.append({"id": phase["id"], "starts": round(at, 1), "ends": round(at + span, 1),
                     "minutes": round(span, 1), "does": phase.get("does", ""),
                     "exits": phase.get("exits", ""), "reserve": bool(phase.get("reserve"))})
        at += span
    return {"schema": 1, "command": "cadence", "box_minutes": box, "wip": spec.get("wip"),
            "phases": rows, "checkpoints_at": [round(box * float(c), 1) for c in spec.get("checkpoints") or []],
            "definition_of_done": spec.get("definition_of_done") or [],
            "on_expiry": spec.get("on_expiry") or [], "never_under_pressure": spec.get("never_under_pressure") or [],
            "measure": spec.get("measure") or []}


def main(argv: list[str]) -> int:
    minutes = float(argv[argv.index("--minutes") + 1]) if "--minutes" in argv else None
    plan = schedule(minutes)
    if "--json" in argv:
        print(json.dumps(plan, indent=2))
        return 0
    print(f"cadence: a {plan['box_minutes']:g}-minute box, WIP {plan['wip']} — one change, one hypothesis, one pull request")
    for row in plan["phases"]:
        mark = "  [RESERVE, entered on the clock whatever the state]" if row["reserve"] else ""
        print(f"{row['starts']:>5.1f}-{row['ends']:<5.1f} {row['id']:<10} {row['does']}{mark}")
        print(f"{'':>11} exit: {row['exits']}")
    print("checkpoints at " + ", ".join(f"{c:g}m" for c in plan["checkpoints_at"])
          + " — is the declared change still reachable inside the reserve? If not, cut scope NOW.")
    print("done when: " + " AND ".join(plan["definition_of_done"]))
    for line in plan["on_expiry"]:
        print(f"on expiry: {line}")
    for line in plan["never_under_pressure"]:
        print(f"NEVER:     {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
