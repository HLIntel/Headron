#!/usr/bin/env python3
"""What this repository HANDS OVER before it is asked anything — measured, and ratcheted.

WHY (2.10.0). Measured on this tree: 159 markdown files, 45% of the bytes. That number alone is
rhetoric in both directions. 78 of those files are language packs no session opens until a route
names one, so "45% prose" describes a library, not a blob — and at the same time nothing here
measured the part that actually costs a reader anything, which is what a runtime loads with no
route resolved and no question asked. An entry path can grow a page at a time while every other
count in this contract stays green.

SO THE INSTRUMENT MEASURES THE ENTRY, NOT THE TREE. Two paths are declared in
`atlas.yaml/context_policy/entry_paths` — what an agent runtime loads automatically, and what a
person opens first — each with a byte budget set to its own measured size. The budget is a
RATCHET: it may fall and never rise, so the only way to add to an entry document is to take
something out of it, and `atlas.py check` refuses a raise rather than leaving it to review.

WHAT IT DOES NOT PROVE: that the bytes on the entry path are the RIGHT bytes. A small entry
document that sends every reader to the wrong place costs more than a large one that routes
correctly, and no byte count can see the difference. That is what the router's own evidence line
and a human reviewer are for.
"""
from __future__ import annotations

import sys

from atlascore import ROOT, atlas, tracked


def paths() -> dict:
    return ((atlas().get("context_policy") or {}).get("entry_paths")) or {}


def measure() -> dict[str, dict]:
    """Per declared entry path: its files, their sizes, the total and the budget it is held to."""
    report: dict[str, dict] = {}
    for name, spec in paths().items():
        rows = []
        for rel_path in (spec or {}).get("files") or []:
            path = ROOT / str(rel_path)
            rows.append((str(rel_path), path.stat().st_size if path.exists() else -1))
        report[name] = {
            "files": rows,
            "bytes": sum(size for _, size in rows if size > 0),
            "budget": int((spec or {}).get("budget_bytes") or 0),
            "slack": int((spec or {}).get("slack_bytes") or 0),
            "why": str((spec or {}).get("why") or ""),
        }
    return report


def lazy_bytes() -> tuple[int, int]:
    """Everything reachable ONLY after a route, so the entry cost has something to be read against."""
    entry = {str(f) for spec in paths().values() for f in (spec or {}).get("files") or []}
    total = count = 0
    for path in tracked():
        if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".md":
            continue
        if path.resolve().relative_to(ROOT.resolve()).as_posix() in entry:
            continue
        total += path.stat().st_size
        count += 1
    return total, count


def entry_cost_errors() -> list[str]:
    """A budget may only fall, and a path may not name a file the tree does not have."""
    errors: list[str] = []
    if not paths():
        return ["atlas.yaml/context_policy declares no entry_paths — the one cost a reader pays "
                "before asking anything would then be measured by nothing"]
    for name, row in measure().items():
        for rel_path, size in row["files"]:
            if size < 0:
                errors.append(f"context_policy/entry_paths/{name} names {rel_path}, which does not exist")
        if not row["budget"]:
            errors.append(f"context_policy/entry_paths/{name} declares no budget_bytes — an entry "
                          "path with no ceiling grows a page at a time and nothing says so")
        elif row["bytes"] > row["budget"]:
            errors.append(f"entry path '{name}' is {row['bytes']} bytes against a budget of "
                          f"{row['budget']} — the ratchet only falls: take something OUT of the "
                          "entry path, or move it behind a route")
        elif row["budget"] - row["bytes"] > row["slack"]:
            errors.append(f"entry path '{name}' measures {row['bytes']} against a budget of "
                          f"{row['budget']} — {row['budget'] - row['bytes']} bytes of slack, over the "
                          f"declared {row['slack']}. Lower the budget to what it now costs, or the "
                          "next addition is absorbed by the gap instead of being refused by it")
    return errors


def main(argv: list[str] | None = None) -> int:
    report = measure()
    for name, row in report.items():
        print(f"entry path '{name}' — {row['why']}")
        for rel_path, size in row["files"]:
            print(f"  {size:>7} B  ~{max(size, 0) // 4:>6} tok  {rel_path}")
        print(f"  {row['bytes']:>7} B  ~{row['bytes'] // 4:>6} tok  TOTAL — budget {row['budget']}, "
              f"slack {row['budget'] - row['bytes']}/{row['slack']}")
    lazy, files = lazy_bytes()
    handed = sum(r["bytes"] for r in report.values())
    print(f"handed over before a route: {handed} B (~{handed // 4} tok)")
    print(f"reachable only through a route: {lazy} B across {files} documents — "
          f"{lazy / max(handed, 1):.1f}x the entry path, and none of it is read unasked")
    problems = entry_cost_errors()
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: bytes, not judgement. A short entry document that sends every reader to the")
    print("       wrong place costs more than a long one that routes correctly, and no byte")
    print("       count can tell them apart — the router's evidence line and a reviewer can.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
