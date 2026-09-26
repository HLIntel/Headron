#!/usr/bin/env python3
"""Unpushed work, bounded by what actually grows — not by how many branches hold it.

MEASURED AT 2.17.0, AND THE FIRST ANSWER WAS WRONG. The question asked was "cap at four branches,
or five, or six?" This tree had THREE branches and TWO worktrees, so every one of those caps was
already satisfied and none of them would ever have fired. What had actually accumulated was eight
commits over roughly three hours, on ONE branch, none of them pushed — so a branch-count cap would
have printed a clean pass over exactly the risk it was asked to bound.

That is the same shape as a count-capped rotation over growing items: the container count is not
the quantity. What is lost when a worktree is destroyed is COMMITS and TIME, so those are what is
bounded here.

WHY THESE NUMBERS. The commit cap is set from the measured session: eight commits means a cap of
five fires ONCE, in the middle, when acting on it is still cheap — while a cap of three would have
fired three times in the same session, and a guard that fires three times an hour is a guard that
gets silenced. The age cap is under the measured three hours for the same reason: it should
interrupt before the work is a session old, not after.

IT NEVER PUSHES UNASKED. Pushing is an outward-facing act on somebody's repository, and an
instrument that did it unasked would be exactly the kind of unattended side effect the agent
controls exist to refuse. By default this REPORTS, and the exit code is the verdict. `--land` IS
the ask, and it does all of landing or none of it.

PUSH AND MERGE ARE ONE STEP (2.27.0). Measured across this repository's own sessions: work was
reported "pushed" while it sat unmerged behind a pull request nothing would ever merge, and the
owner found it by reading a stale landing page. A pushed lane with no armed merge is STRANDED —
it looks finished from the terminal and is invisible on the page. So a pushed, unmerged branch
must carry an armed auto-merge, and `--land` pushes, opens the pull request and arms it together.
The required checks are the gate: auto-merge waits on them, so nothing lands on red.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from atlascore import ROOT, atlas


def merged_by_patch(branch: str, base_ref: str) -> bool:
    """Is every commit on `branch` already in `base_ref` as an equivalent patch? (A squash-merged lane.)

    `git branch -d` asks about ANCESTRY, which a squash merge destroys: the lane's commit is nowhere in the
    base's history even though its whole diff is. `git cherry` prints '-' for a patch the base already has
    and '+' for one it does not, so a lane is finished when it holds at least one commit and no '+'.
    """
    lines = [ln for ln in _git("cherry", base_ref, branch).split("\n") if ln.strip()]
    return bool(lines) and all(ln.startswith("-") for ln in lines)


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False, timeout=600)
    return done.stdout.strip() if done.returncode == 0 else ""


def bound() -> dict:
    return ((atlas().get("branch_policy") or {}).get("unpushed_bound")) or {}


def branches() -> list[dict]:
    """Every local branch, with what it holds that no remote does, and how old that work is."""
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    rows: list[dict] = []
    for name in _git("for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines():
        upstream = _git("rev-parse", "--abbrev-ref", f"{name}@{{upstream}}")
        # AGAINST ITS OWN UPSTREAM WHERE THERE IS ONE, against the base where there is not: a
        # branch nothing tracks holds ALL of its work unpushed, and comparing it to the base is
        # the only honest reading of that.
        reference = upstream or f"origin/{base}"
        unpushed = _git("rev-list", "--count", f"{reference}..{name}")
        oldest = _git("log", "-1", "--format=%ct", f"{reference}..{name}")
        rows.append({
            "branch": name,
            "tracks": upstream or None,
            "unpushed": int(unpushed) if unpushed.isdigit() else 0,
            "age_hours": round((time.time() - int(oldest)) / 3600, 1) if oldest.isdigit() else 0.0,
        })
    return rows


def unpushed_errors() -> list[str]:
    """What exceeds the declared bound, named per branch so the remedy is obvious."""
    limits = bound()
    if not limits:
        return ["branch_policy/unpushed_bound is not declared, so work accumulates unpushed and "
                "nothing says how much is too much until a worktree is gone"]
    rows = [r for r in branches() if r["unpushed"]]
    problems: list[str] = []
    for row in rows:
        if row["unpushed"] > int(limits.get("max_commits", 0)):
            problems.append(f"{row['branch']}: {row['unpushed']} unpushed commits against a bound "
                            f"of {limits['max_commits']} — push, or say why this one waits")
        if row["age_hours"] > float(limits.get("max_age_hours", 0)):
            problems.append(f"{row['branch']}: oldest unpushed work is {row['age_hours']}h old "
                            f"against a bound of {limits['max_age_hours']}h")
    if len(rows) > int(limits.get("max_branches_with_unpushed", 0)):
        problems.append(f"{len(rows)} branches hold unpushed work against a bound of "
                        f"{limits['max_branches_with_unpushed']} — one of them is forgotten, and "
                        "the one that is forgotten is never the one being looked at")
    if not str(limits.get("why") or "").strip():
        problems.append("branch_policy/unpushed_bound states no reason for its numbers, which "
                        "makes them a preference rather than a measurement")
    return problems


def landing(branch: str) -> dict:
    """The four states of one branch, because three of them look identical from a terminal.

    A branch can be pushed and still invisible: the forge's landing page renders the DEFAULT
    branch. It can be merged and still invisible: the page is cached. Reporting one number for
    all of that is how a finished change gets re-done.
    """
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    upstream = _git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    unmerged = _git("rev-list", "--count", f"origin/{base}..{branch}")
    return {
        "committed": bool(_git("rev-parse", "--verify", branch)),
        "pushed": bool(upstream) and not _git("rev-list", "--count", f"{upstream}..{branch}").strip("0"),
        "merged": (unmerged or "1") == "0",
        "published": "not observable from here — the rendered page is cached; the forge's API is "
                     "the authority, per staleness_discipline/platform_language_bar",
    }


def landing_verdict(pushed: bool, merged: bool, pr: dict | None, forge_ok: bool) -> str:
    """Whether anything will ever merge this branch. Pure, so the planted cases need no network.

    The dangerous state is the one that looks done: pushed, a pull request open, and nothing armed
    to merge it. It stays that way until somebody reads the landing page and notices.
    """
    if merged:
        return "merged"
    if not pushed:
        return "local"
    if not forge_ok:
        return "unknown: the forge was not asked — REFUSING to call it armed or stranded"
    if not pr:
        return "STRANDED: pushed with no pull request, so nothing will merge it"
    if pr.get("state") != "OPEN":
        return f"STRANDED: its pull request is {str(pr.get('state')).lower()} and it is not merged"
    if not pr.get("autoMergeRequest"):
        return f"STRANDED: pull request #{pr.get('number')} is open and nothing will merge it"
    return f"armed: pull request #{pr.get('number')} merges when its required checks pass"


def _pull_request(branch: str) -> tuple[dict | None, bool]:
    """(the branch's OPEN pull request or None, whether the forge answered at all).

    OPEN ONLY — FOUND ON THIS MECHANISM'S FIRST RUN. `gh pr view <branch>` answers with the most
    recent pull request for that NAME, merged ones included, so a lane reused after its first
    merge was matched to the dead request: no new one was opened, auto-merge was "armed" on a
    merged request as a no-op, and `ok` printed over it. The verdict line caught it, which is why
    land() now exits on the verdict rather than on its steps.
    """
    import json
    import shutil
    if not shutil.which("gh"):
        return None, False
    done = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "open",
                           "--json", "number,state,autoMergeRequest"],
                          cwd=ROOT, capture_output=True, text=True, check=False, timeout=600)
    if done.returncode != 0:
        return None, False
    found = json.loads(done.stdout or "[]")
    return (found[0] if found else None), True


CLEAN_GATES = (("scripts/atlas.py", "check"), ("scripts/atlas_test.py",))


def clean_checkout_errors(gates: tuple = CLEAN_GATES) -> str | None:
    """Run the gates in a throwaway checkout of HEAD; None when all pass, else which one failed.

    WHY (3.4.0). A lane was landed after its own clean-checkout run printed clean=1: the verdict was
    printed and nothing gated on it. The working tree held a __pycache__ that a clean checkout does not,
    so every local run was green and CI would have been red. The gate now lives in the landing itself,
    for every agent that lands through it, with no flag to skip it.
    """
    import sys
    import tempfile
    with tempfile.TemporaryDirectory() as parent:
        clean = Path(parent) / "clean"
        subprocess.run(["git", "worktree", "add", "-q", "--detach", str(clean), "HEAD"], cwd=ROOT, check=True, timeout=600)
        try:
            for gate in gates:
                done = subprocess.run([sys.executable, *gate], cwd=clean, capture_output=True, text=True, check=False, timeout=600)
                if done.returncode != 0:
                    tail = (done.stdout + done.stderr).strip().splitlines()[-3:]
                    return f"`{' '.join(gate)}` exited {done.returncode}: {' | '.join(tail)[:300]}"
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(clean)], cwd=ROOT, check=False, timeout=600)
    return None


def _land_once(branch: str) -> int:
    """Push, open the pull request if there is none, and arm auto-merge — all three, or report
    which step refused. The merge itself waits on the required checks, so nothing lands on red."""
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    # PULL BEFORE PUSH — branch_policy/push_conflict_rule, applied rather than recited. A push
    # built on a stale base either bounces as non-fast-forward or lands a merge CI never saw.
    if _git("status", "--porcelain"):
        print("land: the tree has uncommitted changes — REFUSING, a landing carries commits only")
        return 1
    for step in (["git", "fetch", "--prune", "origin"], ["git", "rebase", f"origin/{base}"]):
        done = subprocess.run(step, cwd=ROOT, capture_output=True, text=True, check=False, timeout=600)
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} {' '.join(step)}")
        if done.returncode != 0:
            subprocess.run(["git", "rebase", "--abort"], cwd=ROOT, capture_output=True, check=False, timeout=600)
            print("land: the rebase conflicts — aborted and REFUSING; resolve by hand, then land")
            return 1
    # DRIFT REVIEW ON A STRUCTURAL LANDING (3.6.0): surfaced in the session, not on a schedule.
    subprocess.run([sys.executable, str(ROOT / "scripts" / "staleness.py"), "review"], cwd=ROOT, check=False, timeout=600)
    refused = clean_checkout_errors()
    if refused:
        print(f"land: a CLEAN checkout of HEAD fails — REFUSING to push. {refused}")
        return 1
    # A LEASE, NOT A FORCE: after the rebase above a previously pushed lane needs one, and the
    # fetch a moment ago makes the lease mean "overwrite only what was just seen" — another
    # writer who pushed since is refused, which is push_conflict_rule's whole point.
    steps = [["git", "push", "--force-with-lease", "-u", "origin", branch]]
    pr, forge_ok = _pull_request(branch)
    if not forge_ok:
        print("land: the forge did not answer, so no merge can be armed — REFUSING to half-land")
        return 2
    if not pr:
        steps.append(["gh", "pr", "create", "--base", base, "--head", branch, "--fill"])
    steps.append(["gh", "pr", "merge", branch, "--auto", "--rebase"])
    import os
    landing_env = {**os.environ, "ATLAS_LANDING": "1"}  # the one caller .githooks/pre-push admits
    for step in steps:
        done = subprocess.run(step, cwd=ROOT, capture_output=True, text=True, check=False,
                              env=landing_env, timeout=600)
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} {' '.join(step[:4])}")
        if done.returncode != 0:
            print(f"land: stopped — {(done.stderr or done.stdout).strip()[:300]}")
            return 1
    pr, forge_ok = _pull_request(branch)
    verdict = landing_verdict(True, False, pr, forge_ok)
    print(f"{branch}: {verdict}")
    # THE STEPS SAYING ok IS NOT THE VERDICT. A merge armed on a dead request exits 0.
    return 0 if verdict.startswith("armed") else 1



def land(branch: str) -> int:
    """Land, and on failure fetch, rebase and try ONCE more — branch_policy/push_conflict_rule.

    The rule was declared and not implemented. MEASURED at 2.28.0: another lane merged while this
    one was landing, the merge step failed "Base branch was modified", and landing stopped with
    nothing armed. Every step is idempotent — fetch, rebase, a leased push, a pull request only if
    none is open, arming auto-merge — so repeating the whole sequence is safe, and the rule's own
    `escalate_after: one failed retry` is the bound: a second failure is two writers, not a race.
    """
    first = _land_once(branch)
    if first == 0:
        return 0
    print("land: failed once — fetching, rebasing and retrying ONCE, per push_conflict_rule")
    second = _land_once(branch)
    if second != 0:
        print("land: failed twice — escalating rather than retrying: two writers, not a race")
    return second

def untagged_version(version: str, remote_tags: set[str]) -> str | None:
    """The tag main's VERSION needs and does not have, or None. Pure, so it is planted-tested.

    MEASURED at 2.27.0: releases stopped at v2.8.0 while the contract reached 2.27.0 — nineteen
    versions with no tag, so the README's version badge, which reads tags, told every visitor
    v2.8.0. The release workflow's own header said a version with no tag is a claim with no
    artifact; nothing enforced it, because tagging was a step somebody had to remember.
    """
    wanted = f"v{version.strip()}"
    return None if not version.strip() or wanted in remote_tags else wanted


def sync() -> int:
    """After a merge: pull the default branch into its worktree and clear the finished lanes.

    THE PULL SIDE, which had no mechanism at all: a merged lane left its local branch, its gone
    upstream and a main worktree behind origin, and each was cleaned by hand when noticed. Every
    step here REFUSES rather than forcing — `git merge --ff-only` will not create a merge, and
    `git branch -d` will not delete a branch holding unmerged work, which is the guard.
    Worktrees are REPORTED, never removed: one may be a live session's checkout.
    """
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    subprocess.run(["git", "fetch", "--prune", "origin"], cwd=ROOT, capture_output=True, check=False, timeout=600)
    lines = _git("worktree", "list", "--porcelain").split("\n")
    trees = [(lines[i].split(" ", 1)[1], lines[j].split("refs/heads/", 1)[1])
             for i, line in enumerate(lines) if line.startswith("worktree ")
             for j in [next((k for k in range(i, min(i + 4, len(lines)))
                             if lines[k].startswith("branch ")), i)] if "refs/heads/" in lines[j]]
    for path, branch in trees:
        if branch != base:
            continue
        dirty = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                               capture_output=True, text=True, check=False, timeout=600).stdout.strip()
        if dirty:
            print(f"  skip {base} at {path}: uncommitted changes, never pulled over")
            continue
        done = subprocess.run(["git", "-C", path, "merge", "--ff-only", f"origin/{base}"],
                              capture_output=True, text=True, check=False, timeout=600)
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} fast-forward {base} at {path}")
    # PUBLISH IS THE LAST LANDING STATE: main carrying a VERSION with no tag is tagged here, and
    # the tag push fires the release workflow. Pushed as the gh user, so the workflow runs.
    version = _git("show", f"origin/{base}:VERSION")
    remote = {line.rsplit("refs/tags/", 1)[-1] for line in
              _git("ls-remote", "--tags", "origin").split("\n") if "refs/tags/" in line}
    wanted = untagged_version(version, {r.removesuffix("^{}") for r in remote})
    if wanted:
        steps = [["git", "tag", "-a", wanted, f"origin/{base}", "-m", f"contract {wanted}"],
                 ["git", "push", "origin", wanted]]
        for step in steps:
            done = subprocess.run(step, cwd=ROOT, capture_output=True, text=True, check=False, timeout=600)
            print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} {' '.join(step[:3])}")
            if done.returncode != 0:
                print(f"  release not tagged: {(done.stderr or done.stdout).strip()[:200]}")
                break
    else:
        print(f"  ok  v{version.strip()} is tagged on origin — nothing to publish")
    base_ref = f"origin/{base}" if _git("rev-parse", "--verify", "--quiet", f"origin/{base}") else base
    gone = [b for b in _git("for-each-ref", "--format=%(refname:short) %(upstream:track)",
                            "refs/heads/").split("\n") if b.endswith("[gone]")]
    live = {branch for _, branch in trees}
    for row in gone:
        branch = row.split()[0]
        if branch in live:
            print(f"  keep {branch}: its upstream is gone but a worktree has it checked out")
            continue
        done = subprocess.run(["git", "branch", "-d", branch], cwd=ROOT,
                              capture_output=True, text=True, check=False, timeout=600)
        if done.returncode == 0:
            print(f"  ok  {branch}")
            continue
        # A SQUASH-MERGED LANE SHARES NO COMMIT WITH THE BASE (3.24.0), so `git branch -d` reads it as unmerged
        # and --sync kept it forever, printing "holds work not in the default branch" about work that WAS in it.
        # `git cherry` compares PATCHES, not ancestry: every line '-' means the base already carries that change.
        if merged_by_patch(branch, base_ref):
            subprocess.run(["git", "branch", "-D", branch], cwd=ROOT, capture_output=True, timeout=600, check=False)
            print(f"  ok  {branch} — squash-merged: every patch it holds is already in {base_ref}")
        else:
            print(f"  keep {branch} — holds work not in the default branch")
    import json
    import shutil
    if shutil.which("gh"):
        listed = subprocess.run(["gh", "pr", "list", "--state", "open", "--json",
                                 "number,headRefName,isCrossRepository,autoMergeRequest,isDraft"],
                                cwd=ROOT, capture_output=True, text=True, check=False, timeout=600)
        for pr in json.loads(listed.stdout or "[]") if listed.returncode == 0 else []:
            if pr.get("autoMergeRequest") or pr.get("isCrossRepository") or pr.get("isDraft"):
                continue  # armed already; a fork's request is a maintainer's call; a draft is unfinished
            done = subprocess.run(["gh", "pr", "merge", str(pr["number"]), "--auto", "--rebase"],
                                  cwd=ROOT, capture_output=True, text=True, check=False, timeout=600)
            print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} armed stranded pull request "
                  f"#{pr['number']} ({pr['headRefName']})")
    hooks = _git("config", "--get", "core.hooksPath")
    if hooks != ".githooks":
        print("  NOTE core.hooksPath is not .githooks, so a bare push of a lane is not refused "
              "here — `git config core.hooksPath .githooks`")
    for path, branch in trees:
        if branch != base and _git("rev-list", "--count", f"origin/{base}..{branch}") == "0":
            print(f"  FINISHED worktree {path} ({branch}, ahead=0) — remove it from its own session")
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv and "--sync" in argv:
        return sync()
    if argv and "--land" in argv:
        return land(_git("rev-parse", "--abbrev-ref", "HEAD"))
    limits = bound()
    rows = branches()
    for row in sorted(rows, key=lambda r: -r["unpushed"]):
        state = "pushed" if not row["unpushed"] else f"{row['unpushed']} unpushed, {row['age_hours']}h"
        print(f"{row['branch']:<52} {state:<26} tracks {row['tracks'] or 'NOTHING'}")
    holding = [r for r in rows if r["unpushed"]]
    print(f"{len(rows)} branches, {len(holding)} holding unpushed work "
          f"({sum(r['unpushed'] for r in holding)} commits) against bounds: "
          f"{limits.get('max_commits')} commits, {limits.get('max_age_hours')}h, "
          f"{limits.get('max_branches_with_unpushed')} branches")
    current = _git("rev-parse", "--abbrev-ref", "HEAD")
    state = landing(current)
    print(f"{current}: committed={state['committed']} pushed={state['pushed']} "
          f"merged={state['merged']}")
    pr, forge_ok = _pull_request(current) if state["pushed"] and not state["merged"] else (None, True)
    verdict = landing_verdict(state["pushed"], state["merged"], pr, forge_ok)
    print(f"  will it merge: {verdict}")
    print(f"  published: {state['published']}")
    problems = unpushed_errors()
    if verdict.startswith("STRANDED"):
        problems.append(f"{current} is {verdict} — `python scripts/branchstate.py --land` arms it")
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: it REPORTS unless asked. `--land` pulls, rebases, pushes, opens the pull request")
    print("       and arms auto-merge; `--sync` pulls the default branch and clears finished lanes.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
