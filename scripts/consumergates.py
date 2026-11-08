"""Consumer gate discovery, shared by landing and verification."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from atlascore import ROOT


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
            records = json.loads(done.stdout or "[]")
        except json.JSONDecodeError:
            out.append({"path": rel, "gate": "atlas", "state": "no_record", "why": "the atlas gave no gate record"})
            continue
        out += [rec | {"path": rel} for rec in (records if isinstance(records, list) else [records])]
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
        else:
            notes.append(f"{rec['path']}: {rec.get('gate')} {rec.get('state')}")
    return runnable, notes
