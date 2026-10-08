#!/usr/bin/env python3
"""Regression cases for a walk over paths another session owns: a lane removed mid-walk is reported, never raised."""

from __future__ import annotations

import contextlib
import io
import tempfile
from pathlib import Path


def vanished_lane_cases(module) -> None:
    """`worktree list` and the first `cwd=` call are two moments; a sibling may remove the lane between them (3.51.0)."""
    import staleness

    real_git = staleness._git
    with tempfile.TemporaryDirectory() as scratch:
        gone = Path(scratch) / "clean"  # never created: the lane a sibling removed after the listing

    def listing(*args: str, cwd: Path = staleness.ROOT) -> str:
        if args[:2] == ("worktree", "list"):
            return f"worktree {staleness.ROOT}\nbranch refs/heads/main\n\nworktree {gone}\nbranch refs/heads/lane\n\n"
        return real_git(*args, cwd=cwd)

    out = io.StringIO()
    staleness._git = listing
    try:
        with contextlib.redirect_stdout(out):
            code = staleness.worktrees()
    except (FileNotFoundError, NotADirectoryError) as error:
        raise SystemExit(f"FAIL vanished lane: a worktree removed mid-walk crashed the walk: {error!r}") from None
    finally:
        staleness._git = real_git
    line = next((row for row in out.getvalue().splitlines() if str(gone) in row), "")
    if code != 0 or "PRUNABLE" not in line or "2 worktree(s); 1 need attention" not in out.getvalue():
        raise SystemExit(f"FAIL vanished lane: want exit 0 and the lane PRUNABLE, got {code}: {out.getvalue()!r}")
    module.CASES.append(
        (
            "a worktree another session removes between `worktree list` and the walk reads PRUNABLE, exit 0",
            "the planted suite died in staleness.worktrees on FileNotFoundError when a sibling removed its temp lane",
        )
    )
    print("  ok    a lane removed mid-walk is reported PRUNABLE, never raised")


def dropped_reference_cases(module) -> None:
    """A path one file stops naming is not a path the tree lost: only the second goes stale (3.54.0)."""
    import staleness

    real_git, real_changed = staleness._git, staleness.changed_paths
    diff = "-see languages/python/README.md\n-see languages/nowhere/GONE.md\n+see the pack guide\n"
    staleness._git = lambda *args, **_: diff if args[:2] == ("diff", "-U0") and len(args) == 3 else ""
    staleness.changed_paths = list
    try:
        keys = staleness.vanished()
    finally:
        staleness._git, staleness.changed_paths = real_git, real_changed
    if keys != {"languages/nowhere/GONE.md"}:
        raise SystemExit(f"FAIL dropped reference: want only the missing path vanished, got {sorted(keys)}")
    module.CASES.append(
        (
            "a path dropped from one file but still in the tree is not vanished; a missing one is",
            "drift review flagged four files naming pack READMEs that llms.txt stopped listing but never removed",
        )
    )
    print("  ok    a dropped reference to a path still in the tree is not vanished")


def shared_temp_cases(module) -> None:
    """A fixed name in the shared temp dir is refused; a per-run one is not (3.53.0, sighted as a non-root user)."""
    import declcheck

    fixed = "probe = Path(tempfile.gettempdir()) " + '/ "thea-edit-contract.json"\n'
    per_run = 'handle, probe = tempfile.mkstemp(prefix="thea-edit-contract-")\n'
    with tempfile.TemporaryDirectory() as scratch:
        bad, good = Path(scratch, "bad.py"), Path(scratch, "good.py")
        bad.write_text(fixed), good.write_text(per_run)
        found, clean = declcheck.shared_temp_errors([bad]), declcheck.shared_temp_errors([good])
    if len(found) != 1 or "bad.py:1" not in found[0] or clean:
        raise SystemExit(f"FAIL shared temp: planted fixed name -> {found}, per-run name -> {clean}")
    module.CASES.append(
        (
            "a script joining a fixed name to the shared temp dir is refused; a per-run name passes",
            "the planted suite died on PermissionError where another user owned that name in /tmp",
        )
    )
    print("  ok    a fixed name in the shared temp dir is refused; a per-run one passes")


def unmerged_roster_cases(module) -> None:
    """Mid-merge, an unmerged path is ONE roster row (3.54.0): git lists it once per stage, and a README
    regenerated then counted phantom documents and linked one file three times."""
    import subprocess

    import atlascore

    def git(repo, *args):
        subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False, timeout=60)  # noqa: S607

    with tempfile.TemporaryDirectory(prefix="thea-unmerged-") as scratch:
        repo = Path(scratch)
        git(repo, "init", "-q", "-b", "main")
        git(repo, "config", "user.email", "t@t"), git(repo, "config", "user.name", "t")
        (repo / "doc.md").write_text("base\n"), git(repo, "add", "."), git(repo, "commit", "-qm", "base")
        git(repo, "checkout", "-qb", "side")
        (repo / "doc.md").write_text("side\n"), git(repo, "commit", "-qam", "side")
        git(repo, "checkout", "-q", "main")
        (repo / "doc.md").write_text("main\n"), git(repo, "commit", "-qam", "main")
        git(repo, "merge", "-q", "side")
        staged = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-s"], capture_output=True, text=True, check=False, timeout=60
        )  # noqa: S607
        rows = atlascore.ls_files(repo)
    if staged.stdout.count("doc.md") < 2 or rows != ["doc.md"]:
        raise SystemExit(f"FAIL unmerged roster: stages {staged.stdout!r} -> rows {rows}")
    module.CASES.append(
        (
            "mid-merge, an unmerged path is one roster row, never one per stage",
            "a README regenerated mid-conflict counted phantom documents and linked one file three times",
        )
    )
    print("  ok    an unmerged path is one roster row mid-merge")


def run(module) -> None:
    for cases in (vanished_lane_cases, dropped_reference_cases, shared_temp_cases, unmerged_roster_cases):
        cases(module)
