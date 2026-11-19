#!/usr/bin/env python3
"""Task Obligation Ledger: a task's requirements kept outside the model's context, each bound to its proof.

An agent's checklist lives in its context window, and compaction rewrites that window: a requirement stated
early in a long task is the first thing a summary drops, and a "done" the agent remembers is a claim, not a
check. This ledger keeps each obligation on disk, under HEADRON_HOME, as append-only observations:

  add    an obligation: a statement and the procedure that proves it (a microprogram name or a command)
  cover  the changed files an extracted obligation answers for
  close  it: the evidence ref that proved it and the git tree that evidence covers

An agent need not type its own list. `extract` derives it from a task contract (scripts/headronlang.py) and the
files the task changed: each changed file x required gate resolves through the atlas as `headron gate` does, and
each acceptance check is owed. `coverage` names every way the ledger falls short of that list.

The current state is derived by folding the observations, never stored. An obligation is PROVEN only while its
evidence covers the tree being read; after any commit, or with uncommitted changes, the same evidence reads
UNKNOWN, because it no longer covers what is there. `task.obligations` (scripts/microprogram.py) answers ok only
when every obligation is proven on the current tree, and names the first open one as its next step.

  python scripts/obligations.py add <task> <id> --statement TEXT --check PROCEDURE
  python scripts/obligations.py close <task> <id> --evidence REF [--state proven|not-run|unknown]
  python scripts/obligations.py show <task> [--json]          # exit 0 only when every obligation is proven
  python scripts/obligations.py extract <task> <contract> [--root DIR]   # exit 1 when a changed file is a gap
  python scripts/obligations.py coverage <task> <contract> [--root DIR]  # exit 0 only when the ledger is whole

proves: an obligation names a procedure before it can be recorded, a proven obligation names evidence and the
  tree it covers, evidence on another, a dirty or an unknown tree reads unknown, the log is append-only, and a corrupt
  line is refused rather than skipped; extraction is idempotent, a changed file no route reads is a gap, a file
  changed after extraction (committed or not), a dropped obligation and a drifted check each read short, a drift
  refuses extract, and a contract with no base_commit is refused
does_not_prove: that the evidence ref checks what the statement says (the procedure named is the instrument); what
  the objective's prose asks for; that a deleted file needed nothing; that the changes stay inside allowed_paths;
  extract chdirs the whole process into the task root while it resolves gates (an overrun leaves it there)
closed_by: microprogram_test.py (obligation_cases), which plants stale evidence, a procedure-less obligation,
  a done claim with no evidence, a close outside any git tree, a corrupt line, and the ledger read back by a fresh process;
  (extract_cases), which plants a dropped obligation, an unrouted file, a file changed and then committed after
  extraction, a drifted check, a second extraction, a contract with no base_commit and a root outside any git tree
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from atlascore import atlas as declared_atlas
from atlascore import headron_home, route_for, text_of

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
        elif row.get("op") == "cover" and row["id"] in state:  # extract: the files this obligation answers for
            held = set(state[row["id"]].get("paths") or ()) | {str(p) for p in row.get("paths") or ()}
            state[row["id"]]["paths"] = sorted(held)
        elif row.get("op") == "close" and row["id"] in state:
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


def _contract(contract_path: str | Path) -> dict[str, Any]:
    import headronlang  # noqa: PLC0415

    try:
        contract = headronlang.load_contract(contract_path)
    except (OSError, ValueError, SystemExit) as error:
        raise LedgerError(f"{contract_path}: not a readable task contract ({error})") from None
    if not isinstance(contract, dict):
        raise LedgerError(f"{contract_path}: a task contract is one object")
    return contract


def _changed(contract: dict[str, Any], root: Path) -> list[str]:
    """Every file the task changed since its base_commit, committed or not, plus untracked files. A contract with
    no base_commit is refused: against HEAD, a change committed after extraction would vanish from the list. A
    deleted file owes no gate; a git that cannot answer refuses, since no files would pass every check."""
    from atlascore import diff_names, ls_files  # noqa: PLC0415

    if not contract.get("base_commit"):
        raise LedgerError("the task contract names no base_commit; without it a committed change is invisible")
    base = str(contract["base_commit"])
    try:
        tracked = diff_names(root, "--diff-filter=d", base)
    except ValueError as error:
        raise LedgerError(f"cannot list what changed against {base} in {root}: {error}") from None
    try:
        new = ls_files(root, flags=("--others", "--exclude-standard"))
    except SystemExit as error:  # the one reader refuses a git that cannot answer; here it is a ledger error
        raise LedgerError(f"cannot list untracked files in {root}: {error}") from None
    return sorted(set(tracked) | set(new))


def _gates(contract: dict[str, Any]) -> list[str]:
    import agentpolicy  # noqa: PLC0415

    try:
        gates = agentpolicy.required_gates(contract)
    except SystemExit as error:  # an unknown class or modifier refuses there; here it is a ledger error
        raise LedgerError(str(error)) from None
    return list(dict.fromkeys([*gates, *(str(g) for g in contract.get("required_gates") or [])]))


def _accept_id(check: str) -> str:
    slug = re.sub(r"[^a-z0-9._]+", "-", check.lower()).strip("-._")[:60]
    exact = slug == check
    return f"accept.{slug}" if exact else f"accept.{slug or 'check'}.{hashlib.sha256(check.encode()).hexdigest()[:6]}"


def owed(contract: dict[str, Any], root: Path) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    """What a contract owes on the files it changed: ({id: statement, check, paths}, gaps, not owed).

    Each changed file x required gate resolves through the atlas, as `headron gate` does. A runnable gate is an
    obligation keyed by its command, so one `pytest` answers for every file it covers. A gate the repository does
    not adopt (unplaced) is not owed. A gate the atlas declares has no tool for that language (absent) is listed as
    unprovable: named, never a pass, never an obligation, since no run could close it. A file no route reads
    (undeclared) is a GAP: the task touched something the contract cannot see. acceptance.required_checks are owed."""
    import atlas  # noqa: PLC0415

    owe: dict[str, dict[str, Any]] = {}
    gaps: list[str] = []
    not_owed: list[str] = []
    gates = _gates(contract)
    with contextlib.chdir(root):  # gate_record reads a relative path from the working directory
        for name in _changed(contract, root):
            for gate in gates:
                record = atlas.gate_record(name, gate)
                if record["state"] == "runnable" and record["argv"]:
                    cmd = atlas._pasteable(record)  # noqa: SLF001 -- the one renderer `headron gate` prints
                    oid = f"gate.{gate}.{hashlib.sha256(cmd.encode()).hexdigest()[:8]}"
                    owe.setdefault(oid, {"statement": f"{gate} passes", "check": cmd, "paths": []})["paths"].append(
                        name
                    )
                elif record["state"] in ("unplaced", "absent"):
                    label = "not adopted" if record["state"] == "unplaced" else "unprovable"
                    not_owed.append(f"{gate} {name}: {label}, {record['why']}")
                else:
                    gaps.append(f"{gate} {name}: {record['state']}, {record['why']}")
    for check in (contract.get("acceptance") or {}).get("required_checks") or []:
        owe[_accept_id(str(check))] = {"statement": "acceptance check passes", "check": str(check), "paths": []}
    return owe, gaps, not_owed


def _drift(oid: str, row: dict[str, Any], want: dict[str, Any]) -> str:
    if (row["statement"], row["check"]) == (want["statement"], want["check"]):
        return ""
    return f"{oid}: recorded as {row['check']!r}, the contract now owes {want['check']!r}"


def extract(task: str, contract_path: str | Path, root: Path | None = None) -> dict[str, Any]:
    """Record what the contract owes into the ledger. Idempotent: a recorded obligation adds no row, a newly
    changed file it answers for appends one cover row. A drifted obligation refuses before anything is written."""
    root = Path.cwd() if root is None else Path(root)
    owe, gaps, not_owed = owed(_contract(contract_path), root)
    have = current(task)
    drifted = [d for oid, want in owe.items() if oid in have and (d := _drift(oid, have[oid], want))]
    if drifted:
        raise LedgerError("; ".join(drifted) + ": a changed obligation is a new task, never an edit")
    written = []
    for oid, want in owe.items():
        if oid not in have:
            written.append(add(task, oid, want["statement"], want["check"]))
        new = sorted(set(want["paths"]) - set(have.get(oid, {}).get("paths") or ()))
        if new:
            written.append(_append(task, {"op": "cover", "id": oid, "paths": new}))
    return {"written": written, "gaps": gaps, "not_owed": not_owed}


def coverage(task: str, contract_path: str | Path, root: Path | None = None) -> list[str]:
    """Every way the ledger falls short of the contract on the files changed now; empty only when it is whole."""
    root = Path.cwd() if root is None else Path(root)
    owe, gaps, _ = owed(_contract(contract_path), root)
    have = current(task)
    findings = [f"gap {gap}" for gap in gaps]
    for oid, want in owe.items():
        row = have.get(oid)
        if row is None:
            findings.append(f"{oid} not recorded ({want['check']})")
        elif drift := _drift(oid, row, want):
            findings.append(drift)
        elif missing := sorted(set(want["paths"]) - set(row.get("paths") or ())):
            findings.append(f"{oid} does not cover {', '.join(missing[:5])}")
    return findings


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


def _contract_verb(args: argparse.Namespace) -> int:
    """extract: record, print rows written and gaps; coverage: print findings. 0 whole, 1 a gap or finding."""
    if args.cmd == "extract":
        done = extract(args.task, args.contract, args.root)
        print(json.dumps(done))
        return 1 if done["gaps"] else 0
    findings = coverage(args.task, args.contract, args.root)
    print("\n".join(f"  {f}" for f in findings) or f"{args.task}: every owed obligation is recorded")
    return 1 if findings else 0


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
    for verb in ("extract", "coverage"):  # what the task contract owes on the files changed, against the ledger
        e = sub.add_parser(verb)
        e.add_argument("task")
        e.add_argument("contract")
        e.add_argument("--root", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.cmd in ("extract", "coverage"):
            return _contract_verb(args)
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


def proof_record(
    path_value: str, task: str, change: str, modifiers: list[str], measure: bool
) -> tuple[dict | None, int]:
    """Return a deterministic agent result; verification is planned until explicitly measured."""
    profiles = declared_atlas().get("task_profiles") or {}
    language = route_for(path_value)
    if not language:
        print(f"no Atlas route for {path_value}")
        return None, 2
    if task not in profiles:
        print(f"unknown task profile: {task}")
        print("available: " + ", ".join(profiles))
        return None, 2
    from agentpolicy import required_gates  # noqa: PLC0415 — as in this module's other readers
    from atlas import gate_record  # noqa: PLC0415

    planned = required_gates({"change_class": change, "risk_modifiers": modifiers, "task_profile": task})
    declared = [gate_record(path_value, gate) for gate in planned]
    rows = [
        {
            "id": record["gate"],
            "verdict": "NOT RUN",
            "why": "planned; run `headron proof --verify` for evidence"
            if record["state"] == "runnable"
            else record["why"],
            "state": record["state"],
            "argv": record["argv"],
        }
        for record in declared
    ]
    from verify import verdict_code  # noqa: PLC0415 — one canonical exit-code policy

    verification: dict[str, Any] = {"mode": "PLANNED", "exit": verdict_code(rows), "planned": planned, "rows": rows}
    if measure:
        from verify import run_declared_gates  # noqa: PLC0415

        runnable = [
            {"id": record["gate"], "argv": record["argv"], "mutates": False}
            for record in declared
            if record["state"] == "runnable" and record["argv"]
        ]
        measured = {row["id"]: row for row in run_declared_gates(runnable, Path.cwd(), jobs=1)}
        rows = [
            {
                "id": record["gate"],
                "verdict": measured[record["gate"]]["verdict"],
                "why": measured[record["gate"]].get("why") or "",
                "state": record["state"],
                "argv": record["argv"],
            }
            if record["gate"] in measured
            else {
                "id": record["gate"],
                "verdict": "NOT RUN",
                "why": record["why"],
                "state": record["state"],
                "argv": record["argv"],
            }
            for record in declared
        ]
        verification = {"mode": "MEASURED", "exit": verdict_code(rows), "planned": planned, "rows": rows}
    verdict = (
        "NOT RUN"
        if verification["mode"] == "PLANNED"
        else (
            "PASS"
            if verification["exit"] == 0
            else "FAIL"
            if any(row["verdict"] == "FAIL" for row in verification["rows"])
            else "NOT RUN"
        )
    )
    record = {
        "schema": 1,
        "command": "proof",
        "path": path_value,
        "route": language,
        "task": task,
        "tools": list(profiles[task]),
        "change_class": change,
        "risk_modifiers": list(modifiers),
        "required_gates": planned,
        "verdict": verdict,
        "verification": verification,
    }
    return record, int(verification["exit"]) if measure else 2


if __name__ == "__main__":
    raise SystemExit(main())
