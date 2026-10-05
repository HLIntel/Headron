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

from atlascore import ROOT, atlas, worktree


def merged_by_patch(branch: str, base_ref: str) -> bool:
    """Is every commit on `branch` already in `base_ref` as an equivalent patch? (A squash-merged lane.)

    `git branch -d` asks about ANCESTRY, which a squash merge destroys: the lane's commit is nowhere in the
    base's history even though its whole diff is. `git cherry` prints '-' for a patch the base already has
    and '+' for one it does not, so a lane is finished when it holds at least one commit and no '+'.
    """
    lines = [ln for ln in _git("cherry", base_ref, branch).split("\n") if ln.strip()]
    return bool(lines) and all(ln.startswith("-") for ln in lines)


def unlanded_commits(branch: str, base_ref: str) -> list[str]:
    """The commits on `branch` whose CHANGE `base_ref` does not hold — empty means closing it loses nothing.

    WHY CONTENT AND NOT NAMES (3.42.0). Two pull requests were closed as "already on main" because every file
    they touched existed on main; one carried a landing fix never released, the other a freshness gate. A file
    list says where a change went, never whether it arrived. `git cherry` compares patches, and a lane
    squashed from several commits (which no single patch matches) is landed when merging it into the base
    would change nothing: `merge-tree` writes the base's own tree. A conflict counts as unlanded.
    """
    ahead = [ln[2:] for ln in _git("cherry", "-v", base_ref, branch).split("\n") if ln.startswith("+")]
    if ahead:
        merged = _git("merge-tree", "--write-tree", base_ref, branch).split("\n")[0]
        if merged and merged == _git("rev-parse", f"{base_ref}^{{tree}}"):
            return []
    return ahead


STRANDED_AT = 25  # unlanded commits past which a lane is read as forked from a replaced history


def landed(branch: str, base_ref: str) -> int:
    """`thea landed <branch>` — exit 0 when the base holds every change on the branch, 1 with the rest listed."""
    try:
        _tree()
    except ValueError as refused:
        print(refused)
        return 2
    if not _git("rev-parse", "--verify", "--quiet", branch):
        print(f"refused: '{branch}' is not a ref here — `git fetch origin {branch}` first")
        return 2
    rest = unlanded_commits(branch, base_ref)
    for line in rest[:STRANDED_AT]:
        print(f"  unlanded {line}")
    if len(rest) >= STRANDED_AT:
        # A LANE ON A REPLACED HISTORY (3.45.0): hundreds of "unlanded" commits mean the branch forked from
        # a history the base no longer has — it can never merge, and closing it strands its real change.
        print(f"  STRANDED — {len(rest)} commits the base lacks: this lane is built on a replaced history. "
              "Port its own change by patch onto the current base now; never close it before that lands")
    print(f"{branch}: {'LANDED — closing or deleting it loses nothing' if not rest else f'{len(rest)} commit(s) NOT in {base_ref}'}")
    return 1 if rest else 0


def _tree() -> Path:
    """The repository being landed: the caller's own, found from the working directory (atlascore.worktree)."""
    return worktree()


def _is_atlas() -> bool:
    """True only when the tree being landed IS this atlas; a consumer lands in its own repository."""
    return _tree() == ROOT.resolve()


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)
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


def stale_remotes(base: str = "main") -> list[tuple[str, float]]:
    """(remote head no local branch tracks, hours since its last commit): the forge's pile-up, read offline.

    FOUR SAT ON THE FORGE FOR DAYS (3.48.0), each from a pull request CLOSED unmerged: delete-on-merge
    only fires on a merge, and nothing here read refs/remotes, so the pile-up was invisible to every gate.
    """
    tracked = set(_git("for-each-ref", "--format=%(upstream:short)", "refs/heads/").split())
    rows = []
    for line in _git("for-each-ref", "--format=%(refname:short) %(committerdate:unix)", "refs/remotes/origin/").splitlines():
        name, _, stamp = line.partition(" ")
        if name not in tracked | {"origin", f"origin/{base}"} and stamp.isdigit():
            rows.append((name, round((time.time() - int(stamp)) / 3600, 1)))
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
    horizon = float(limits.get("remote_max_age_hours", 0))
    problems += [f"{name}: on the forge, tracked by no local branch, last commit {age}h old against a bound of "
                 f"{horizon}h — `branchstate.py --sync` deletes it once merged or its pull request closed; "
                 "otherwise land it" for name, age in stale_remotes() if age > horizon]
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
        "committed": not _git("status", "--porcelain"),  # a ref always exists; a dirty tree is the unsaved state
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
                          cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)
    if done.returncode != 0:
        return None, False
    found = json.loads(done.stdout or "[]")
    return (found[0] if found else None), True


CLEAN_GATES = (("scripts/atlas.py", "check"), ("scripts/atlas_test.py",))
# One gate's wall-clock budget. The planted suite alone measured 795s on an idle host (3.49.0), so the
# 600s every git call uses killed a GREEN suite mid-run and the landing died on a traceback. Kept above
# the measured run with headroom for a loaded host; a gate that overruns it is reported, never raised.
GATE_SECONDS = 1800


def consumer_gates(clean: Path, files: list[str], change: str) -> tuple[list[list[str]], list[str]]:
    """The gates this atlas routes for each changed file of a CONSUMER's tree: (runnable argv, not-run notes).

    The atlas is the filter between an agent and its repository: it decides WHAT proves a change, and the
    change is proven and landed in the consumer's own clean checkout. A gate the route leaves undeclared or
    absent is reported, never invented. Identical argv (one test runner for many files) runs once.
    """
    import json
    import sys
    runnable: list[list[str]] = []
    notes: list[str] = []
    for rel in files:
        if not (clean / rel).is_file():
            continue
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "atlas.py"), "gate", rel, "--change", change, "--json"],
                              cwd=clean, capture_output=True, text=True, check=False, timeout=600)
        try:
            records = json.loads(done.stdout or "[]")
        except json.JSONDecodeError:
            notes.append(f"{rel}: the atlas gave no gate record")
            continue
        for rec in records if isinstance(records, list) else [records]:
            if rec.get("state") == "runnable" and rec.get("argv"):
                if rec["argv"] not in runnable:
                    runnable.append(rec["argv"])
            else:
                notes.append(f"{rel}: {rec.get('gate')} {rec.get('state')}")
    return runnable, notes


def _consumer_change_class() -> str:
    """The change class a consumer pins in its own `.atlas.yaml`; source_change when it pins none."""
    pin = _tree() / ".atlas.yaml"
    if pin.is_file():
        from atlascore import strict_yaml
        declared = ((strict_yaml(pin.read_text(encoding="utf-8"), str(pin)) or {}).get("atlas") or {}).get("change_class")
        if declared:
            return str(declared)
    return "source_change"


def clean_checkout_errors(gates: list[list[str]] | None = None) -> str | None:
    """Run the gates in a throwaway checkout of HEAD; None when all pass, else which one failed.

    WHY (3.4.0). A lane was landed after its own clean-checkout run printed clean=1: the verdict was
    printed and nothing gated on it. The gate lives in the landing itself, with no flag to skip it.
    With no gates given: this atlas's own gates when landing the atlas, else the gates it routes for the
    consumer's changed files. A gate whose tool is missing refuses the landing and names the tool.
    """
    import sys
    import tempfile
    with tempfile.TemporaryDirectory() as parent:
        clean = Path(parent) / "clean"
        subprocess.run(["git", "worktree", "add", "-q", "--detach", str(clean), "HEAD"], cwd=_tree(), check=True, timeout=600)
        try:
            if gates is None and _is_atlas():
                gates = [[sys.executable, *g] for g in CLEAN_GATES]
            elif gates is None:
                base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
                changed = [f for f in _git("diff", "--name-only", f"origin/{base}...HEAD").split("\n") if f]
                gates, notes = consumer_gates(clean, changed, _consumer_change_class())
                for note in notes:
                    print(f"  not run  {note}")
            for gate in gates:
                try:
                    done = subprocess.run(gate, cwd=clean, capture_output=True, text=True, check=False,
                                          timeout=GATE_SECONDS)
                except FileNotFoundError:
                    return f"`{gate[0]}` is not installed — install it or declare the gate absent for this route"
                except subprocess.TimeoutExpired:
                    return f"NOT RUN `{' '.join(gate)}`: still running after {GATE_SECONDS}s, so it has no verdict"
                if done.returncode == 75:  # atlas_test.BUSY: another suite holds the machine — NOT RUN, not a failure
                    return f"NOT RUN `{' '.join(gate)}`: {(done.stdout + done.stderr).strip()[-300:]}"
                if done.returncode != 0:
                    tail = (done.stdout + done.stderr).strip().splitlines()[-3:]
                    return f"`{' '.join(gate)}` exited {done.returncode}: {' | '.join(tail)[:300]}"
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(clean)], cwd=_tree(), check=False, timeout=600)
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
    # TAG THE TIP BY NAME BEFORE THE REBASE (3.25.0, the shape's own closer, second sighting). A rebase
    # moves HEAD first; if the push is then refused — branch protection, a missing permission, a gate — the
    # commit is reachable only from the reflog, while the branch reports ahead=0 and a clean tree. A named
    # tag survives that, so recovery is `git reset --hard <tag>` instead of reading reflog by hand.
    rescue = f"lane/{branch.replace('/', '-')}/{_git('rev-parse', '--short', 'HEAD')}"
    subprocess.run(["git", "tag", "-f", rescue], cwd=_tree(), capture_output=True, check=False, timeout=600)
    print(f"  ok  tagged the tip {rescue} — if anything below is refused, the commit is still there")
    for step in (["git", "fetch", "--prune", "origin"], ["git", "rebase", f"origin/{base}"]):
        done = subprocess.run(step, cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} {' '.join(step)}")
        if done.returncode != 0 and step[1] == "fetch":
            print(f"land: the fetch failed — nothing changed; {(done.stderr or done.stdout).strip()[:300]}")
            return 1
        if done.returncode != 0:  # HAND (65): a conflict is the same on every retry, so land never retries it
            subprocess.run(["git", "rebase", "--abort"], cwd=_tree(), capture_output=True, check=False, timeout=600)
            print(f"land: the rebase onto origin/{base} conflicts — aborted and REFUSING; rebase by hand, then land")
            return 65
    # DRIFT REVIEW ON A STRUCTURAL LANDING (3.6.0): surfaced in the session, not on a schedule.
    if _is_atlas():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "staleness.py"), "review"], cwd=ROOT, check=False, timeout=600)
    refused = clean_checkout_errors()
    if refused:
        busy = refused.startswith("NOT RUN")
        print(f"land: a CLEAN checkout of HEAD {'was NOT judged' if busy else 'fails'} — REFUSING to push. {refused}")
        return 75 if busy else 65  # a failing gate fails again on a retry: it is the commit, not a race
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
        done = subprocess.run(step, cwd=_tree(), capture_output=True, text=True, check=False,
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



RED = {"failure", "cancelled", "timed_out", "startup_failure"}


def rekick_plan(runs: list[dict]) -> tuple[list[int], bool, list[str]]:
    """(run ids to rerun, whether only a fresh push restarts the rest, jobs that RAN and failed).

    A RUNNER OUTAGE IS NOT A RED CHECK. MEASURED at 3.50.0 during a GitHub Actions incident: every
    failed job read "not acquired by Runner of type hosted" — no runner name and no step — and the
    merge sat BLOCKED behind checks that never executed. Only such a job is retried; a job that ran
    and failed is the commit, and a retry would be the blind retry the bug rule forbids. CodeQL
    default setup runs as event `dynamic`, which the API refuses to rerun ("cannot be retried"),
    and reopening the pull request did not restart it either — only a new head commit does.
    """
    rerun, push, real = [], False, []
    for run in runs:
        failed = [j for j in run["jobs"] if j.get("conclusion") in RED]
        ran = [j["name"] for j in failed if j.get("runner_name") or j.get("steps")]
        real += ran
        if failed and not ran:
            push = push or run.get("event") == "dynamic"
            rerun += [] if run.get("event") == "dynamic" else [run["id"]]
    return rerun, push, real


def rekick(branch: str) -> int:
    """Restart the checks an outage stranded on this lane's head; refuse when any check really failed."""
    import json
    import os
    head = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain") or head != _git("rev-parse", f"origin/{branch}"):
        print("rekick: the lane is not exactly its pushed head — REFUSING; land it first")
        return 1

    def api(path: str) -> dict:
        done = subprocess.run(["gh", "api", path], cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)
        if done.returncode != 0:
            raise SystemExit(f"rekick: the forge refused {path}: {(done.stderr or done.stdout).strip()[:300]}")
        return json.loads(done.stdout)
    runs = [{**r, "jobs": api(f"repos/{{owner}}/{{repo}}/actions/runs/{r['id']}/jobs")["jobs"]}
            for r in api(f"repos/{{owner}}/{{repo}}/actions/runs?head_sha={head}")["workflow_runs"]
            if r.get("conclusion") in RED]
    rerun, push, real = rekick_plan(runs)
    if real:
        print(f"rekick: these checks RAN and failed — the commit, not the platform; nothing retried: {real}")
        return 1
    for run_id in rerun:
        done = subprocess.run(["gh", "run", "rerun", str(run_id), "--failed"], cwd=_tree(),
                              capture_output=True, text=True, check=False, timeout=600)
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} gh run rerun {run_id} --failed")
    if push:  # a new committer date is a new head with the SAME tree, so the gates that passed still hold
        subprocess.run(["git", "commit", "--amend", "--no-edit", "--quiet"], cwd=_tree(), check=True, timeout=600)
        if _git("rev-parse", "HEAD^{tree}") != _git("rev-parse", f"{head}^{{tree}}"):
            raise SystemExit("rekick: the re-stamped head changed the tree — REFUSING to push")
        done = subprocess.run(["git", "push", "--force-with-lease", "origin", branch], cwd=_tree(), capture_output=True,
                              text=True, check=False, env={**os.environ, "ATLAS_LANDING": "1"}, timeout=600)
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} re-pushed {branch} with the same tree: dynamic runs restart")
        if done.returncode != 0:
            return 1
    print(f"rekick: {len(rerun)} run(s) restarted{', head re-pushed' if push else ''}; nothing stranded" if rerun or push
          else "rekick: nothing stranded — no failed run on this head lacked a runner")
    return 0


def land(branch: str) -> int:
    """Land, and on failure fetch, rebase and try ONCE more — branch_policy/push_conflict_rule.

    The rule was declared and not implemented. MEASURED at 2.28.0: another lane merged while this
    one was landing, the merge step failed "Base branch was modified", and landing stopped with
    nothing armed. Every step is idempotent — fetch, rebase, a leased push, a pull request only if
    none is open, arming auto-merge — so repeating the whole sequence is safe, and the rule's own
    `escalate_after: one failed retry` is the bound: a second failure is two writers, not a race.
    A rebase conflict or a failing gate (65) is the commit itself, so it is never retried: MEASURED
    at 3.49.0, both were retried and then mislabelled "two writers".
    """
    first = _land_once(branch)
    if first == 75 and _suite_host_free():  # NOT RUN, and the holder finished: the same landing, not a race retry
        print("land: the machine's planted suite finished — landing again")
        first = _land_once(branch)
    if first in (0, 65, 75):  # 65 needs a hand, 75 NOT RUN: neither is a second writer, so no retry (3.49.0)
        if first == 75:
            print("land: NOT RUN — the machine's suite lock was taken again; nothing was pushed. Land again later")
        return first
    print("land: failed once — fetching, rebasing and retrying ONCE, per push_conflict_rule")
    second = _land_once(branch)
    if second != 0:
        print("land: failed twice — escalating rather than retrying: two writers, not a race")
    return second

def _suite_host_free(wait: float = 1800.0) -> bool:
    """Wait for atlas_test.host_lock's machine lock to fall free; False at the deadline.

    A NOT RUN landing once told a person to wait on a PID and land again: done by hand twice in one
    session (3.49.0). The lock is the signal, not the PID: a PID is reused, a released flock is not.
    """
    import fcntl

    from resilience import wait_until
    path = Path(_git("rev-parse", "--path-format=absolute", "--git-common-dir")) / "atlas-suite-host.lock"
    holder = []

    def free() -> bool:
        with open(path, "a+") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return True  # closing releases it for the gate about to take it
            except BlockingIOError:
                if not holder:
                    handle.seek(0)
                    holder.append(handle.read().strip() or "an unrecorded process")
                    print(f"land: NOT RUN — {holder[0]} holds the machine's suite lock; waiting up to {wait:.0f}s")
                return False
    if wait_until(free, timeout=wait, interval=15):
        return True
    print(f"land: the machine's planted suite ({holder[0]}) still holds its lock after {wait:.0f}s")
    return False


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
    subprocess.run(["git", "fetch", "--prune", "origin"], cwd=_tree(), capture_output=True, check=False, timeout=600)
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
            done = subprocess.run(step, cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)
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
        done = subprocess.run(["git", "branch", "-d", branch], cwd=_tree(),
                              capture_output=True, text=True, check=False, timeout=600)
        if done.returncode == 0:
            print(f"  ok  {branch}")
            continue
        # A SQUASH-MERGED LANE SHARES NO COMMIT WITH THE BASE (3.24.0), so `git branch -d` reads it as unmerged
        # and --sync kept it forever, printing "holds work not in the default branch" about work that WAS in it.
        # `git cherry` compares PATCHES, not ancestry: every line '-' means the base already carries that change.
        if merged_by_patch(branch, base_ref):
            subprocess.run(["git", "branch", "-D", branch], cwd=_tree(), capture_output=True, timeout=600, check=False)
            print(f"  ok  {branch} — squash-merged: every patch it holds is already in {base_ref}")
        else:
            print(f"  keep {branch} — holds work not in the default branch")
    import json
    import shutil
    if shutil.which("gh"):
        listed = subprocess.run(["gh", "pr", "list", "--state", "open", "--json",
                                 "number,headRefName,isCrossRepository,autoMergeRequest,isDraft"],
                                cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)
        for pr in json.loads(listed.stdout or "[]") if listed.returncode == 0 else []:
            if pr.get("autoMergeRequest") or pr.get("isCrossRepository") or pr.get("isDraft"):
                continue  # armed already; a fork's request is a maintainer's call; a draft is unfinished
            done = subprocess.run(["gh", "pr", "merge", str(pr["number"]), "--auto", "--rebase"],
                                  cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)
            print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} armed stranded pull request "
                  f"#{pr['number']} ({pr['headRefName']})")
    sweep_remotes(base, base_ref)
    refresh_install([path for path, branch in trees if branch == base], version.strip())
    hooks = _git("config", "--get", "core.hooksPath")
    if hooks != ".githooks":
        print("  NOTE core.hooksPath is not .githooks, so a bare push of a lane is not refused "
              "here — `git config core.hooksPath .githooks`")
    for path, branch in trees:
        if branch != base and _git("rev-list", "--count", f"origin/{base}..{branch}") == "0":
            print(f"  FINISHED worktree {path} ({branch}, ahead=0) — remove it from its own session")
    return 0


def sweep_remotes(base: str, base_ref: str) -> None:
    """Delete each remote head that is merged or whose pull request closed; an open one, or none, is kept.

    A CLOSED REQUEST LOSES NOTHING: the forge keeps its commits at refs/pull/<n>/head after the branch goes.
    """
    import json
    for name, _age in stale_remotes(base):
        branch = name.removeprefix("origin/")
        listed = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "all", "--json", "number,state"],
                                cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)
        prs = json.loads(listed.stdout or "[]") if listed.returncode == 0 else None
        if prs is None or any(pr["state"] == "OPEN" for pr in prs):
            print(f"  keep {name}: {'the forge did not answer' if prs is None else 'its pull request is open'}")
            continue
        why = "merged" if merged_by_patch(name, base_ref) else (
            f"pull request #{prs[0]['number']} {prs[0]['state'].lower()}" if prs else "")
        if not why:
            print(f"  keep {name}: no pull request and unmerged — land it or delete it")
            continue
        done = subprocess.run(["git", "push", "origin", "--delete", branch], cwd=_tree(),
                              capture_output=True, text=True, check=False, timeout=600)
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} deleted remote {branch} — {why}")


def refresh_install(trees: list[str], version: str) -> None:
    """Re-point the installed CLI at the default branch IN PLACE: one environment, overwritten, never a second.

    DRIFT FOLLOWS EVERY UPDATE (3.37.0 measured an install two versions stale). An editable install tracks the
    checkout's code, but not new entry points or dependencies, so a VERSION mismatch reinstalls with --force.
    """
    import shutil

    from doctor import installed_cli, installed_drift
    launchers, reported, _root = installed_cli()
    if not launchers or not trees:
        print("  ok  no installed thea to keep current" if not launchers else "  note no default-branch worktree")
        return
    if len(launchers) > 1:
        print(f"  FAIL {len(launchers)} thea launchers on PATH ({', '.join(launchers)}) — remove all but one")
    drift = installed_drift(launchers[0])
    if reported == version and not drift:
        print(f"  ok  installed thea reports {version}, contract lock identical")
        return
    done = subprocess.run([shutil.which("uv") or "uv", "tool", "install", "--force", "--editable", trees[0]],
                          capture_output=True, text=True, check=False, timeout=600)
    print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} reinstalled thea in place: {reported or 'unknown'} -> {version}")


def main(argv: list[str] | None = None) -> int:
    if argv and "--sync" in argv:
        return sync()
    if argv and "--land" in argv:
        return land(_git("rev-parse", "--abbrev-ref", "HEAD"))
    if argv and "--rekick" in argv:
        return rekick(_git("rev-parse", "--abbrev-ref", "HEAD"))
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
    problems = unpushed_errors() + ([] if state["committed"] else [f"{current} holds uncommitted changes — nothing in them is saved"])
    if verdict.startswith("STRANDED"):
        problems.append(f"{current} is {verdict} — `python scripts/branchstate.py --land` arms it")
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: it REPORTS unless asked. `--land` pulls, rebases, pushes, opens the pull request")
    print("       and arms auto-merge; `--sync` pulls the default branch and clears finished lanes.")
    return 1 if problems else 0


def worktree_report() -> dict:
    """Every worktree, classified by the kinds atlas.yaml/worktree_policy declares.

    A REPORT, NOT A GATE, and deliberately. The right number of worktrees is a property of the
    MACHINE, not of the repository — a CI runner has one, a developer mid-session has several — and
    a gate that fires on a correct developer machine is a gate that gets switched off. What it does
    owe is a count beside the classification: a testbed nobody removed and no testbed at all print
    the same silence otherwise.
    """
    import re
    import subprocess

    from atlascore import atlas
    policy = atlas().get("worktree_policy") or {}
    lane = str((atlas().get("branch_policy") or {}).get("worktree_pattern") or "")
    out = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=_tree(),
                         capture_output=True, timeout=120, check=False).stdout.decode()
    trees, current = [], {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = {"path": line.split(" ", 1)[1], "branch": "", "detached": False}
            trees.append(current)
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1]
        elif line.strip() == "detached":
            current["detached"] = True
    # CLASSIFIED BY WHAT A WORKTREE HOLDS, NEVER BY WHERE IT SITS. The first version matched
    # branch_policy/worktree_pattern against the path and put every real lane in "unclassified":
    # that pattern is `../thea-software-wt/<language>-<topic>` and nothing on this machine is laid
    # out that way, because the worktrees are created by a harness that chooses its own directory.
    # A path is a rendering; the BRANCH is the identity (code-quality §3). The stale pattern is
    # reported rather than quietly worked around.
    default = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    for tree in trees:
        branch = tree["branch"].rsplit("/", 1)[-1]
        if tree["detached"]:
            tree["kind"] = "testbed"
        elif branch == default:
            tree["kind"] = "main"
        elif tree["branch"]:
            tree["kind"] = "lane"
        else:
            tree["kind"] = "unclassified"
    pattern_matches = [t for t in trees if lane and re.search(re.escape(lane.split("<")[0].strip("./")), t["path"])]
    counts: dict[str, int] = {}
    for tree in trees:
        counts[tree["kind"]] = counts.get(tree["kind"], 0) + 1
    return {"schema": 1, "command": "worktrees", "kinds_declared": sorted(policy.get("kinds") or {}),
            "counts": counts, "trees": trees,
            # A DECLARED LAYOUT NOTHING ON DISK USES is worth printing beside the classification: it
            # is a convention a reader will follow and a tool will not produce.
            "declared_layout": lane,
            "declared_layout_matches": len(pattern_matches)}


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
