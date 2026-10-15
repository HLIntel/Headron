"""Consumer gate discovery, shared by landing and verification."""

import json
import subprocess
import sys
from pathlib import Path

from atlascore import ROOT


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


def consumer_gates(clean: Path, files: list[str], change: str) -> tuple[list[list[str]], list[str]]:
    """The gates this atlas routes for each changed file of a CONSUMER's tree: (runnable argv, not-run notes).

    The atlas is the filter between an agent and its repository: it decides WHAT proves a change, and the
    change is proven and landed in the consumer's own clean checkout. A gate the route leaves undeclared or
    absent is reported, never invented. Identical argv (one test runner for many files) runs once.
    """
    runnable: list[list[str]] = []
    notes: list[str] = []
    for rec in consumer_records(clean, files, change):
        if rec.get("state") == "runnable" and rec.get("argv"):
            if rec["argv"] not in runnable:
                runnable.append(rec["argv"])
        elif rec.get("state") == "no_record":
            notes.append(f"{rec['path']}: {rec['why']}")
        else:
            notes.append(f"{rec['path']}: {rec.get('gate')} {rec.get('state')}")
    return runnable, notes
