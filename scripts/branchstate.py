#!/usr/bin/env python3
"""Unpushed work, bounded by what actually grows — not by how many branches hold it.

MEASURED AT 2.17.0, AND THE FIRST ANSWER WAS WRONG. The question asked was "cap at four branches,
or five, or six?" This tree had THREE branches and TWO worktrees, so every one of those caps was
already satisfied and none of them would ever have fired. What had actually accumulated was eight
commits over roughly three hours, on ONE branch, none of them pushed — so a branch-count cap would
have printed a clean pass over exactly the risk it was asked to bound.

That is the same shape as a count-capped rotation over growing items: the container count is not
the quantity. What is lost when a worktree is destroyed is COMMITS and TIME, so those are what is
bounded here.

WHY THESE NUMBERS. The commit cap is set from the measured session: eight commits means a cap of
five fires ONCE, in the middle, when acting on it is still cheap — while a cap of three would have
fired three times in the same session, and a guard that fires three times an hour is a guard that
gets silenced. The age cap is under the measured three hours for the same reason: it should
interrupt before the work is a session old, not after.

IT NEVER PUSHES ANYTHING. Pushing is an outward-facing act on somebody's repository, and an
instrument that did it unasked would be exactly the kind of unattended side effect the agent
controls exist to refuse. This REPORTS, and the exit code is the verdict.
"""
from __future__ import annotations

import subprocess
import sys
import time

from atlascore import ROOT, atlas


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return done.stdout.strip() if done.returncode == 0 else ""


def bound() -> dict:
    return ((atlas().get("branch_policy") or {}).get("unpushed_bound")) or {}


def branches() -> list[dict]:
    """Every local branch, with what it holds that no remote does, and how old that work is."""
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    rows: list[dict] = []
    for name in _git("for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines():
        upstream = _git("rev-parse", "--abbrev-ref", f"{name}@{{upstream}}")
        # AGAINST ITS OWN UPSTREAM WHERE THERE IS ONE, against the base where there is not: a
        # branch nothing tracks holds ALL of its work unpushed, and comparing it to the base is
        # the only honest reading of that.
        reference = upstream or f"origin/{base}"
        unpushed = _git("rev-list", "--count", f"{reference}..{name}")
        oldest = _git("log", "-1", "--format=%ct", f"{reference}..{name}")
        rows.append({
            "branch": name,
            "tracks": upstream or None,
            "unpushed": int(unpushed) if unpushed.isdigit() else 0,
            "age_hours": round((time.time() - int(oldest)) / 3600, 1) if oldest.isdigit() else 0.0,
        })
    return rows


def unpushed_errors() -> list[str]:
    """What exceeds the declared bound, named per branch so the remedy is obvious."""
    limits = bound()
    if not limits:
        return ["branch_policy/unpushed_bound is not declared, so work accumulates unpushed and "
                "nothing says how much is too much until a worktree is gone"]
    rows = [r for r in branches() if r["unpushed"]]
    problems: list[str] = []
    for row in rows:
        if row["unpushed"] > int(limits.get("max_commits", 0)):
            problems.append(f"{row['branch']}: {row['unpushed']} unpushed commits against a bound "
                            f"of {limits['max_commits']} — push, or say why this one waits")
        if row["age_hours"] > float(limits.get("max_age_hours", 0)):
            problems.append(f"{row['branch']}: oldest unpushed work is {row['age_hours']}h old "
                            f"against a bound of {limits['max_age_hours']}h")
    if len(rows) > int(limits.get("max_branches_with_unpushed", 0)):
        problems.append(f"{len(rows)} branches hold unpushed work against a bound of "
                        f"{limits['max_branches_with_unpushed']} — one of them is forgotten, and "
                        "the one that is forgotten is never the one being looked at")
    if not str(limits.get("why") or "").strip():
        problems.append("branch_policy/unpushed_bound states no reason for its numbers, which "
                        "makes them a preference rather than a measurement")
    return problems


def main(argv: list[str] | None = None) -> int:
    limits = bound()
    rows = branches()
    for row in sorted(rows, key=lambda r: -r["unpushed"]):
        state = "pushed" if not row["unpushed"] else f"{row['unpushed']} unpushed, {row['age_hours']}h"
        print(f"{row['branch']:<52} {state:<26} tracks {row['tracks'] or 'NOTHING'}")
    holding = [r for r in rows if r["unpushed"]]
    print(f"{len(rows)} branches, {len(holding)} holding unpushed work "
          f"({sum(r['unpushed'] for r in holding)} commits) against bounds: "
          f"{limits.get('max_commits')} commits, {limits.get('max_age_hours')}h, "
          f"{limits.get('max_branches_with_unpushed')} branches")
    problems = unpushed_errors()
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: it REPORTS. Pushing is an outward-facing act on a repository, and an instrument")
    print("       that did it unasked is the unattended side effect the agent controls refuse.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
