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


def run(module) -> None:
    vanished_lane_cases(module)
