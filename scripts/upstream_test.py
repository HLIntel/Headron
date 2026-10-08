#!/usr/bin/env python3
"""Planted upstream-count cases (3.53.0): a lane behind its default branch past the bound is refused."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

POLICY = {"default_base": "main", "upstream_bound": {"max_behind_commits": 2, "why": "planted"}}


def lane(scratch: Path, behind: int, origin: bool = True) -> Path:
    """A repository whose HEAD sits `behind` commits under a hand-made origin/main."""
    git = ["git", "-C", str(scratch), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.hooksPath=/dev/null"]
    subprocess.run(["git", "init", "-q", "-b", "main", str(scratch)], check=True, timeout=30)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "base"], check=True, timeout=30)
    for n in range(behind):
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", f"upstream {n}"], check=True, timeout=30)
    if origin:
        subprocess.run([*git, "update-ref", "refs/remotes/origin/main", "HEAD"], check=True, timeout=30)
    subprocess.run([*git, "reset", "-q", "--hard", f"HEAD~{behind}"], check=True, timeout=30)
    return scratch


def run(module) -> None:
    from upstream import upstream_errors

    for name, kills, behind, policy, origin, needle in (
        ("a lane at the bound passes", "", 2, POLICY, True, ""),
        (
            "a lane past the upstream bound is refused",
            "a lane that lands by hand-rebasing a default branch that moved under it",
            3,
            POLICY,
            True,
            "upstream count 3 against a bound of 2",
        ),
        (
            "an undeclared upstream bound is refused",
            "a bound nobody declared, so every count passes",
            0,
            {"default_base": "main"},
            True,
            "upstream_bound is not declared",
        ),
        (
            "a lane with no origin ref is NOT RUN, never a pass",
            "a blind count of zero printed as clean",
            0,
            POLICY,
            False,
            None,
        ),
    ):
        with tempfile.TemporaryDirectory(prefix="thea-upstream-") as scratch:
            found, count = upstream_errors(lane(Path(scratch), behind, origin), policy)
        refused = count is None and not found if needle is None else any(needle in e for e in found)
        if needle == "" and found or needle != "" and not refused:
            raise SystemExit(f"FAIL {name}: want {needle!r}, got {found} at count {count}")
        if kills:
            module.CASES.append((name, kills))
    import port

    for name, count, want in (
        ("the agent port line prints a NOT RUN upstream count as ?, never 0", None, "↓?"),
        ("the agent port line prints the upstream count it read", 7, "↓7"),
    ):
        rec = {"lens": "codebase", "target": ".", "upstream": {"count": count, "base": "main", "bound": 5}}
        if want not in port.line(rec, color=False):
            raise SystemExit(f"FAIL {name}: want {want!r} in {port.line(rec, color=False)!r}")
        module.CASES.append((name, "an agent that starts on a lane blind to how far the default branch moved"))
