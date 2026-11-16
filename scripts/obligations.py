#!/usr/bin/env python3
"""Task Obligation Ledger: a task's requirements kept outside the model's context, each bound to its proof.

An agent's checklist lives in its context window, and compaction rewrites that window: a requirement stated
early in a long task is the first thing a summary drops, and a "done" the agent remembers is a claim, not a
check. This ledger keeps each obligation on disk, under HEADRON_HOME, as append-only observations:

  add    an obligation: a statement and the procedure that proves it (a microprogram name or a command)
  close  it: the evidence ref that proved it and the git tree that evidence covers

The current state is derived by folding the observations, never stored. An obligation is PROVEN only while its
evidence covers the tree being read; after any commit, or with uncommitted changes, the same evidence reads
UNKNOWN, because it no longer covers what is there. `task.obligations` (scripts/microprogram.py) answers ok only
when every obligation is proven on the current tree, and names the first open one as its next step.

  python scripts/obligations.py add <task> <id> --statement TEXT --check PROCEDURE
  python scripts/obligations.py close <task> <id> --evidence REF [--state proven|not-run|unknown]
  python scripts/obligations.py show <task> [--json]          # exit 0 only when every obligation is proven

proves: an obligation names a procedure before it can be recorded, a proven obligation names evidence and the
  tree it covers, evidence on another, a dirty or an unknown tree reads unknown, the log is append-only, and a corrupt
  line is refused rather than skipped
does_not_prove: that the evidence ref checks what the statement says; the procedure named is the instrument
closed_by: microprogram_test.py (obligation_cases), which plants stale evidence, a procedure-less obligation,
  a done claim with no evidence, a close outside any git tree, a corrupt line, and the ledger read back by a fresh process
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from atlascore import headron_home, text_of

STATES = ("pending", "not-run", "unknown", "proven")
NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,79}")


class LedgerError(ValueError):
    """An observation that may not be recorded, or a ledger line that cannot be read."""


def path(task: str) -> Path:
    if not NAME.fullmatch(task):
        raise LedgerError(f"task {task!r} is not a slug ([a-z0-9._-], 1-80 chars)")
    return headron_home() / "obligations" / f"{task}.jsonl"


UNKNOWN_TREE = "unknown-tree"


def tree(root: Path | None = None) -> str:
    """The tree evidence is bound to: HEAD's tree id, marked `+dirty` when anything is uncommitted.

    The root is the repository the task is in (cwd by default), not Headron's own checkout: an agent using the
    installed tool in another repo binds its evidence to that repo. Outside a git tree it is UNKNOWN_TREE,
    which no evidence ever covers.
    """
    root = Path.cwd() if root is None else root
    head = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=root, capture_output=True, text=True, timeout=30, check=False
    )
    if head.returncode:
        return UNKNOWN_TREE
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=30, check=False
    )
    return head.stdout.strip() + ("+dirty" if dirty.returncode or dirty.stdout.strip() else "")


def read(task: str) -> list[dict[str, Any]]:
    """Every observation, in order. A line that is not one JSON object is refused: skipping it would drop an
    obligation silently, which is the failure this ledger exists to stop."""
    store = path(task)
    if not store.exists():
        return []
    rows = []
    for number, line in enumerate(text_of(store).splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise LedgerError(f"{store}:{number} is not JSON ({error.msg}); repair the line, never delete it") from None
        if not isinstance(row, dict) or not NAME.fullmatch(str(row.get("id", ""))):
            raise LedgerError(f"{store}:{number} names no obligation id")
        rows.append(row)
    return rows


def current(task: str) -> dict[str, dict[str, Any]]:
    """The derived state: each obligation's statement and procedure, plus its latest close."""
    state: dict[str, dict[str, Any]] = {}
    for row in read(task):
        if row.get("op") == "add":
            state[row["id"]] = {"statement": row["statement"], "check": row["check"], "state": "pending"}
        elif row["id"] in state:
            state[row["id"]].update(state=row["state"], evidence=row.get("evidence", ""), tree=row.get("tree", ""))
    return state


def standing(row: dict[str, Any], now: str) -> str:
    """proven only while the evidence covers `now`; proven evidence for another or a dirty tree is unknown."""
    if row["state"] != "proven":
        return row["state"]
    covered = row.get("tree") == now and now != UNKNOWN_TREE and not now.endswith("+dirty")
    return "proven" if covered else "unknown"


def _append(task: str, row: dict[str, Any]) -> dict[str, Any]:
    store = path(task)
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as log:  # append, never rewrite: an earlier close stays as recorded
        log.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def add(task: str, oid: str, statement: str, check: str) -> dict[str, Any]:
    if not NAME.fullmatch(oid):
        raise LedgerError(f"obligation id {oid!r} is not a slug")
    if not statement.strip() or not check.strip():
        raise LedgerError(f"{oid}: an obligation needs a statement and the procedure that proves it")
    if oid in current(task):
        raise LedgerError(f"{oid} is already recorded for {task}; close it, never re-add it")
    return _append(task, {"op": "add", "id": oid, "statement": statement.strip(), "check": check.strip()})


def close(task: str, oid: str, evidence: str, state: str = "proven", at: str | None = None) -> dict[str, Any]:
    if state not in STATES[1:]:
        raise LedgerError(f"{oid}: close state {state!r} is not one of {STATES[1:]}")
    if oid not in current(task):
        raise LedgerError(f"{oid} is not an obligation of {task}; add it first")
    if state == "proven" and not evidence.strip():
        raise LedgerError(f"{oid}: proven names the evidence ref that proved it (a receipt, a log, a commit)")
    at = tree() if at is None else at
    if state == "proven" and (at == UNKNOWN_TREE or at.endswith("+dirty")):
        raise LedgerError(f"{oid}: evidence on {at} covers no committed tree; commit, re-run the check, close")
    return _append(task, {"op": "close", "id": oid, "state": state, "evidence": evidence.strip(), "tree": at})


def report(task: str, now: str) -> tuple[str, dict[str, dict[str, Any]], str]:
    """(status, rows, next) for task.obligations: ok only when every obligation is proven on `now`."""
    rows = {oid: {**row, "state": standing(row, now)} for oid, row in current(task).items()}
    if not rows:
        return "unknown", rows, f"record the task's obligations: `python scripts/obligations.py add {task} <id> ...`"
    open_rows = [(oid, row) for oid, row in rows.items() if row["state"] != "proven"]
    if not open_rows:
        return "ok", rows, ""
    oid, row = open_rows[0]
    status = "unknown" if all(r["state"] == "unknown" for _, r in open_rows) else "refused"
    return status, rows, f"prove {oid}: run `{row['check']}`, then close it with the evidence ref"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="obligations", description=(__doc__ or "obligations").splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("task")
    a.add_argument("id")
    a.add_argument("--statement", required=True)
    a.add_argument("--check", required=True)
    c = sub.add_parser("close")
    c.add_argument("task")
    c.add_argument("id")
    c.add_argument("--evidence", default="")
    c.add_argument("--state", default="proven", choices=STATES[1:])
    s = sub.add_parser("show")
    s.add_argument("task")
    s.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "add":
            print(json.dumps(add(args.task, args.id, args.statement, args.check)))
            return 0
        if args.cmd == "close":
            print(json.dumps(close(args.task, args.id, args.evidence, args.state)))
            return 0
        status, rows, next_step = report(args.task, tree())
    except LedgerError as error:
        print(f"obligations: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"status": status, "obligations": rows, "next": next_step}))
    else:
        print(f"{args.task}: {status}")
        print("\n".join(f"  {row['state']:<8} {oid}: {row['statement']}" for oid, row in rows.items()))
        if next_step:
            print(f"  next: {next_step}")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
