#!/usr/bin/env python3
"""Regression cases for one-artifact handoff capsules, and for handing back a finished lane's worktree."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run(module) -> None:
    """Register the handoff capsule contract into atlas_test's counted cases."""
    import handoff

    record = handoff.capsule("scripts/intake.py", "tighten prompt routing")
    expected = ["languages/python/README.md", "languages/python/OPERATING.md", "languages/python/tools.yaml"]
    if (
        record["scope"] != ["scripts/intake.py"]
        or record["route"]["language"] != "python"
        or record["context"] != expected
        or not all(row["command"] for row in record["acceptance"])
    ):
        raise SystemExit(f"FAIL handoff widened or lost its artifact edge: {record}")
    try:
        handoff.capsule("missing.py")
    except ValueError:
        pass
    else:
        raise SystemExit("FAIL handoff accepted an artifact outside the declared tree")
    module.CASES.append(
        (
            "handoff binds one artifact to route evidence, bounded context and acceptance commands",
            "a multi-agent brief that gives a repository dump or leaves the recipient to infer its gates",
        )
    )
    print("  ok    handoff carries one artifact's route, context and gates")
    pass_cache_case(module)
    lane_tree_cases(module)
    land_empty_cases(module)


def pass_cache_case(module) -> None:
    """A clean-checkout PASS is remembered per (tree, gates); a failure is never remembered."""
    import sys
    import tempfile
    import uuid
    from pathlib import Path

    import branchstate

    with tempfile.TemporaryDirectory() as tmp:
        runs, nonce = Path(tmp) / "runs", uuid.uuid4().hex
        tally = f"open({str(runs)!r}, 'a').write('x')"
        good = [[sys.executable, "-c", f"{tally}  # {nonce}"]]
        bad = [[sys.executable, "-c", f"{tally}; raise SystemExit(3)  # {nonce}"]]
        verdicts = [branchstate.clean_checkout_errors(g) for g in (good, good, bad, bad)]
        ran = len(runs.read_text()) if runs.exists() else 0
    if verdicts[:2] != [None, None] or None in verdicts[2:] or ran != 3:
        raise SystemExit(f"FAIL the clean-checkout pass cache: verdicts {verdicts}, gate ran {ran} time(s), want 3")
    module.CASES.append(
        (
            "a clean-checkout pass on an identical tree and gates is not re-run; a failure always is",
            "a re-land after a push or forge refusal that re-queues the whole suite on the tree it already passed",
        )
    )
    print("  ok    a clean-checkout pass is remembered by tree and gates, a failure never")



def _tree_verdicts() -> dict[str, str | None]:
    """tree_kept over a landed, clean, idle lane, then once per way removing it could destroy something."""
    import importlib
    import tempfile

    import branchstate

    importlib.reload(branchstate)
    with tempfile.TemporaryDirectory() as repo:
        (Path(repo) / "o.txt").write_text("work no base has\n")
        for argv in (
            ["init", "-q", "-b", "main"],
            ["commit", "-q", "--allow-empty", "-m", "b"],
            ["worktree", "add", "-q", "-b", "lane", "lane"],
            ["checkout", "-qb", "open"],
            ["add", "o.txt"],
            ["commit", "-qm", "open"],
            ["checkout", "-q", "main"],
        ):
            subprocess.run(
                ["git", "-c", "user.name=t", "-c", "user.email=t@t", *argv],
                cwd=repo,
                check=True,
                capture_output=True,
                timeout=60,
            )
        lane, saved, branchstate._tree = str(Path(repo) / "lane"), branchstate._tree, lambda: Path(repo)
        try:
            got = {
                name: branchstate.tree_kept(lane, branch, "main", live, 0.0)
                for name, branch, live in (
                    ("landed", "lane", set()),
                    ("live", "lane", {os.path.realpath(lane) + "/sub"}),
                    ("blind", "lane", None),
                    ("unlanded", "open", set()),
                )
            }
            (Path(lane) / "draft.txt").write_text("x")
            got["dirty"] = branchstate.tree_kept(lane, "lane", "main", set(), 0.0)
        finally:
            branchstate._tree = saved
    return got


def lane_tree_cases(module) -> None:
    got = _tree_verdicts()
    if got["landed"] is not None or not all(got[k] for k in ("live", "blind", "unlanded", "dirty")):
        raise SystemExit(f"FAIL tree_kept: a landed idle lane must go and every other must stay: {got}")
    with module.mutated("scripts/branchstate.py", lambda t: t.replace("(any(c == root", "(False and any(c == root", 1)):
        planted = _tree_verdicts()
    _tree_verdicts()  # reload the restored module
    if planted["live"] is not None:
        raise SystemExit("FAIL the lane-tree probe did not notice the live-process check removed")
    module.CASES.append(
        (
            "--sync removes a landed, clean, idle, unentered worktree and keeps every other",
            "a forgotten tree kept forever, or a live session's checkout removed under it",
        )
    )
    print("  ok    lane trees: landed+idle removed; live, blind, unlanded, dirty kept; a dropped live check caught")


def land_empty_cases(module) -> None:
    """A lane at ahead=0 lands as FINISHED before any gate runs; a lane with a commit goes on to the gate."""
    import tempfile

    import branchstate

    with tempfile.TemporaryDirectory() as tmp:
        origin, lane, here = Path(tmp) / "origin.git", Path(tmp) / "lane", os.getcwd()
        git = lambda *a, at=lane: subprocess.run(["git", *a], cwd=at, capture_output=True, check=True, timeout=600)  # noqa: E731
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, timeout=600)
        subprocess.run(["git", "clone", "-q", str(origin), str(lane)], check=True, capture_output=True, timeout=600)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "base")
        git("push", "-q", "origin", "HEAD:main")
        git("checkout", "-q", "-b", "claude/empty")
        gated, real = [], branchstate.clean_checkout_errors
        branchstate.clean_checkout_errors = lambda: gated.append(1) or "planted refusal"
        try:
            os.chdir(lane)
            empty = branchstate._land_once("claude/empty")
            git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "work")
            ahead = branchstate._land_once("claude/empty")
        finally:
            os.chdir(here)
            branchstate.clean_checkout_errors = real
    assert empty == 0 and gated == [1], f"ahead=0 must finish before the gate (rc {empty}, gate runs {len(gated)})"
    assert ahead == 65, f"a lane with a commit must reach the gate (rc {ahead})"
    module.CASES.append(
        (
            "land on an ahead=0 lane is FINISHED before the suite runs, a lane with work still meets the gate",
            "a full suite, a failed PR create and a 'two writers' escalation over a lane with nothing in it",
        )
    )
    print("  ok    land finishes an empty lane without running its gate")
