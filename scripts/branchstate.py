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

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import agents
from atlascore import ROOT, atlas, worktree


def merged_by_patch(branch: str, base_ref: str) -> bool:
    """Is every commit on `branch` already in `base_ref` as an equivalent patch? (A squash-merged lane.)

    `git branch -d` asks about ANCESTRY, which a squash merge destroys: the lane's commit is nowhere in the
    base's history even though its whole diff is. `git cherry` prints '-' for a patch the base already has
    and '+' for one it does not, so a lane is finished when it holds at least one commit and no '+'.
    """
    return _carries(_git("cherry", base_ref, branch))


def _carries(cherry: str) -> bool:
    lines = [ln for ln in cherry.split("\n") if ln.strip()]
    return bool(lines) and all(ln.startswith("-") for ln in lines)


def finished_lane(branch: str, base_ref: str) -> bool:
    """Ahead=0 by ancestry, or every patch already in the base — the two shapes a landed lane leaves."""
    return _git("rev-list", "--count", f"{base_ref}..{branch}") == "0" or merged_by_patch(branch, base_ref)


def live_cwds() -> set[str] | None:
    """Every directory a running process stands in; None when nothing can say (no lsof)."""
    try:
        out = subprocess.run(["lsof", "-d", "cwd", "-Fn"], capture_output=True, text=True, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return {os.path.realpath(ln[1:]) for ln in out.stdout.splitlines() if ln.startswith("n")}


def tree_kept(path: str, branch: str, base_ref: str, live: set[str] | None, idle_hours: float) -> str | None:
    """Why a lane's worktree stays, or None when it is finished AND abandoned and removing it loses nothing.

    FORGOTTEN TREES (3.50.0): --sync printed "FINISHED, remove it from its own session" and nobody did; a
    rebase-landed lane was not even printed, since ancestry cannot see it. Seven sat for hours. Each test
    below is a way the removal could destroy something; every one refuses rather than guesses."""
    root = os.path.realpath(path)
    stamp = subprocess.run(
        ["git", "-C", path, "log", "-g", "-1", "--format=%ct", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    ).stdout.strip()
    idle = (time.time() - int(stamp)) / 3600 if stamp.isdigit() else idle_hours
    reasons = [
        (not finished_lane(branch, base_ref), f"holds work not in {base_ref} — land it"),
        (live is None, "nothing can say whether a session stands in it"),
        (any(c == root or c.startswith(root + os.sep) for c in live or ()), "a running process stands in it"),
        (bool(_git("-C", path, "status", "--porcelain")), "uncommitted or untracked files"),
        (idle < idle_hours, f"touched {idle:.1f}h ago, under the {idle_hours}h idle bound"),
    ]
    return next((why for hit, why in reasons if hit), None)


def carried_by(branch: str, refs: list[str], cherry=None) -> str | None:
    """The first of `refs` already holding every patch on `branch`, else None.

    WHY. Two open pull requests sat DIRTY with auto-merge armed while main, or another open lane, already
    carried every change they held: nothing would ever merge them and nothing said so. `--sync` names them.
    """
    cherry = cherry or (lambda b, r: _git("cherry", r, b))
    return next((ref for ref in refs if _carries(cherry(branch, ref))), None)


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
    if not _git(
        "rev-parse", "--verify", "--quiet", f"{base_ref}^{{commit}}"
    ):  # a failed cherry printed nothing: LANDED
        print(f"refused: base '{base_ref}' is not a ref here — nothing can be compared against it")
        return 2
    rest = unlanded_commits(branch, base_ref)
    for line in rest[:STRANDED_AT]:
        print(f"  unlanded {line}")
    if len(rest) >= STRANDED_AT:
        # A LANE ON A REPLACED HISTORY (3.45.0): hundreds of "unlanded" commits mean the branch forked from
        # a history the base no longer has — it can never merge, and closing it strands its real change.
        print(
            f"  STRANDED — {len(rest)} commits the base lacks: this lane is built on a replaced history. "
            "Port its own change by patch onto the current base now; never close it before that lands"
        )
    print(
        f"{branch}: {'LANDED — closing or deleting it loses nothing' if not rest else f'{len(rest)} commit(s) NOT in {base_ref}'}"
    )
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


def _gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)


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
        # A LANDED LANE HOLDS NOTHING UNPUSHED (3.50.0): counted by ancestry, a rebase-landed lane read as
        # forgotten work forever, and seven of them kept the session-end gate red until nobody read it.
        unpushed = "0" if finished_lane(name, f"origin/{base}") else _git("rev-list", "--count", f"{reference}..{name}")
        oldest = _git("log", "-1", "--format=%ct", f"{reference}..{name}")
        rows.append(
            {
                "branch": name,
                "tracks": upstream or None,
                "unpushed": int(unpushed) if unpushed.isdigit() else 0,
                "age_hours": round((time.time() - int(oldest)) / 3600, 1) if oldest.isdigit() else 0.0,
            }
        )
    return rows


def stale_remotes(base: str = "main") -> list[tuple[str, float]]:
    """(remote head no local branch tracks, hours since its last commit): the forge's pile-up, read offline.

    FOUR SAT ON THE FORGE FOR DAYS (3.48.0), each from a pull request CLOSED unmerged: delete-on-merge
    only fires on a merge, and nothing here read refs/remotes, so the pile-up was invisible to every gate.
    A FORGE-OWNED HEAD IS NOBODY'S WORK (3.53.0): a merge queue's temporary refs failed a fresh clone, so
    the prefixes declared in `unpushed_bound/forge_owned_prefixes` are skipped by name, never by guess.
    """
    tracked = set(_git("for-each-ref", "--format=%(upstream:short)", "refs/heads/").split())
    owned = tuple(f"origin/{prefix}" for prefix in bound().get("forge_owned_prefixes") or ())
    rows = []
    for line in _git(
        "for-each-ref", "--format=%(refname:short) %(committerdate:unix)", "refs/remotes/origin/"
    ).splitlines():
        name, _, stamp = line.partition(" ")
        if name not in tracked | {"origin", f"origin/{base}"} and stamp.isdigit() and not name.startswith(owned):
            rows.append((name, round((time.time() - int(stamp)) / 3600, 1)))
    return rows


def unpushed_errors() -> list[str]:
    """What exceeds the declared bound, named per branch so the remedy is obvious."""
    limits = bound()
    if not limits:
        return [
            "branch_policy/unpushed_bound is not declared, so work accumulates unpushed and "
            "nothing says how much is too much until a worktree is gone"
        ]
    rows = [r for r in branches() if r["unpushed"]]
    problems: list[str] = []
    for row in rows:
        if row["unpushed"] > int(limits.get("max_commits", 0)):
            problems.append(
                f"{row['branch']}: {row['unpushed']} unpushed commits against a bound "
                f"of {limits['max_commits']} — push, or say why this one waits"
            )
        if row["age_hours"] > float(limits.get("max_age_hours", 0)):
            problems.append(
                f"{row['branch']}: oldest unpushed work is {row['age_hours']}h old "
                f"against a bound of {limits['max_age_hours']}h"
            )
    if len(rows) > int(limits.get("max_branches_with_unpushed", 0)):
        problems.append(
            f"{len(rows)} branches hold unpushed work against a bound of "
            f"{limits['max_branches_with_unpushed']} — one of them is forgotten, and "
            "the one that is forgotten is never the one being looked at"
        )
    horizon = float(limits.get("remote_max_age_hours", 0))
    problems += [
        f"{name}: on the forge, tracked by no local branch, last commit {age}h old against a bound of "
        f"{horizon}h — `branchstate.py --sync` deletes it once merged or its pull request closed; "
        "otherwise land it"
        for name, age in stale_remotes()
        if age > horizon
    ]
    if not str(limits.get("why") or "").strip():
        problems.append(
            "branch_policy/unpushed_bound states no reason for its numbers, which "
            "makes them a preference rather than a measurement"
        )
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
    if pr.get("inQueue"):  # a queued request may carry no auto-merge: the queue rebases and merges it
        return f"queued: pull request #{pr.get('number')} is in the merge queue, which rebases and merges it"
    if not pr.get("autoMergeRequest"):
        return f"STRANDED: pull request #{pr.get('number')} is open and nothing will merge it"
    # ARMED IS NOT ENOUGH (3.50.0). main requires a branch up to date with it, and auto-merge never
    # rebases: the first lane to merge left every other armed lane BEHIND, waiting forever while this
    # line printed "armed". DIRTY waits the same way, on a conflict nobody was told about.
    status = str(pr.get("mergeStateStatus") or "").upper()
    if status == "BEHIND" and not pr.get("queue"):  # a merge queue tests the rebased result itself
        return f"STRANDED: pull request #{pr.get('number')} is armed but behind its base — `--sync` rebases it"
    if status == "DIRTY":
        return f"STRANDED: pull request #{pr.get('number')} is armed but conflicts with its base — rebase it by hand"
    if pr.get("unreported"):
        return f"STRANDED: pull request #{pr.get('number')} waits on {', '.join(pr['unreported'])}, which nothing ran"
    return f"armed: pull request #{pr.get('number')} merges when its required checks pass"


def _pull_request(branch: str) -> tuple[dict | None, bool]:
    """(the branch's OPEN pull request or None, whether the forge answered at all).

    OPEN ONLY — FOUND ON THIS MECHANISM'S FIRST RUN. `gh pr view <branch>` answers with the most
    recent pull request for that NAME, merged ones included, so a lane reused after its first
    merge was matched to the dead request: no new one was opened, auto-merge was "armed" on a
    merged request as a no-op, and `ok` printed over it. The verdict line caught it, which is why
    land() now exits on the verdict rather than on its steps.
    """

    if not shutil.which("gh"):
        return None, False
    fields = "number,state,autoMergeRequest,mergeStateStatus,statusCheckRollup"
    done = _gh("pr", "list", "--head", branch, "--state", "open", "--json", fields)
    if done.returncode != 0:
        return None, False
    pr = (json.loads(done.stdout or "[]") or [None])[0]
    if pr:
        rules = _base_rules()
        pr["unreported"] = _unreported(pr.pop("statusCheckRollup", None) or [], rules)
        pr["queue"] = any(r.get("type") == "merge_queue" for r in rules)
        q = 'query($n:Int!){repository(owner:"{owner}",name:"{repo}"){pullRequest(number:$n){isInMergeQueue}}}'
        asked = _gh("api", "graphql", "-F", f"n={pr['number']}", "-f", f"query={q}") if pr["queue"] else None
        pr["inQueue"] = bool(asked and asked.returncode == 0 and '"isInMergeQueue":true' in asked.stdout)
    return pr, True


def _base_rules() -> list[dict]:
    """The rules GitHub applies to the default base, or [] when the forge does not answer."""
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    done = _gh("api", f"repos/{{owner}}/{{repo}}/rules/branches/{base}")
    return json.loads(done.stdout or "[]") if done.returncode == 0 else []


def _unreported(rollup: list[dict], rules: list[dict]) -> list[str]:
    """Required checks with no run once every reported check has finished: nothing produces them.

    FOUND 3.51.0: an org transfer switched CodeQL default setup off, and three armed pull requests
    waited on `Analyze` forever while landing_verdict printed "armed"."""
    if not rollup or any(c.get("status", "COMPLETED") != "COMPLETED" or c.get("state") == "PENDING" for c in rollup):
        return []
    seen = {c.get("name") or c.get("context") for c in rollup}
    need = [
        c["context"]
        for r in rules
        if r.get("type") == "required_status_checks"
        for c in (r.get("parameters") or {}).get("required_status_checks", [])
    ]
    return [n for n in need if n not in seen]


# CI'S CHEAP STEPS RUN FIRST (3.50.0). A lane passed this suite locally and its PR went red on
# `ruff format --check`, a step only CI ran; the re-land cost another full suite. "{python}" is this interpreter.
CLEAN_GATES = (
    ("ruff", "format", "--check", "."),
    ("ruff", "check", "."),
    ("{python}", "scripts/atlas.py", "check"),
    ("{python}", "scripts/atlas_test.py"),
)
# One gate's wall-clock budget. The planted suite alone measured 795s on an idle host (3.49.0), so the
# 600s every git call uses killed a GREEN suite mid-run and the landing died on a traceback. Kept above
# the measured run with headroom for a loaded host; a gate that overruns it is reported, never raised.
GATE_SECONDS = 1800


def run_gate(gate: list[str], cwd: Path, keep: int = 4096) -> tuple[int, str]:
    """Run one clean gate with its output in a file; return its code and the last `keep` bytes.

    MEASURED at 3.50.0: a looping test printed one line for its hour-long deadline into a captured pipe,
    the landing held ~45 GB of it, and the kernel's memory killer took the landing (rc 137, nothing pushed).
    """
    import tempfile

    with tempfile.TemporaryFile() as out:
        done = subprocess.run(gate, cwd=cwd, stdout=out, stderr=subprocess.STDOUT, check=False, timeout=GATE_SECONDS)
        out.seek(max(0, out.seek(0, 2) - keep))
        return done.returncode, out.read().decode(errors="replace")


def consumer_records(tree: Path, files: list[str], change: str) -> list[dict]:
    """Every gate record this atlas routes for each changed file of a CONSUMER's tree, as `atlas.py gate --json`
    prints it; a file the atlas gave no record for is one record with state `no_record`. ONE producer for the
    landing and for `verify` run in a consumer."""
    out: list[dict] = []
    for rel in files:
        if not (tree / rel).is_file():
            continue
        done = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "atlas.py"), "gate", rel, "--change", change, "--json"],
            cwd=tree,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
        try:
            records = json.loads(done.stdout or "[]")
        except json.JSONDecodeError:
            out.append({"path": rel, "gate": "atlas", "state": "no_record", "why": "the atlas gave no gate record"})
            continue
        out += [rec | {"path": rel} for rec in (records if isinstance(records, list) else [records])]
    return out


def consumer_gates(clean: Path, files: list[str], change: str) -> tuple[list[list[str]], list[str]]:
    """The gates this atlas routes for each changed file of a CONSUMER's tree: (runnable argv, not-run notes).

    The atlas is the filter between an agent and its repository: it decides WHAT proves a change, and the
    change is proven and landed in the consumer's own clean checkout. A gate the route leaves undeclared or
    absent is reported, never invented. Identical argv (one test runner for many files) runs once.
    """
    runnable: list[list[str]] = []
    notes: list[str] = []
    for rec in consumer_records(clean, files, change):
        if rec.get("state") == "runnable" and rec.get("argv"):
            if rec["argv"] not in runnable:
                runnable.append(rec["argv"])
        elif rec.get("state") == "no_record":
            notes.append(f"{rec['path']}: {rec['why']}")
        else:
            notes.append(f"{rec['path']}: {rec.get('gate')} {rec.get('state')}")
    return runnable, notes


def _consumer_change_class() -> str:
    """The change class a consumer pins in its own `.atlas.yaml`; source_change when it pins none."""
    pin = _tree() / ".atlas.yaml"
    if pin.is_file():
        from atlascore import strict_yaml

        declared = ((strict_yaml(pin.read_text(encoding="utf-8"), str(pin)) or {}).get("atlas") or {}).get(
            "change_class"
        )
        if declared:
            return str(declared)
    return "source_change"


PASS_LEDGER_BYTES = 4096  # a byte cap, not a count: the ledger of passed (tree, gates) keys never grows past it


def _pass_key(tree: str, gates: list[list[str]], clean: Path) -> str:
    """The content a clean-checkout verdict is OF: the tree object and the exact gate argv, the
    throwaway checkout's path normalised out. A name (branch, PR, lane) is never part of it."""
    import hashlib

    argv = [[str(a).replace(str(clean), "<clean>") for a in g] for g in gates]
    return hashlib.sha256(json.dumps([tree, argv]).encode()).hexdigest()


def _pass_ledger() -> Path:
    return Path(_git("rev-parse", "--path-format=absolute", "--git-common-dir")) / "atlas-clean-pass"


def _passed(key: str) -> bool:
    try:
        return key in _pass_ledger().read_text(encoding="utf-8").split()
    except OSError:
        return False


def _record_pass(key: str) -> None:
    path = _pass_ledger()
    try:
        keys = path.read_text(encoding="utf-8").split()
    except OSError:
        keys = []
    keys.append(key)
    while len(" ".join(keys)) > PASS_LEDGER_BYTES:
        keys.pop(0)
    path.write_text("\n".join(keys) + "\n", encoding="utf-8")


def _verified(clean: Path, gates: list[list[str]]) -> bool:
    """True when verify.py's recorded PASS rows cover every gate, on content byte-identical to `clean`.

    ONE PROOF, NOT TWO (3.51.0). verify.py and the landing kept separate pass ledgers, so a tree verify had
    just passed re-ran the planted suite inside --land, measured at 14 minutes. The digest is of the clean
    checkout, so a file untracked or uncommitted at verify time makes it differ and the gates re-run.
    """
    from verify import input_digest, reuse_evidence  # noqa: PLC0415

    done = (atlas().get("verification_policy") or {}).get("done_set") or []
    have = {tuple(r["argv"]) for r in reuse_evidence(done, input_digest(clean)).values()}
    return all(tuple("python" if a == sys.executable else a for a in g) in have for g in gates)


def clean_checkout_errors(gates: list[list[str]] | None = None) -> str | None:
    """Run the gates in a throwaway checkout of HEAD; None when all pass, else which one failed.

    WHY (3.4.0). A lane was landed after its own clean-checkout run printed clean=1: the verdict was
    printed and nothing gated on it. The gate lives in the landing itself, with no flag to skip it.
    With no gates given: this atlas's own gates when landing the atlas, else the gates it routes for the
    consumer's changed files. A gate whose tool is missing refuses the landing and names the tool.
    """
    import tempfile

    # A PASS IS A FACT ABOUT A TREE (3.50.0). A land refused after its suite passed — a push or forge
    # failure, a lock wait, a rekick — re-ran the whole planted suite on the identical tree, queued behind
    # every other lane's suite on the machine lock. Only a PASS is remembered; a failure or NOT RUN never is.
    tree = _git("rev-parse", "HEAD^{tree}")
    with tempfile.TemporaryDirectory() as parent:
        clean = Path(parent) / "clean"
        subprocess.run(
            ["git", "worktree", "add", "-q", "--detach", str(clean), "HEAD"], cwd=_tree(), check=True, timeout=600
        )
        try:
            if gates is None and _is_atlas():
                gates = [[sys.executable if a == "{python}" else a for a in g] for g in CLEAN_GATES]
            elif gates is None:
                base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
                changed = [f for f in _git("diff", "--name-only", f"origin/{base}...HEAD").split("\n") if f]
                gates, notes = consumer_gates(clean, changed, _consumer_change_class())
                for note in notes:
                    print(f"  not run  {note}")
            key = _pass_key(tree, gates, clean)
            if _passed(key):
                print(f"  ok   clean checkout of tree {tree[:12]} already passed these gates — not re-run")
                return None
            if _is_atlas() and _verified(clean, gates):
                print(f"  ok   verify.py passed these gates on content byte-identical to tree {tree[:12]} — not re-run")
                _record_pass(key)
                return None
            for gate in gates:
                try:
                    code, out = run_gate(gate, clean)
                except FileNotFoundError:
                    return f"`{gate[0]}` is not installed — install it or declare the gate absent for this route"
                except subprocess.TimeoutExpired:
                    return f"NOT RUN `{' '.join(gate)}`: still running after {GATE_SECONDS}s, so it has no verdict"
                if code == 75:  # atlas_test.BUSY: another suite holds the machine — NOT RUN, not a failure
                    return f"NOT RUN `{' '.join(gate)}`: {out.strip()[-300:]}"
                if code != 0:
                    tail = out.strip().splitlines()[-3:]
                    return f"`{' '.join(gate)}` exited {code}: {' | '.join(tail)[:300]}"
            _record_pass(key)
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
    # NOTHING TO LAND IS FINISHED, NOT FAILED (second sighting). A lane at ahead=0 ran the clean-checkout
    # suite, then failed on `gh pr create` ("no commits between"), retried, and escalated as two writers.
    if _git("rev-list", "--count", f"origin/{base}..{branch}") == "0":
        print(f"land: nothing to land — {branch} is ahead=0 of origin/{base}; FINISHED, remove the worktree and branch")
        return 0
    # DRIFT REVIEW ON A STRUCTURAL LANDING (3.6.0): surfaced in the session, not on a schedule.
    if _is_atlas():
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "staleness.py"), "review"], cwd=ROOT, check=False, timeout=600
        )
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
        done = subprocess.run(
            step, cwd=_tree(), capture_output=True, text=True, check=False, env=landing_env, timeout=600
        )
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} {' '.join(step[:4])}")
        if done.returncode != 0:
            print(f"land: stopped — {(done.stderr or done.stdout).strip()[:300]}")
            return 1
    pr, forge_ok = _pull_request(branch)
    verdict = landing_verdict(True, False, pr, forge_ok)
    print(f"{branch}: {verdict}")
    agents.field("field_landed", {"pr": (pr or {}).get("number"), "armed": verdict.startswith("armed")})
    # THE STEPS SAYING ok IS NOT THE VERDICT. A merge armed on a dead request exits 0.
    return 0 if verdict.startswith("armed") else 1


LAND_WAIT = 3600.0  # one bound on every NOT RUN wait in a landing, not per retry


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
    first, deadline = _land_once(branch), time.monotonic() + LAND_WAIT
    # NOT RUN while another session's suite holds the lock: wait and land again until the deadline. ONE
    # retry lost the lock to a sibling suite twice in a row (3.50.0) and nothing was pushed.
    while first == 75 and time.monotonic() < deadline and _suite_host_free(deadline - time.monotonic()):
        print("land: the machine's planted suite finished — landing again")
        first = _land_once(branch)
    if first in (0, 65, 75):  # 65 needs a hand, 75 NOT RUN: neither is a second writer, so no retry (3.49.0)
        if first == 75:
            print(f"land: NOT RUN — the suite lock stayed taken for {LAND_WAIT:.0f}s; nothing was pushed")
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
    A lane's worktree is removed only when `tree_kept` finds no reason to keep it; else the reason prints.
    """
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    subprocess.run(["git", "fetch", "--prune", "origin"], cwd=_tree(), capture_output=True, check=False, timeout=600)
    lines = _git("worktree", "list", "--porcelain").split("\n")
    trees = [
        (lines[i].split(" ", 1)[1], lines[j].split("refs/heads/", 1)[1])
        for i, line in enumerate(lines)
        if line.startswith("worktree ")
        for j in [next((k for k in range(i, min(i + 4, len(lines))) if lines[k].startswith("branch ")), i)]
        if "refs/heads/" in lines[j]
    ]
    for path, branch in trees:
        if branch != base:
            continue
        dirty = subprocess.run(
            ["git", "-C", path, "status", "--porcelain"], capture_output=True, text=True, check=False, timeout=600
        ).stdout.strip()
        if dirty:
            print(f"  skip {base} at {path}: uncommitted changes, never pulled over")
            continue
        done = subprocess.run(
            ["git", "-C", path, "merge", "--ff-only", f"origin/{base}"],
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} fast-forward {base} at {path}")
    # PUBLISH IS THE LAST LANDING STATE: main carrying a VERSION with no tag is tagged here, and
    # the tag push fires the release workflow. Pushed as the gh user, so the workflow runs.
    version = _git("show", f"origin/{base}:VERSION")
    remote = {
        line.rsplit("refs/tags/", 1)[-1]
        for line in _git("ls-remote", "--tags", "origin").split("\n")
        if "refs/tags/" in line
    }
    wanted = untagged_version(version, {r.removesuffix("^{}") for r in remote})
    if wanted:
        steps = [
            ["git", "tag", "-a", wanted, f"origin/{base}", "-m", f"contract {wanted}"],
            ["git", "push", "origin", wanted],
        ]
        for step in steps:
            done = subprocess.run(step, cwd=_tree(), capture_output=True, text=True, check=False, timeout=600)
            print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} {' '.join(step[:3])}")
            if done.returncode != 0:
                print(f"  release not tagged: {(done.stderr or done.stdout).strip()[:200]}")
                break
    else:
        print(f"  ok  v{version.strip()} is tagged on origin — nothing to publish")
    base_ref = f"origin/{base}" if _git("rev-parse", "--verify", "--quiet", f"origin/{base}") else base
    gone = [
        b
        for b in _git("for-each-ref", "--format=%(refname:short) %(upstream:track)", "refs/heads/").split("\n")
        if b.endswith("[gone]")
    ]
    live = {branch for _, branch in trees}
    for row in gone:
        branch = row.split()[0]
        if branch in live:
            print(f"  keep {branch}: its upstream is gone but a worktree has it checked out")
            continue
        done = subprocess.run(
            ["git", "branch", "-d", branch], cwd=_tree(), capture_output=True, text=True, check=False, timeout=600
        )
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

    if shutil.which("gh"):
        listed = _gh(
            "pr",
            "list",
            "--state",
            "open",
            "--json",
            "number,headRefName,isCrossRepository,autoMergeRequest,isDraft,mergeStateStatus",
        )
        open_prs = json.loads(listed.stdout or "[]") if listed.returncode == 0 else []
        for pr in open_prs:
            others = [f"origin/{o['headRefName']}" for o in open_prs if o["number"] != pr["number"]]
            carrier = carried_by(f"origin/{pr['headRefName']}", [base_ref, *others])
            if carrier:
                print(f"  CLOSE #{pr['number']} ({pr['headRefName']}): every patch it holds is already in {carrier}")
        queue = any(r.get("type") == "merge_queue" for r in _base_rules())
        for pr in open_prs:  # under a merge queue, update-branch would eject a queued request
            if (
                pr.get("autoMergeRequest")
                and pr.get("mergeStateStatus") == "BEHIND"
                and not pr.get("isCrossRepository")
                and not queue
            ):
                # As the gh user, never GITHUB_TOKEN: the rebased head must re-run the required checks.
                done = _gh("pr", "update-branch", str(pr["number"]), "--rebase")
                print(
                    f"  {'ok ' if done.returncode == 0 else 'FAIL'} rebased armed pull request "
                    f"#{pr['number']} ({pr['headRefName']}) that sat behind {base}"
                )
            elif pr.get("autoMergeRequest") and pr.get("mergeStateStatus") == "DIRTY":
                print(
                    f"  CONFLICT #{pr['number']} ({pr['headRefName']}): armed, and nothing merges it until rebased by hand"
                )
        for pr in open_prs:
            if pr.get("autoMergeRequest") or pr.get("isCrossRepository") or pr.get("isDraft"):
                continue  # armed already; a fork's request is a maintainer's call; a draft is unfinished
            done = _gh("pr", "merge", str(pr["number"]), "--auto", "--rebase")
            print(
                f"  {'ok ' if done.returncode == 0 else 'FAIL'} armed stranded pull request "
                f"#{pr['number']} ({pr['headRefName']})"
            )
    sweep_remotes(base, base_ref)
    from doctor import refresh_install

    refresh_install([path for path, branch in trees if branch == base], version.strip())
    hooks = _git("config", "--get", "core.hooksPath")
    if hooks != ".githooks":
        print(
            "  NOTE core.hooksPath is not .githooks, so a bare push of a lane is not refused "
            "here — `git config core.hooksPath .githooks`"
        )
    live, idle = live_cwds(), float(bound().get("max_age_hours", 2))
    for path, branch in trees:
        if branch == base:
            continue
        why = tree_kept(path, branch, base_ref, live, idle)
        if why:
            print(f"  keep worktree {path} ({branch}): {why}")
            continue
        gone = subprocess.run(
            ["git", "worktree", "remove", path], cwd=_tree(), capture_output=True, text=True, check=False, timeout=60
        )
        if gone.returncode == 0:
            subprocess.run(["git", "branch", "-D", branch], cwd=_tree(), capture_output=True, check=False, timeout=60)
        print(f"  {'ok ' if gone.returncode == 0 else 'FAIL'} removed finished worktree {path} ({branch})")
    return 0


def sweep_remotes(base: str, base_ref: str) -> None:
    """Delete each remote head that is merged or whose pull request closed; an open one, or none, is kept.

    A CLOSED REQUEST LOSES NOTHING: the forge keeps its commits at refs/pull/<n>/head after the branch goes.
    """
    for name, _age in stale_remotes(base):
        branch = name.removeprefix("origin/")
        listed = _gh("pr", "list", "--head", branch, "--state", "all", "--json", "number,state")
        prs = json.loads(listed.stdout or "[]") if listed.returncode == 0 else None
        if prs is None or any(pr["state"] == "OPEN" for pr in prs):
            print(f"  keep {name}: {'the forge did not answer' if prs is None else 'its pull request is open'}")
            continue
        why = (
            "merged"
            if merged_by_patch(name, base_ref)
            else (f"pull request #{prs[0]['number']} {prs[0]['state'].lower()}" if prs else "")
        )
        if not why:
            print(f"  keep {name}: no pull request and unmerged — land it or delete it")
            continue
        done = subprocess.run(
            ["git", "push", "origin", "--delete", branch],
            cwd=_tree(),
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
        print(f"  {'ok ' if done.returncode == 0 else 'FAIL'} deleted remote {branch} — {why}")


def main(argv: list[str] | None = None) -> int:
    if argv and "--sync" in argv:
        return sync()
    if argv and "--land" in argv:
        return land(_git("rev-parse", "--abbrev-ref", "HEAD"))
    if argv and "--rekick" in argv:
        from ghaudit import rekick  # noqa: PLC0415 — the forge's Actions runs, audited where the forge is

        return rekick(_git("rev-parse", "--abbrev-ref", "HEAD"), _tree())
    limits = bound()
    rows = branches()
    for row in sorted(rows, key=lambda r: -r["unpushed"]):
        state = "pushed" if not row["unpushed"] else f"{row['unpushed']} unpushed, {row['age_hours']}h"
        print(f"{row['branch']:<52} {state:<26} tracks {row['tracks'] or 'NOTHING'}")
    holding = [r for r in rows if r["unpushed"]]
    print(
        f"{len(rows)} branches, {len(holding)} holding unpushed work "
        f"({sum(r['unpushed'] for r in holding)} commits) against bounds: "
        f"{limits.get('max_commits')} commits, {limits.get('max_age_hours')}h, "
        f"{limits.get('max_branches_with_unpushed')} branches"
    )
    current = _git("rev-parse", "--abbrev-ref", "HEAD")
    state = landing(current)
    print(f"{current}: committed={state['committed']} pushed={state['pushed']} merged={state['merged']}")
    pr, forge_ok = _pull_request(current) if state["pushed"] and not state["merged"] else (None, True)
    verdict = landing_verdict(state["pushed"], state["merged"], pr, forge_ok)
    print(f"  will it merge: {verdict}")
    print(f"  published: {state['published']}")
    problems = unpushed_errors() + (
        [] if state["committed"] else [f"{current} holds uncommitted changes — nothing in them is saved"]
    )
    if verdict.startswith("STRANDED"):
        problems.append(f"{current} is {verdict} — `python scripts/branchstate.py --land` arms it")
    for problem in problems:
        print(f"- {problem}")
    trees = worktree_report()
    print(f"worktrees: {trees['counts']} (kinds declared: {', '.join(trees['kinds_declared'])})")
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
    out = subprocess.run(
        ["git", "worktree", "list", "--porcelain"], cwd=_tree(), capture_output=True, timeout=120, check=False
    ).stdout.decode()
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
    return {
        "schema": 1,
        "command": "worktrees",
        "kinds_declared": sorted(policy.get("kinds") or {}),
        "counts": counts,
        "trees": trees,
        # A DECLARED LAYOUT NOTHING ON DISK USES is worth printing beside the classification: it
        # is a convention a reader will follow and a tool will not produce.
        "declared_layout": lane,
        "declared_layout_matches": len(pattern_matches),
    }


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
