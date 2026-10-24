#!/usr/bin/env python3
"""Planted local-state cases for the atlas-derived seats instrument."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(module) -> None:
    """Each required state runs through the public CLI under a test-only state path."""
    with tempfile.TemporaryDirectory(prefix="thea-seats-") as directory:
        state = Path(directory) / "seats.json"
        env = {**os.environ, "THEA_SEATS_STATE": str(state)}

        def call(*argv: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, "scripts/atlas.py", "seats", *argv],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )

        empty = call("--json")
        empty_body = json.loads(empty.stdout)
        clean = (
            empty.returncode == 0
            and empty_body["state"] == "empty"
            and all(not row["attached"] for row in empty_body["seats"])
        )
        _case(
            module,
            "an absent state lists every declared seat detached",
            "an empty state mistaken for a partial roster",
            clean,
        )

        attached = call("attach", "claude", "--json")
        first = json.loads(attached.stdout)
        same = call("attach", "claude", "--json")
        second = json.loads(same.stdout)
        persisted = json.loads(state.read_text(encoding="utf-8"))
        idem = (
            attached.returncode == same.returncode == 0
            and first == second
            and persisted == {"claude": {"attached_at": first["attached_at"]}}
        )
        _case(
            module,
            "attach is idempotent and writes only an attachment timestamp",
            "a second attach changing state or storing roster data",
            idem,
        )

        listed = call("--json")
        recorded = json.loads(listed.stdout)
        found = next(row for row in recorded["seats"] if row["id"] == "claude")
        _case(
            module,
            "a recorded attachment is reflected in the derived roster",
            "a state file ignored by the listing",
            listed.returncode == 0 and recorded["state"] == "recorded" and found == first,
        )

        text = call()
        lines = text.stdout.splitlines()
        _case(
            module,
            "the text listing prints one row per seat, attached ones marked",
            "the bare listing indexing the {seats, state} wrapper as if it were one seat",
            text.returncode == 0
            and len(lines) == len(recorded["seats"])
            and "claude\tagent\tClaude Code\tattached" in lines,
        )

        detached = call("detach", "claude", "--json")
        detached_body = json.loads(detached.stdout)
        detached_again = call("detach", "claude", "--json")
        _case(
            module,
            "detach removes an attachment idempotently",
            "a detach leaving a recorded attachment",
            detached.returncode == 0
            and not detached_body["attached"]
            and detached_again.returncode == 0
            and json.loads(detached_again.stdout) == detached_body
            and json.loads(state.read_text(encoding="utf-8")) == {},
        )

        before = state.read_bytes()
        unknown = call("attach", "not-a-seat", "--json")
        _case(
            module,
            "an unknown id exits 2 without writing",
            "an unknown integration creating state",
            unknown.returncode == 2 and "not-a-seat" in unknown.stderr and state.read_bytes() == before,
        )

        state.write_text("{", encoding="utf-8")
        torn = state.read_bytes()
        unreadable = call("--json")
        unreadable_body = json.loads(unreadable.stdout)
        refuses_attach, refuses_detach = call("attach", "claude", "--json"), call("detach", "claude", "--json")
        safe = (
            unreadable.returncode == 0
            and unreadable_body["state"] == "unreadable"
            and all(not row["attached"] for row in unreadable_body["seats"])
            and refuses_attach.returncode == refuses_detach.returncode == 1
            and state.read_bytes() == torn
        )
        _case(
            module,
            "a torn state is shown unreadable and both mutations refuse without overwriting it",
            "a malformed state silently reset by attach or detach",
            safe,
        )

        state.unlink()
        call("attach", "claude", "--json")
        private = stat.S_IMODE(state.stat().st_mode) == 0o600
        _case(
            module, "a written state file is mode 0600", "attachment timestamps readable by other local users", private
        )


def _case(module, name: str, kills: str, holds: bool) -> None:
    if not holds:
        raise SystemExit(f"FAIL {name}\n  kills: {kills}")
    module.CASES.append((name, kills))
    print(f"  ok    {name}")
