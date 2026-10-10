#!/usr/bin/env python3
"""Planted case: a lane of this atlas landed through the installed runtime runs its own landing, never a consumer's."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import branchstate


def own_checkout_case(module) -> None:
    here = Path.cwd()
    mine = branchstate.atlas()["identity"]["repository"]
    try:
        with tempfile.TemporaryDirectory() as repo:
            subprocess.run(["git", "init", "-q", repo], check=True, timeout=600)
            (Path(repo) / "scripts").mkdir()
            (Path(repo) / "scripts" / "branchstate.py").write_text("")
            os.chdir(repo)
            (Path(repo) / "atlas.yaml").write_text(f"identity:\n  repository: {mine}\n")
            if branchstate._own_checkout() != Path(repo).resolve():
                raise SystemExit("FAIL a lane of this atlas landed through the runtime is judged as a consumer")
            (Path(repo) / "atlas.yaml").write_text("identity:\n  repository: someone-else\n")
            if branchstate._own_checkout() is not None:
                raise SystemExit("FAIL a consumer with its own branchstate.py is re-executed as this atlas")
        os.chdir(branchstate.ROOT)
        if branchstate._own_checkout() is not None:
            raise SystemExit("FAIL the atlas itself re-executes its own landing")
    finally:
        os.chdir(here)
    if module is not None:
        module.CASES.append(
            (
                "a lane of this atlas landed through the installed runtime runs its own landing",
                "a release lane judged as a consumer: the json pack's bare ajv refuses a land the atlas gates pass",
            )
        )
    print("  ok    a lane of this atlas landed through the installed runtime runs its own landing")


def run(module) -> None:
    own_checkout_case(module)


if __name__ == "__main__":
    run(None)
