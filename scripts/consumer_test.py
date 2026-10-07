#!/usr/bin/env python3
"""Regression cases for the atlas run FROM a consumer: its CI diff, its verify, and an ignored directory."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        timeout=600,
    )


def _env(module, **extra: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("ATLAS_PATHS", "GITHUB_BASE_REF", "THEA_READ_ONLY")}
    return env | {"THEA_ROOT": str(module.ROOT), "PYTHONPATH": str(module.ROOT / "scripts")} | extra


def _pr_checkout(top: Path, depth: bool) -> Path:
    """A pull-request checkout as actions/checkout leaves it: HEAD detached on the PR, no local `main`."""
    origin, work, ci = top / "origin.git", top / "work", top / "ci"
    _git(top, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(top, "clone", "-q", str(origin), str(work))
    (work / "README.md").write_text("# r\n")
    _git(work, "add", "."), _git(work, "commit", "-qm", "base"), _git(work, "push", "-q", "origin", "HEAD:main")
    _git(work, "checkout", "-qb", "pr")
    (work / "a.py").write_text("x = 1\n")
    _git(work, "add", "."), _git(work, "commit", "-qm", "pr"), _git(work, "push", "-q", "origin", "pr")
    _git(top, "init", "-q", str(ci))
    _git(ci, "remote", "add", "origin", f"file://{origin}")
    _git(ci, "fetch", "-q", *(["--depth", "1"] if depth else []), "origin", "+refs/heads/pr:refs/remotes/origin/pr")
    _git(ci, "checkout", "-q", "--detach", "origin/pr")
    return ci


def ci_base_case(module) -> None:
    """SIGHTED: GITHUB_BASE_REF=main diffed `main...HEAD` in a checkout holding only origin/main; the failure
    read as zero files and a consumer PR with two unroutable files passed."""
    script = str(module.ROOT / "scripts" / "atlasci.py")
    with tempfile.TemporaryDirectory() as top:
        ci = _pr_checkout(Path(top), depth=True)
        run = [sys.executable, script]
        seen = subprocess.run(
            run,
            cwd=ci,
            env=_env(module, GITHUB_BASE_REF="main"),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if seen.returncode != 0 or "1 file(s)" not in seen.stdout or "origin/main" not in seen.stdout:
            raise SystemExit(
                f"FAIL atlasci on a PR checkout without local main: rc={seen.returncode} {seen.stdout[-300:]!r}"
            )
        blind = subprocess.run(
            run,
            cwd=ci,
            env=_env(module, GITHUB_BASE_REF="no-such-base"),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if blind.returncode != 2 or "NOT RUN" not in blind.stdout:
            raise SystemExit(
                f"FAIL atlasci passed a PR it could not diff: rc={blind.returncode} {blind.stdout[-300:]!r}"
            )
    module.CASES.append(
        (
            "atlasci diffs a PR against origin/<base>, fetching it, and a diff it cannot take is NOT RUN",
            "a reusable CI job exiting 0 over zero files because the base ref was a bare name",
        )
    )
    print("  ok    atlasci: PR base is origin/<base>, fetched when absent; a failed diff is NOT RUN")


def consumer_verify_case(module) -> None:
    """SIGHTED: `thea verify` in a consumer ran the atlas's own done set and wrote its marker into the atlas."""
    with tempfile.TemporaryDirectory() as repo:
        tree = Path(repo).resolve()
        _git(tree, "init", "-q")
        (tree / "bad.py").write_text("def broken(:\n")
        done = subprocess.run(
            [sys.executable, str(module.ROOT / "scripts" / "atlas.py"), "verify"],
            cwd=tree,
            env=_env(module),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        marker = tree / ".git" / "thea-last-verify.json"
        if done.returncode != 1 or "bad.py" not in done.stdout or "contract" in done.stdout or not marker.is_file():
            raise SystemExit(
                f"FAIL verify in a consumer: rc={done.returncode} marker={marker.is_file()} {done.stdout[-300:]!r}"
            )
    module.CASES.append(
        (
            "verify in a consumer runs the gates routed for ITS change and records the verdict in ITS git dir",
            "a consumer verified by the atlas's own contract, its dashboard never given a verdict",
        )
    )
    print("  ok    verify in a consumer proves the consumer's change and writes its marker there")


def ignored_directory_case(module) -> None:
    """SIGHTED: a gitignored `build/` left by an install failed the contract for every consumer of the runtime."""
    import dirscope  # noqa: PLC0415

    ignored, fresh = module.ROOT / "build", module.ROOT / "thea_plant_unscoped"
    if ignored.exists() or fresh.exists():
        raise SystemExit(f"FAIL ignored-directory case cannot plant: {ignored} or {fresh} already exists")
    try:
        (ignored / "lib").mkdir(parents=True), (ignored / "lib" / "x").write_text("x")
        fresh.mkdir(), (fresh / "x").write_text("x")
        found = dirscope.tree_directories()
    finally:
        shutil.rmtree(ignored, ignore_errors=True), shutil.rmtree(fresh, ignore_errors=True)
    if "build" in found or "thea_plant_unscoped" not in found:
        raise SystemExit(
            f"FAIL tree_directories: ignored build counted={'build' in found}, new directory missed={'thea_plant_unscoped' not in found}"
        )
    module.CASES.append(
        (
            "a gitignored directory is not in the tree, and a new unignored one still is",
            "an install leftover failing the contract for every consumer",
        )
    )
    print("  ok    dirscope: a gitignored directory is not scoped; a new one still fails loudly")


def run(module) -> None:
    ci_base_case(module)
    consumer_verify_case(module)
    ignored_directory_case(module)
