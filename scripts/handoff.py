#!/usr/bin/env python3
"""A bounded, artifact-specific handoff — route evidence instead of a repository dump.

WHY. `thea delegate` names what every brief needs, but a second model still had to infer which
file, guide and gates the first model meant. That is where context expands: it opens the tree to
find a route, then receives more files than the task needs. This command makes the useful edges
explicit: artifact -> route evidence -> three route documents -> acceptance commands. Its output
is a capsule another model can act on, not a claim that the delegate's result is correct.

    thea handoff scripts/intake.py --task "tighten prompt routing"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from atlascore import ROOT, atlas, route_with_evidence


def capsule(path: str, task: str | None = None, change: str = "source_change") -> dict:
    """Build a route-scoped brief; refuse an unknown artifact or change class."""
    target = Path(path) if Path(path).is_absolute() else ROOT / path
    if not target.is_file() or not target.resolve().is_relative_to(ROOT):
        raise ValueError(f"REFUSED: {path} is not a file inside this atlas")
    relative = target.resolve().relative_to(ROOT).as_posix()
    route, rule, evidence = route_with_evidence(relative)
    if not route:
        raise ValueError(f"REFUSED: {path} has no declared route")
    profiles = (atlas().get("verification_policy") or {}).get("profiles") or {}
    if change not in profiles:
        raise ValueError(f"REFUSED: {change} is not a declared change class")
    from agentpolicy import required_gates  # noqa: PLC0415
    from atlas import gate_record  # noqa: PLC0415

    gates = sorted(required_gates({"change_class": change}))
    acceptance = [{"gate": gate, "command": gate_record(relative, gate).get("argv") or []} for gate in gates]
    context = [f"languages/{route}/README.md", f"languages/{route}/OPERATING.md", f"languages/{route}/tools.yaml"]
    contract = atlas().get("delegation_contract") or {}
    required = contract.get("required") or {}
    return {
        "schema": 1,
        "command": "handoff",
        "goal": task or "<the outcome this artifact serves>",
        "scope": [relative],
        "route": {"language": route, "rule": rule, "evidence": evidence},
        "context": context,
        "acceptance": acceptance,
        "returns": (required.get("returns") or {}).get("ask", "path:line and a verdict"),
        "forbidden": (required.get("forbidden") or {}).get("ask", "do not widen scope"),
        "read_only": (required.get("read_only") or {}).get("ask", "THEA_READ_ONLY=1"),
    }


def main(argv: list[str]) -> int:
    path = next((arg for arg in argv if not arg.startswith("--")), "")
    task = argv[argv.index("--task") + 1] if "--task" in argv else None
    change = argv[argv.index("--change") + 1] if "--change" in argv else "source_change"
    try:
        record = capsule(path, task, change)
    except (IndexError, ValueError) as exc:
        print(exc)
        return 2
    if "--json" in argv:
        print(json.dumps(record, indent=2))
        return 0
    print(f"goal      {record['goal']}\nscope     {', '.join(record['scope'])}")
    print(f"route     {record['route']['language']} ({record['route']['rule']}: {record['route']['evidence']})")
    print("context   " + ", ".join(record["context"]))
    print("accept    " + "; ".join(f"{row['gate']}: {' '.join(row['command'])}" for row in record["acceptance"]))
    print(f"returns   {record['returns']}\nforbidden {record['forbidden']}\nread-only {record['read_only']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
