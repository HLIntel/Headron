#!/usr/bin/env python3
"""Does using the atlas actually help? Measured where it can be, and REFUSED where it cannot.

WHY (2.15.0). This repository could prove it was internally consistent and could not prove it
improved anything. A contract that verifies its own documents and never measures an outcome is a
very rigorous way of being unfalsifiable.

WHAT THIS MEASURES, AND WHAT IT WILL NOT PRETEND TO. Four arms are declared — no atlas,
instructions only, route/plan, route/plan plus enforcement — and only two of them can be obtained
by an instrument here. The first is a DECLARED MODEL: the assumption is printed so it can be
attacked, and it is not a measurement. The second needs a real agent making real decisions, so it
is reported `not_run` with the reason, because a blank and a zero read the same in a table and
only one of them is honest.

THE RULES THIS OBEYS, ALL OF WHICH EXIST BECAUSE THEY WERE BROKEN SOMEWHERE ELSE FIRST:
  - K and the chance baseline are printed on every run. A bar cleared over K comparisons yields
    0.05K winners by luck, and a number with no baseline beside it is rhetoric.
  - The held-out set is reported SEPARATELY. A suite you select on is in-sample, and the router
    and the gate table were both written while looking at the fixed set.
  - It measures ROUTING and CONTEXT, not agent success. Those are what this repository actually
    controls; task success belongs to whoever runs the agent, and claiming it here would be
    measuring somebody else's work with my instrument.
"""
from __future__ import annotations

import json
import sys

from agentpolicy import gate_command, required_gates
from atlascore import ROOT, atlas, route_targets, route_with_evidence, tracked

TASKS = "benchmarks/tasks"


def tasks() -> list[dict]:
    """Every declared task, in a stable order. The COUNT is printed, never assumed."""
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((ROOT / TASKS).glob("*.json"))]


def unassisted_model() -> tuple[int, str]:
    """The cost of finding the toolchain WITHOUT a router, as a stated assumption.

    A model, not a measurement, and it is the optimistic one: an agent with no route is assumed to
    read the entry documents and the pack index rather than the whole tree. The pessimistic reading
    — a breadth-first read — is an order of magnitude larger, and using it would flatter this
    repository with a number nobody attacked.
    """
    index = [p for p in tracked()
             if p.suffix.lower() == ".md" and p.is_file() and not p.is_symlink()
             and (p.name == "README.md" or p.parent == ROOT)]
    total = sum(p.stat().st_size for p in index)
    return total, (f"an agent with no router reads the {len(index)} index and root documents to "
                   "find which toolchain owns a file; the pessimistic reading is the whole tree, "
                   "and using that would flatter this result with a number nobody attacked")


def assisted(task: dict) -> dict:
    """One task under the route/plan arm: what the atlas returns, and whether it is right."""
    route, rule, _ = route_with_evidence(str(task["target"]))
    files = [f"languages/{route}/README.md", f"languages/{route}/OPERATING.md",
             f"languages/{route}/tools.yaml"] if route else []
    gates = required_gates({"change_class": task.get("change_class"), "risk_modifiers": []})
    runnable = sum(1 for g in gates if route and gate_command(route, g)[0])
    return {
        "route_correct": route == task.get("expected_route"),
        "rule_correct": rule.split(" ")[0] == task.get("expected_resolved_by"),
        "context_bytes": sum((ROOT / f).stat().st_size for f in files if (ROOT / f).exists()),
        "files_named": len(files),
        "gates_resolved": runnable,
        "gates_total": len(gates),
    }


def report() -> dict:
    """The four arms, with each one's provenance stated rather than implied."""
    rows = tasks()
    fixed = [t for t in rows if not t.get("held_out")]
    held = [t for t in rows if t.get("held_out")]
    measured = {t["task_id"]: assisted(t) for t in rows}
    unassisted_bytes, assumption = unassisted_model()
    routable = sum(1 for t in rows if t.get("expected_route"))
    # THE CHANCE BASELINE. Guessing uniformly among the packs gets the routable ones right at
    # 1/len(packs) each and the unroutable ones right only by refusing, which a guesser never does.
    chance = routable / max(len(route_targets()), 1)
    return {
        "schema": 1,
        "atlas_version": str(atlas().get("version")),
        "k": len(rows) * 2,
        "tasks": {"total": len(rows), "held_out": len(held)},
        "baseline": {
            "routes_correct_by_chance": round(chance, 3),
            "note": (f"{routable} of {len(rows)} targets are routable; a uniform guess over "
                     f"{len(route_targets())} packs expects {chance:.3f} correct, and never "
                     "refuses, so it scores zero on every target whose right answer is no route"),
        },
        "arms": [
            {"arm": "no_atlas", "obtained_by": "declared_model", "model": assumption,
             "context_bytes": unassisted_bytes, "files_named": 0,
             "routes_correct": 0, "routes_correct_held_out": 0, "rules_correct": 0,
             "gates_resolved": 0, "gates_total": 0},
            {"arm": "instructions_only", "obtained_by": "not_run",
             "why_not_run": "it needs a real agent reading the entry documents and DECIDING; "
                            "simulating that decision here would be measuring my own assumption "
                            "about it and reporting the assumption as a result"},
            {"arm": "route_plan", "obtained_by": "instrument",
             "context_bytes": sum(m["context_bytes"] for m in measured.values()),
             "files_named": sum(m["files_named"] for m in measured.values()),
             "routes_correct": sum(1 for t in fixed if measured[t["task_id"]]["route_correct"]),
             "routes_correct_held_out": sum(1 for t in held if measured[t["task_id"]]["route_correct"]),
             "rules_correct": sum(1 for m in measured.values() if m["rule_correct"]),
             "gates_resolved": sum(m["gates_resolved"] for m in measured.values()),
             "gates_total": sum(m["gates_total"] for m in measured.values())},
            {"arm": "route_plan_enforced", "obtained_by": "not_run",
             "why_not_run": "the controls REFUSE; they do not improve a route. Their effect is "
                            "measured by agent_test.py, which plants a defect per control — "
                            "counting them here would double-count the same evidence"},
        ],
    }


def main(argv: list[str] | None = None) -> int:
    record = report()
    if "--json" in (argv if argv is not None else sys.argv[1:]):
        print(json.dumps(record, indent=2))
    else:
        print(f"atlas benchmark {record['atlas_version']} — K={record['k']}, "
              f"{record['tasks']['total']} tasks ({record['tasks']['held_out']} held out)")
        for arm in record["arms"]:
            if arm["obtained_by"] == "not_run":
                print(f"  {arm['arm']:<22} NOT RUN — {arm['why_not_run']}")
                continue
            tag = "MODEL" if arm["obtained_by"] == "declared_model" else "measured"
            print(f"  {arm['arm']:<22} [{tag}] context {arm['context_bytes']:>7} B | "
                  f"files {arm['files_named']:>3} | routes {arm['routes_correct']}/"
                  f"{record['tasks']['total'] - record['tasks']['held_out']} fixed, "
                  f"{arm['routes_correct_held_out']}/{record['tasks']['held_out']} HELD OUT | "
                  f"gates {arm['gates_resolved']}/{arm['gates_total']}")
            if arm["obtained_by"] == "declared_model":
                print(f"  {'':<22} assumption: {arm['model']}")
        print(f"  chance baseline: {record['baseline']['routes_correct_by_chance']} correct — "
              f"{record['baseline']['note']}")
    wrong = [t["task_id"] for t in tasks() if not assisted(t)["route_correct"]]
    for task_id in wrong:
        print(f"- WRONG ROUTE: {task_id}")
    print("SCOPE: routing and context, never agent success. Task success belongs to whoever runs")
    print("       the agent; claiming it here would measure somebody else's work with my ruler.")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
