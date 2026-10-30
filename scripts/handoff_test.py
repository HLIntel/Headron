#!/usr/bin/env python3
"""Regression cases for one-artifact handoff capsules, and for handing back a finished lane's worktree."""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path


def run(module) -> None:
    """Register the handoff capsule contract into atlas_test's counted cases."""
    freshness_shallow_case(module)
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
    carried_case(module)
    land_wait_case(module)
    gate_output_case(module)
    ci_parity_case(module)


def gate_output_case(module) -> None:
    """A clean gate's output lands in a file: a runaway writer cannot fill the landing's memory."""
    import sys
    import tracemalloc

    import branchstate

    flood = (
        "import sys\nfor _ in range(1 << 16): sys.stdout.write('x' * 1023 + chr(10))\nprint('last line')\nsys.exit(3)"
    )
    tracemalloc.start()
    try:
        code, tail = branchstate.run_gate([sys.executable, "-c", flood], Path.cwd())
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    if code != 3 or not tail.rstrip().endswith("last line") or len(tail) > 4096 or peak > 8 << 20:
        raise SystemExit(f"FAIL a flooding gate: rc {code}, tail {len(tail)} chars, peak {peak >> 20} MiB held")
    module.CASES.append(
        (
            "a clean gate's output goes to a file and only its tail is held",
            "a looping test whose prints a captured pipe buffered until the kernel killed the landing",
        )
    )
    print("  ok    a flooding gate leaves the landing its tail, not its output")


def carried_case(module) -> None:
    """--sync names an open request whose every patch another ref holds; a request with its own work, never."""
    import branchstate

    table = {("pr", "main"): "+ a\n- b", ("pr", "other"): "- a\n- b", ("own", "main"): "+ c", ("own", "other"): "+ c"}
    fake = lambda b, r: table.get((b, r), "")  # noqa: E731
    found = [branchstate.carried_by(b, ["main", "other"], fake) for b in ("pr", "own", "empty")]
    if found != ["other", None, None]:
        raise SystemExit(f"FAIL carried_by: {found}, want ['other', None, None]")
    module.CASES.append(
        (
            "--sync names an open request whose every patch main or another open lane already holds",
            "a superseded request left open and armed, DIRTY forever, that nothing will merge or close",
        )
    )
    print("  ok    --sync names an open request another ref already carries")


def case_total_pin_case() -> None:
    import atlasinv
    import testgroups

    atlas_source = "expected = shard_pin(shard, cross_checked)"
    if atlasinv._declared_pin(atlas_source, "atlas_test.py") != testgroups.shard_pin("all", False):
        raise SystemExit("FAIL unconditional suite pin")
    agent = atlasinv._declared_pin((atlasinv.ROOT / "scripts/agent_test.py").read_text(), "agent_test.py")
    if atlasinv.declared_case_total() != testgroups.shard_pin("all", False) + agent:
        raise SystemExit("FAIL suite total omits a declared pin")
    for source in ("pass", "expected = 1\nexpected = 2", "expected = unknown()", "expected ="):
        try:
            atlasinv._declared_pin(source, "atlas_test.py")
        except ValueError:
            continue
        raise SystemExit("FAIL invalid or ambiguous suite pin was accepted")


def ci_parity_case(module) -> None:
    """Every ruff step CI runs is a clean-checkout gate, ahead of the planted suite."""
    import re
    from pathlib import Path

    import branchstate

    case_total_pin_case()

    ci = (Path(branchstate._tree()) / "ci" / "atlas-ci.yml").read_text(encoding="utf-8")
    steps = [
        tuple(m.split())
        for m in re.findall(
            r"^\s*(?:run:\s*)?((?:uvx --from ruff==\S+ )?ruff (?:check \.|format --check \.))(?:\s|$)", ci, re.M
        )
    ]
    gates = list(branchstate.CLEAN_GATES)
    # atlas_test.py was removed from local gates (3.58.0); all gates are now the pre-suite set
    missing = [s for s in steps if s not in gates]
    if not steps or missing:
        raise SystemExit(f"FAIL CI runs {missing or 'no ruff step'} that a landing does not run")
    altered = [tuple("ruff==0.0.0" if arg.startswith("ruff==") else arg for arg in step) for step in steps]
    if any(step in gates for step in altered):
        raise SystemExit("FAIL CI parity ignored the pinned Ruff version")
    module.CASES.append(
        (
            "a landing's clean checkout runs every ruff step CI runs",
            "a lane green locally whose PR goes red on a format check only CI ran, costing a second full suite",
        )
    )
    print(f"  ok    a landing runs CI's {len(steps)} ruff step(s)")


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


def oldest_lane_age_case() -> None:
    """A recent commit must not hide older unpushed work, even when git returns newest first."""
    import branchstate

    with tempfile.TemporaryDirectory() as repo:

        def git(*args: str) -> None:
            subprocess.run(
                ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                cwd=repo,
                capture_output=True,
                timeout=60,
                check=True,
            )

        git("init", "-q", "-b", "main")
        (Path(repo) / "f.txt").write_text("base\n")
        git("add", "f.txt")
        git("commit", "-qm", "base")
        git("update-ref", "refs/remotes/origin/main", "main")
        git("checkout", "-qb", "lane")
        for year in (2000, 2001):
            (Path(repo) / "f.txt").write_text(f"{year}\n")
            git("add", "f.txt")
            date = f"{year}-01-01T00:00:00+0000"
            subprocess.run(
                ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", str(year)],
                cwd=repo,
                env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date},
                capture_output=True,
                timeout=60,
                check=True,
            )
        original_tree, original_git = branchstate._tree, branchstate._git
        branchstate._tree = lambda: Path(repo).resolve()
        try:
            expected = round((time.time() - 946684800) / 3600, 1)
            measured = next(row["age_hours"] for row in branchstate.branches() if row["branch"] == "lane")
            # Plant the old `log -1` behavior and prove this fixture distinguishes it.
            branchstate._git = lambda *args: (
                original_git(args[0], "-1", *args[1:]) if args[0] == "log" else original_git(*args)
            )
            planted = next(row["age_hours"] for row in branchstate.branches() if row["branch"] == "lane")
        finally:
            branchstate._tree, branchstate._git = original_tree, original_git
    if abs(measured - expected) > 0.1 or measured - planted < 8000:
        raise SystemExit(f"FAIL oldest unpushed age: {measured=} {expected=} {planted=}")


def lane_tree_cases(module) -> None:
    oldest_lane_age_case()
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


def land_empty_cases(module, *, plant: bool = True) -> None:
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
        git("push", "-q", "-u", "origin", "claude/empty")
        published_tip = git("rev-parse", "HEAD").stdout.strip().decode()
        git("checkout", "-q", "-b", "side", "origin/main")
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "side")
        git("checkout", "-q", "claude/empty")
        git("-c", "user.name=t", "-c", "user.email=t@t", "merge", "-q", "--no-ff", "side", "-m", "merge side")
        gate = branchstate.clean_checkout_errors
        branchstate.clean_checkout_errors = lambda: "planted refusal"
        try:
            os.chdir(lane)
            assert branchstate._land_once("claude/empty") == 65
            git("merge-base", "--is-ancestor", published_tip, "HEAD")
            assert len(git("rev-list", "--parents", "-n", "1", "HEAD").stdout.split()) == 3
        finally:
            os.chdir(here)
            branchstate.clean_checkout_errors = gate
        other = Path(tmp) / "other"
        subprocess.run(["git", "clone", "-q", str(origin), str(other)], check=True, timeout=600)
        git("checkout", "-q", "claude/empty", at=other)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "remote", at=other)
        git("push", "-q", "origin", "claude/empty", at=other)
        remote_tip = git("rev-parse", "HEAD", at=other).stdout
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "local")
        real_gate, real_pr = branchstate.clean_checkout_errors, branchstate._pull_request
        branchstate.clean_checkout_errors = lambda: None
        branchstate._pull_request = lambda _branch: ({"number": 1}, True)
        try:
            os.chdir(lane)
            diverged = branchstate._land_once("claude/empty")
        finally:
            os.chdir(here)
            branchstate.clean_checkout_errors, branchstate._pull_request = real_gate, real_pr
        assert diverged != 0 and git("rev-parse", "claude/empty", at=origin).stdout == remote_tip, (
            "landing must refuse a divergent remote without rewriting its tip"
        )
    assert empty == 0 and gated == [1], f"ahead=0 must finish before the gate (rc {empty}, gate runs {len(gated)})"
    assert ahead == 65, f"a lane with a commit must reach the gate (rc {ahead})"
    if plant:
        _land_force_push_plant(module)
    module.CASES.append(
        (
            "land on an ahead=0 lane is FINISHED before the suite runs, a lane with work still meets the gate",
            "a full suite, a failed PR create and a 'two writers' escalation over a lane with nothing in it",
        )
    )
    print("  ok    land finishes an empty lane without running its gate")


def _land_force_push_plant(module) -> None:
    """Catch a force push even if the separate ancestry guard is also broken."""
    import importlib

    import branchstate

    real_run = subprocess.run

    def local_run(args, *pos, **kwargs):
        if args[0] == "gh":
            return subprocess.CompletedProcess(args, 0, "", "")
        return real_run(args, *pos, **kwargs)

    try:
        with module.mutated(
            "scripts/branchstate.py",
            lambda text: text.replace("if ancestor.returncode != 0:", "if False:", 1).replace(
                'steps = [["git", "push", "-u", "origin", branch]]',
                'steps = [["git", "push", "--force-with-lease", "-u", "origin", branch]]',
                1,
            ),
        ):
            importlib.reload(branchstate)
            subprocess.run = local_run
            try:
                land_empty_cases(module, plant=False)
            except AssertionError as exc:
                if "without rewriting its tip" not in str(exc):
                    raise
            else:
                raise AssertionError("the divergent-remote case missed a planted force push")
    finally:
        subprocess.run = real_run
        importlib.reload(branchstate)


def freshness_shallow_case(module) -> None:
    """freshness refuses a shallow clone (NOT RUN), and a full one is judged (control)."""
    import freshness

    real = freshness._shallow
    try:
        freshness._shallow = lambda: True
        planted = freshness.freshness_errors()
        freshness._shallow = lambda: False
        control = freshness.freshness_errors()
    finally:
        freshness._shallow = real
    if not any("shallow clone" in e for e in planted) or any("shallow clone" in e for e in control):
        raise SystemExit(f"FAIL freshness on a shallow clone: planted={planted} control={control}")
    module.CASES.append(("freshness refuses a shallow clone", "a history check passing on a checkout with no history"))
    print("  ok    freshness: a shallow clone is NOT RUN, a full clone is judged")
    row = {"path": "p", "contract": "2.26.0", "minors_behind": None, "subject": "", "exempt": None}
    real_survey, real_shallow = freshness.survey, freshness._shallow
    try:
        freshness._shallow = lambda: False
        freshness.survey = lambda: [{**row, "major_behind": True}]
        planted = freshness.freshness_errors()
        freshness.survey = lambda: [{**row, "major_behind": False}]
        control = freshness.freshness_errors()
    finally:
        freshness.survey, freshness._shallow = real_survey, real_shallow
    if not any("major" in e for e in planted) or any("major" in e for e in control):
        raise SystemExit(f"FAIL freshness on an older major: planted={planted} control={control}")
    module.CASES.append(("freshness judges an older major", "a path a whole major behind reading '?' and passing"))
    print("  ok    freshness: a path a major behind is flagged, the same path current is not")


def land_wait_case(module) -> None:
    """A NOT RUN landing lands again each time the suite lock frees, until one bounded deadline."""
    import branchstate

    saved = branchstate._land_once, branchstate._suite_host_free
    codes, calls = [75, 75, 0], []
    branchstate._land_once = lambda b: calls.append(b) or codes[len(calls) - 1]
    branchstate._suite_host_free = lambda wait: True
    try:
        got = branchstate.land("lane")
    finally:
        branchstate._land_once, branchstate._suite_host_free = saved
    if (got, len(calls)) != (0, 3):
        raise SystemExit(f"FAIL land after two lost lock races: rc {got} after {len(calls)} attempt(s), want 0 after 3")
    module.CASES.append(
        (
            "a landing that lost the suite lock lands again each time it frees, under one deadline",
            "a single retry that loses the lock to a sibling session's suite and pushes nothing",
        )
    )
    print("  ok    a NOT RUN landing retries on every lock release until one deadline")
