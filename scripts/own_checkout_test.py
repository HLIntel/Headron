#!/usr/bin/env python3
"""Planted case: a lane of this atlas landed through the installed runtime runs its own landing, never a consumer's."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

import branchstate


def own_checkout_case(module: ModuleType | None) -> None:
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


def lane_is_its_own_atlas_case(module: ModuleType | None) -> None:
    """Both hand-offs, entered the way the installed CLI enters them: HEADRON_ROOT names the installed tree."""
    mine = branchstate.atlas()["identity"]["repository"]
    stub = "import os, sys\nprint('lane', os.environ.get('HEADRON_ROOT'), sys.argv[1:])\nsys.exit(7)\n"
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")} | {"HEADRON_ROOT": str(branchstate.ROOT)}
    with tempfile.TemporaryDirectory() as repo:
        subprocess.run(["git", "init", "-q", repo], check=True, timeout=600, env=env)
        (Path(repo) / "scripts").mkdir()
        (Path(repo) / "atlas.yaml").write_text(f"identity:\n  repository: {mine}\n")
        (Path(repo) / "scripts" / "verify.py").write_text(stub)
        (Path(repo) / "scripts" / "branchstate.py").write_text(stub)
        for script, flag in (("atlas.py verify", "--changed"), ("branchstate.py", "--land")):
            program, *command = script.split()
            done = subprocess.run(
                [sys.executable, str(branchstate.ROOT / "scripts" / program), *command, flag],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if done.returncode != 7 or f"lane None ['{flag}']" not in done.stdout:
                raise SystemExit(f"FAIL {script} from a lane kept the installed root: {done.stdout}{done.stderr}"[:600])
    if module is not None:
        module.CASES.append(
            (
                "a lane entered through the installed CLI is its own atlas",
                "a lane's gates read the installed tree: verify raised ValueError on a path outside the lane",
            )
        )
    print("  ok    a lane entered through the installed CLI is its own atlas")


def run(module: ModuleType | None) -> None:
    own_checkout_case(module)
    lane_is_its_own_atlas_case(module)


if __name__ == "__main__":
    run(None)
