"""The brief a delegated agent needs — `thea delegate [--task "..."]`. Under-specification is the failure.

WHY (3.23.0). Thea hands work to subagents, to opencode, to a free model for a second opinion. Measured
across 200 traces of 7 multi-agent frameworks (MAST, arXiv:2503.13657), the two largest failure buckets
are SPECIFICATION issues and INTER-AGENT MISALIGNMENT — together most of what goes wrong, and neither is
a model capability problem. They are briefs that did not say enough, and results taken on trust.

So a handoff here carries six things, and `delegation_contract` in atlas.yaml declares them once:
  goal        one sentence, the outcome — not the method, which is the delegate's to choose
  scope       the files or directories it may read and change; everything else is out
  acceptance  how ITS work is judged, in a command or an observable, never "do a good job"
  returns     the shape of the answer, so the caller can act on it without re-reading the work
  forbidden   what it must not do, including the actions that look helpful (widening scope, "fixing
              while here", editing what it was asked to review)
  read_only   THEA_READ_ONLY=1 for anything that is not explicitly the editing agent — an audit that
              can write is an audit that raced the editor (measured here at 3.9.0)

AND THE HALF EVERY FRAMEWORK GETS WRONG: what comes back is a HYPOTHESIS, not a result. It is confirmed
by an instrument in this repository or it is not confirmed. This file prints that line every time.
"""
from __future__ import annotations

import json
import sys

from atlascore import atlas


def brief(task: str | None = None) -> dict:
    spec = atlas().get("delegation_contract") or {}
    fields = spec.get("required") or {}
    return {"schema": 1, "command": "delegate", "task": task or "<what the delegate is for>",
            "brief": {name: (row or {}).get("ask", "") for name, row in fields.items()},
            "why": {name: (row or {}).get("why", "") for name, row in fields.items()},
            "on_return": spec.get("on_return") or []}


def main(argv: list[str]) -> int:
    task = argv[argv.index("--task") + 1] if "--task" in argv else None
    record = brief(task)
    if "--json" in argv:
        print(json.dumps(record, indent=2))
        return 0
    print(f"delegating: {record['task']}\nevery brief carries all six — an absent one is the most measured cause of a wasted run\n")
    for name, ask in record["brief"].items():
        print(f"{name:<11} {ask}")
        print(f"{'':<11}  why: {record['why'][name]}")
    print()
    for line in record["on_return"]:
        print(f"on return: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
