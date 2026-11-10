"""Consumer gate discovery, shared by landing and verification."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from atlascore import ROOT, atlas


def enter_lane(lane: Path, script: str, argv: list[str]) -> NoReturn:
    """Hand this command to a lane's own copy of `script`, with that copy as its own atlas.

    SIGHTED (3.62.0): the installed CLI exports HEADRON_ROOT, so a lane's gates read the installed tree while running
    in the lane, and `headron verify` raised ValueError on a path outside it. Inherited, the root also never equals
    the lane, so the hand-off would repeat forever."""
    for name in ("HEADRON_ROOT", "CODE_DEVELOPMENT_ROOT"):
        os.environ.pop(name, None)
    os.chdir(lane)
    os.execv(sys.executable, [sys.executable, str(lane / "scripts" / script), *argv])  # noqa: S606


def consumer_records(tree: Path, files: list[str], change: str) -> list[dict]:
    """Every gate record this atlas routes for each changed file of a CONSUMER's tree, as `atlas.py gate --json`
    prints it; a file the atlas gave no record for is one record with state `no_record`. ONE producer for the
    landing and for `verify` run in a consumer."""
    out: list[dict] = []
    for rel in files:
        if not (tree / rel).is_file():
            out.append(
                {
                    "path": rel,
                    "gate": "atlas",
                    "state": "no_record",
                    "why": "deleted or missing file: dependent gates unresolved",
                }
            )
            continue
        done = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "atlas.py"), "gate", rel, "--change", change, "--json"],
            cwd=tree,
            stdin=subprocess.DEVNULL,  # a consumer's tool that reads stdin must not wait on the caller's terminal
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
        try:
            records = json.loads(done.stdout)
        except json.JSONDecodeError:
            records = None
        if not isinstance(records, list) or not records or not all(isinstance(rec, dict) for rec in records):
            out.append({"path": rel, "gate": "atlas", "state": "no_record", "why": "the atlas gave no gate record"})
            continue
        for rec in records:
            argv = rec.get("argv")
            if rec.get("state") == "runnable" and (
                not isinstance(argv, list) or not argv or not all(isinstance(arg, str) and arg for arg in argv)
            ):
                out.append({"path": rel, "gate": rec.get("gate"), "state": "no_record", "why": "invalid gate argv"})
            else:
                out.append(rec | {"path": rel})
        if done.returncode and all(rec.get("state") in ("runnable", "absent") for rec in records):
            out.append({"path": rel, "gate": "atlas", "state": "no_record", "why": "gate discovery failed"})
    return out


def consumer_gates(clean: Path, files: list[str], change: str) -> tuple[list[tuple[list[str], str]], list[str]]:
    """The gates this atlas routes for each changed file of a CONSUMER's tree: ((argv, cwd) runnable, not-run notes).

    The atlas is the filter between an agent and its repository: it decides WHAT proves a change, and the
    change is proven and landed in the consumer's own clean checkout, each gate in the directory its record
    names (a per-project runner in its project). A gate the route leaves undeclared, absent or unplaced is
    reported, never invented. An identical (argv, cwd) — one test runner for many files — runs once.
    """
    runnable: list[tuple[list[str], str]] = []
    notes: list[str] = []
    for rec in consumer_records(clean, files, change):
        argv, cwd = rec.get("argv"), str(rec.get("cwd") or ".")
        if rec.get("state") == "runnable" and argv:
            if (placed := (list(argv), cwd)) not in runnable:
                runnable.append(placed)
        elif rec.get("state") == "no_record":
            notes.append(f"{rec['path']}: {rec['why']}")
        elif rec.get("state") != "absent":
            notes.append(f"{rec['path']}: {rec.get('gate')} {rec.get('state')}")
    return runnable, notes


def check_record(version: object, rc: int, errors: list[str], warnings: list[str], counts: object) -> dict:
    """The `check --json` record: every finding with its severity and what that severity blocks."""
    severity = (atlas().get("verification_policy") or {}).get("severity") or {}
    found = [(level, m) for level, said in (("error", errors), ("warning", warnings)) for m in said]
    return {
        "schema": 1,
        "command": "check",
        "atlas_version": version,
        "exit": rc,
        "findings": [{"severity": s, "blocks": severity.get(s), "message": m} for s, m in found],
        "counts": counts,
    }


def consumer_check(fix: bool, as_json: bool) -> int | None:
    """`headron check` in a CONSUMER's tree: what it answers there, or None in an atlas checkout (a lane included).

    SIGHTED (polyglot benchmark): run in eight consumer checkouts, `check` proved Headron's own contract against
    the installed tool's environment and exited 1 in every one on `dependency_count_is_the_closure`, a lock the
    consumer never had. Headron's contract and its locked dependencies are checked in Headron's repository; a
    consumer's change is proven by `headron verify`. `--fix` rewrites Headron's generated files, so it is refused."""
    from verify import is_atlas_checkout, target_tree  # noqa: PLC0415 — verify is the one home of both

    tree = target_tree()
    if is_atlas_checkout(tree):
        return None
    if fix:
        rc, said = 2, f"REFUSED check --fix: {tree} is not Headron's repository, and --fix rewrites Headron's files"
    else:
        rc, said = (
            0,
            (
                f"NOT RUN here: {tree} is not Headron's repository, so Headron's contract and its locked "
                "dependencies are checked there; this tree's change is proven by `headron verify`"
            ),
        )
    if as_json:
        print(
            json.dumps(
                check_record(str(atlas().get("version")), rc, [said] if rc else [], [] if rc else [said], None),
                indent=2,
            )
        )
    else:
        print(said, file=sys.stderr if rc else sys.stdout)
    return rc
