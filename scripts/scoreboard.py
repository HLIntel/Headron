#!/usr/bin/env python3
"""What the benchmarks measure, as a floor that only rises: one row per metric, simple enough to act on.

WHY (3.14.0). The measured benefits were a report: a table on the landing page and nothing that failed
when a number fell. A reviewer put it plainly — the figures are real, and nothing holds them. Each row
here is (metric, now, floor, headroom). Below its floor the build fails, because the benefit regressed.
Above its floor by more than `slack`, it fails too, and says what to raise the floor to — the same
only-rises ratchet the byte budgets use, so a gain is locked in the run that earned it.

  python scripts/scoreboard.py [--json]      the table; exit 1 on any row out of bounds

A number is the WORST model in the record (min over models), never the mean: a floor a mean clears
while one model regressed is a floor that one model walks under.
"""
from __future__ import annotations

import json
import sys

from atlascore import ROOT, atlas


def _walk(node, parts: list[str]):
    """Every value at a dotted path; `*` fans out over a mapping's values."""
    if not parts:
        yield node
        return
    head, rest = parts[0], parts[1:]
    if head == "*":
        for value in (node or {}).values():
            yield from _walk(value, rest)
    elif isinstance(node, dict) and head in node:
        yield from _walk(node[head], rest)


def value_of(row: dict) -> float | None:
    """The worst ratio at the row's path: `num`/`den` fields of each record it reaches. None = unmeasured."""
    record = json.loads((ROOT / row["file"]).read_text(encoding="utf-8"))
    ratios = [float(r[row["num"]]) / float(r[row["den"]]) for r in _walk(record, row["path"].split(".") if row["path"] else [])
              if isinstance(r, dict) and r.get(row["den"])]
    return min(ratios) if ratios else None


def rows() -> list[dict]:
    out = []
    for row in atlas().get("benchmark_floors") or []:
        now = value_of(row)
        floor, slack = float(row["floor"]), float(row.get("slack", 0.05))
        verdict = ("UNMEASURED" if now is None else "BELOW" if now < floor
                   else "RAISE" if now - floor > slack else "OK")
        out.append({"id": row["id"], "now": None if now is None else round(now, 3), "floor": floor,
                    "headroom": None if now is None else round(now - floor, 3), "verdict": verdict,
                    "measured_by": row.get("measured_by", "")})
    return out


def floor_errors() -> list[str]:
    errors = [] if atlas().get("benchmark_floors") else ["atlas.yaml declares no benchmark_floors: the measured benefits hold nothing"]
    for r in rows():
        if r["verdict"] == "BELOW":
            errors.append(f"benchmark {r['id']} is {r['now']} against a floor of {r['floor']} — the benefit regressed; "
                          f"re-run {r['measured_by']} and fix the cause, never the floor")
        elif r["verdict"] == "RAISE":
            errors.append(f"benchmark {r['id']} is {r['now']}, {r['headroom']} over its floor of {r['floor']} — raise the "
                          f"floor to {r['now']}; a gain left below the slack is lost the next time it slips")
        elif r["verdict"] == "UNMEASURED":
            errors.append(f"benchmark {r['id']} reads nothing at its path — a floor over no record holds nothing")
    return errors


def main(argv: list[str]) -> int:
    table = rows()
    if "--json" in argv:
        print(json.dumps({"schema": 1, "command": "scoreboard", "atlas_version": str(atlas().get("version")),
                          "rows": table}, indent=2))
    else:
        print(f"{'metric':<34}{'now':>7}{'floor':>7}{'headroom':>10}  verdict")
        for r in table:
            print(f"{r['id']:<34}{str(r['now']):>7}{r['floor']:>7}{str(r['headroom']):>10}  {r['verdict']}")
        print("SCOPE: recorded runs, worst model per metric; a floor holds a record, it does not re-run a model")
    return 1 if floor_errors() else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
