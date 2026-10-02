"""The brief a delegated agent needs — `thea delegate [--task "..."]`. Under-specification is the failure.

WHY (3.23.0). Thea hands work to subagents, to opencode, to a free model for a second opinion. Measured
across 200 traces of 7 multi-agent frameworks (MAST, arXiv:2503.13657), the two largest failure buckets
are SPECIFICATION issues and INTER-AGENT MISALIGNMENT — together most of what goes wrong, and neither is
a model capability problem. They are briefs that did not say enough, and results taken on trust.

So a handoff carries six things, each with its reason, declared ONCE in atlas.yaml/delegation_contract.

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
            # THE LABELS TRAVEL WITH THE BRIEF, not only with the answer. A delegate told to label
            # its claims returns claims that can be acted on differently; one told only "be
            # accurate" returns a wall of equally-weighted sentences, and the caller then either
            # re-runs everything (spending what the delegation saved) or trusts everything.
            "return_labels": {name: (row or {}).get("means", "")
                              for name, row in (spec.get("return_labels") or {}).items()},
            "caller_owes": {name: (row or {}).get("caller_owes", "")
                            for name, row in (spec.get("return_labels") or {}).items()},
            "on_return": spec.get("on_return") or []}


def main(argv: list[str]) -> int:
    task = argv[argv.index("--task") + 1] if "--task" in argv else None
    record = brief(task)
    print(json.dumps(record, indent=2) if "--json" in argv else render(record))
    return 0


def render(record: dict) -> str:
    """Static brief FIRST, task LAST, in XML tags (REPORTED, Anthropic's prompting guide: a stable prefix
    caches, and a query after its context answers better). A task printed first is a cache miss every time."""
    rows = [f"<{name}>{ask}\n  why: {record['why'][name]}</{name}>" for name, ask in record["brief"].items()]
    returns = "\n".join(record["on_return"])
    return ("<brief>every brief carries all six — an absent one is the most measured cause of a wasted run\n"
            + "\n".join(rows) + f"</brief>\n<on_return>\n{returns}\n</on_return>\n<task>{record['task']}</task>")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
