#!/usr/bin/env python3
"""`headron ci`: run the jobs scripts/cipipeline.py declares, on this machine, as one graph of microprograms.

NATIVE, NOTHING TRANSLATED: each step's command runs as declared under `bash -euo pipefail -c`, bounded by its
timeout_s (scripts/gaterunner.py), and answers a MicroResult. scripts/micrograph.py orders the job units, blocks
a unit whose need did not answer ok, and stops one past its job's budget. Every non-ok answer is never a pass:
  - a step that exits non-zero: refused, and its job stops there;
  - a step that times out, needs a tool not on PATH, or names an action only a hosted runner holds: unknown.
Exit 0 only when every selected unit answered ok; 1 when one was refused; 2 when one could not decide.

A clean whole run (the CONTRACT jobs, HEAD committed) fans out: each unit runs in its own detached worktree of
HEAD as `.github/ci-local.sh --unit <unit>`, at most CI_LOCAL_WORKERS at once and past the first only while
slot.admitter() grants it (measured idle cores, one grant per settle). A dirty tree, width 1, or named jobs run in place, one unit at a time.

proves: a unit is ok only when every one of its steps exited 0 within its bound, and only after its needs were ok
does_not_prove: that a step's command checks what its name says; that is the step's own instrument
closed_by: cilocal_test.py, which plants a failed need, a hung step, a missing tool, a killed child and a dirty tree

See also: cipipeline.py (job declarations), micrograph.py (DAG ordering), microprogram.py (step results),
gaterunner.py (step execution), slot.py (core budgeting).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from types import ModuleType

import cipipeline
import gaterunner
import micrograph
from atlascore import git_run, text_of
from microprogram import MicroResult
from slot import admitter, take

HOOK_MARK = "# installed by .github/ci-local.sh --install-hook"
WIDTH = 3  # units at once: the contract DAG never has more ready, and each is one process beside a bounded example pool
PIPELINE = "scripts/cipipeline.py"
# A unit's exit code IS its status: anything else (a signal, a crash) is unknown, never ok.
STATUS_OF = {0: "ok", 1: "refused", 2: "unknown"}
KEEP = 1 << 20  # bytes of a step's output kept: the suite's verdict line is its last


def _width() -> int:
    raw = os.environ.get("CI_LOCAL_WORKERS", "")
    if raw and (not raw.isdigit() or int(raw) < 1):
        raise SystemExit(f"cilocal: CI_LOCAL_WORKERS={raw!r} is not a positive integer; refusing to guess a width")
    return int(raw or WIDTH)


def _committed_head() -> str | None:
    """HEAD when the tree IS HEAD. A dirty tree runs in place: a worktree of HEAD would pass without its edits."""
    status = git_run(None, "status", "--porcelain")
    if status.returncode or status.stdout.strip():
        return None
    rev = git_run(None, "rev-parse", "HEAD")
    if rev.returncode:
        return None
    return rev.stdout.strip()


def load(path: str | Path) -> ModuleType:
    """The tree's own declaration, by path: a lane is judged by ITS jobs, never by the installed root's."""
    if Path(path).resolve() == Path(cipipeline.__file__).resolve():
        return cipipeline
    spec = importlib.util.spec_from_file_location("pipeline_under_test", path)
    if spec is None or spec.loader is None or not Path(path).is_file():
        raise SystemExit(f"ci: no pipeline at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # a dataclass resolves its own module by name while it is built
    spec.loader.exec_module(module)
    return module


def _answer(unit: str, status: str, why: str, next_step: str, output: str = "") -> MicroResult:
    return MicroResult(
        unit, "1", status, output or None, evidence_refs=(why,), next=None if status == "ok" else next_step
    )


def run_step(step: cipipeline.Step, unit: str, *, tree: Path, env: dict[str, str], left_s: float) -> MicroResult:
    """One step as a microprogram: ok only on exit 0 within its bound."""
    again = f"run `headron ci {unit.split(':')[0]}` and fix {step.name!r}"
    if step.unavailable:
        return _answer(unit, "unknown", f"{step.name}: {step.unavailable}", f"answer {step.name!r} where it can run")
    if missing := [tool for tool in step.tools if not shutil.which(tool, path=env.get("PATH"))]:
        return _answer(
            unit, "unknown", f"{step.name}: {', '.join(missing)} not on PATH", f"install {missing[0]}, then {again}"
        )
    timeout = min(step.timeout_s, left_s)
    if timeout <= 0:
        return _answer(unit, "unknown", f"{step.name}: no time left in the job's budget", again)
    try:
        result = gaterunner.run(
            ["bash", "-euo", "pipefail", "-c", step.run],
            cwd=tree / step.cwd,
            timeout=timeout,
            env={**env, **step.env},
            keep=KEEP,
            merge=True,
        )
    except subprocess.TimeoutExpired:
        return _answer(
            unit, "unknown", f"{step.name}: timed out after {timeout:g}s", f"find what it waits on, then {again}"
        )
    except OSError as exc:
        return _answer(unit, "unknown", f"{step.name}: could not start: {exc}", again)
    print(result.stdout, end="" if result.stdout.endswith("\n") or not result.stdout else "\n", flush=True)
    if result.returncode:
        return _answer(unit, "refused", f"{step.name}: exit {result.returncode}", again, result.stdout[-4000:])
    return _answer(unit, "ok", step.name, "")


def run_unit(job: cipipeline.Job, unit: str, *, temp: Path, artifacts: Path, timeout_s: float) -> MicroResult:
    """Every step of one unit in order, in this tree; the first non-ok step is the unit's answer."""
    scratch = temp / unit.replace(":", "-")
    scratch.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    shard = unit.partition(":")[2]
    env = {
        **os.environ,
        "CI": "true",
        "HEADRON_CI_TEMP": str(scratch),
        "HEADRON_CI_ARTIFACTS": str(artifacts),
        "HEADRON_CI_SHARD": shard,
    }
    deadline = time.monotonic() + timeout_s
    for step in job.steps:
        print(f"::: {unit} / {step.name}", flush=True)
        answer = run_step(step, unit, tree=Path.cwd(), env=env, left_s=deadline - time.monotonic())
        if not answer.actionable:
            return answer
    return _answer(unit, "ok", f"{len(job.steps)} steps", "")


class _Done:
    """A unit run in place: its answer is known when `start` returns."""

    def __init__(self, answer: MicroResult) -> None:
        self.answer = answer

    def poll(self) -> MicroResult | None:
        return self.answer

    def stop(self) -> None:
        return None


class _Child:
    """A unit in its own detached worktree of HEAD; its log prints whole when it ends, then its tree goes."""

    def __init__(self, unit: str, tree: Path, head: str, env: dict[str, str]) -> None:
        subprocess.run(["git", "worktree", "add", "-q", "--detach", str(tree), head], check=True, timeout=600)
        print(f"::: started {unit}", flush=True)
        self.unit, self.tree, self.began = unit, tree, time.monotonic()
        with tree.with_suffix(".log").open("wb") as log:
            self.process = subprocess.Popen(
                [str(tree / ".github" / "ci-local.sh"), "--unit", unit],
                cwd=tree,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

    def _close(self) -> None:
        print(text_of(self.tree.with_suffix(".log"), errors="replace"), end="", flush=True)
        subprocess.run(["git", "worktree", "remove", "--force", str(self.tree)], check=False, timeout=600)

    def poll(self) -> MicroResult | None:
        if (rc := self.process.poll()) is None:
            return None
        self._close()
        status = STATUS_OF.get(rc, "unknown")
        return _answer(self.unit, status, f"child exit {rc}", f"run `headron ci --unit {self.unit}` in place")

    def stop(self) -> None:
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=30)
        self._close()


def run_graph(jobs: Sequence[cipipeline.Job], runner_temp: Path, *, head: str | None, width: int) -> int:
    """Every unit of `jobs` through the graph; 0 only when all answered ok."""
    graph = cipipeline.nodes(jobs)
    job_of = {unit: job for job in jobs for unit in job.units()}
    artifacts = Path(os.environ.get("HEADRON_CI_ARTIFACTS") or runner_temp / ".artifacts")
    began = time.monotonic()
    held = None
    if head and width > 1:
        # ONE ADMISSION. Each unit's planted suite takes the machine slot (atlas_test.host_lock), so three
        # admitted units queued behind two slots (MEASURED: guards-1 231 s -> 651 s, "slot: queued behind"
        # in the ci-admit land). The graph takes the slot once and hands it down through HEADRON_SLOT_HELD,
        # so the admitter above is the only gate on how many units run.
        held = take(f"ci graph at {head[:12]}", wait=float(os.environ.get("HEADRON_SLOT_WAIT", "3600")))
        trees = runner_temp / "units"
        trees.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "HEADRON_CI_ARTIFACTS": str(artifacts)}
        env.pop("VIRTUAL_ENV", None)
        count = iter(range(len(graph)))

        def start(node: micrograph.Node, timeout_s: float) -> micrograph.Running:
            return _Child(node.name, trees / str(next(count)), head, env)

        admit: Callable[[], bool] = admitter()
    else:
        width = 1

        def start(node: micrograph.Node, timeout_s: float) -> micrograph.Running:
            return _Done(
                run_unit(job_of[node.name], node.name, temp=runner_temp, artifacts=artifacts, timeout_s=timeout_s)
            )

        admit = lambda: True  # noqa: E731
    try:
        results = micrograph.run(graph, start, budget_s=sum(node.timeout_s for node in graph), width=width, admit=admit)
    finally:
        if held is not None:
            held.close()
            os.environ.pop("HEADRON_SLOT_HELD", None)
    print(micrograph.summary(results.items()))
    print(
        f"ci: {sum(r.actionable for r in results.values())}/{len(results)} ok — width {width}, {time.monotonic() - began:.0f}s"
    )
    return verdict(results.values())


def verdict(results: Iterable[MicroResult]) -> int:
    """0 all ok; 1 when any was refused (a decided no outranks what it blocked); else 2 when any is undecided."""
    statuses = {result.status for result in results}
    return 1 if "refused" in statuses else 2 if statuses - {"ok"} else 0


# WHY A LANDING NEEDS A HAND, declared (field ledger 2026-11: 47 of 182 landings exited 65, cause unrecorded,
# so no fix could be ranked). Every 65 in branchstate._land_once names one; one that names none is "unattributed".
LAND_REFUSALS = ("uninspectable", "diverged", "rebase", "merge", "gate", "replay", "post_ci")
LAND_UNATTRIBUTED = "unattributed"  # a 65 whose cause no `refuse` named: the role known, its value not
refusal: dict[str, str] = {}  # this landing's cause; record_landing consumes it, so none reaches the next landing


def refuse(reason: str, refused: str = "") -> int:
    """Name the cause of a 65 for this landing's field_landed event, and return 65."""
    if reason not in LAND_REFUSALS:
        raise ValueError(f"land: undeclared refusal reason {reason!r}; declare it in LAND_REFUSALS")
    refusal.clear()
    refusal.update({"reason": reason, **({"gate": gate_name(refused)} if reason == "gate" else {})})
    return 65


def gate_name(refused: str) -> str:
    """The gate's identity from a refusal: its script and arguments, never its output or a machine path.

    The refusal text carries the gate's output tail, and the ledger records what ran, never what it printed.
    """
    quoted = refused.split("`")
    if len(quoted) < 3 or not quoted[1].split():
        return "unattributed"
    argv = quoted[1].split()
    script = next((i for i, a in enumerate(argv) if a.endswith((".py", ".sh"))), 0)
    return " ".join([Path(argv[script]).name, *argv[script + 1 :]])[:120]


def record_landing(code: int, attempts: int) -> int:
    """Record every completed landing operation, including refused and exhausted attempts."""
    import agents  # noqa: PLC0415

    body: dict[str, object] = {"armed": code == 0, "result_code": code, "attempts": attempts}
    if code == 65:  # the cause of a refusal that needs a hand, so the split by cause is measurable
        body.update(refusal or {"reason": LAND_UNATTRIBUTED})
    refusal.clear()
    agents.field("field_landed", body)
    return code


def _rescue_prefix(branch: str) -> str:
    return f"lane/{branch.replace('/', '-')}/"


def tag_rescue(branch: str, git: Callable[..., str]) -> str:
    """Tag the tip by name before the rebase, and return the tag (3.25.0, the shape's own closer, second sighting).

    A rebase moves HEAD first; if the push is then refused — branch protection, a missing permission, a
    gate — the commit is reachable only from the reflog, while the branch reports ahead=0 and a clean tree.
    A named tag survives that, so recovery is `git reset --hard <tag>` instead of reading reflog by hand."""
    tag = _rescue_prefix(branch) + git("rev-parse", "--short", "HEAD")
    git("tag", "-f", tag)
    return tag


def close_landing(branch: str, verdict: str, git: Callable[..., str]) -> int:
    """Report the verdict and its exit code; only a merged lane gives up its rescue tags.

    MEASURED at 3.62.0: 12 tags stood from lanes already landed, 5 from one lane, because a retry after
    a rebase names a new tip. Nothing removed them, and every one read as work left to review."""
    print(f"{branch}: {verdict}")
    if verdict == "merged":
        for tag in git("tag", "--list", f"{_rescue_prefix(branch)}*").split():
            git("tag", "-d", tag)
        return 0
    return 0 if verdict.startswith(("armed", "queued")) else 1


def merged_head(
    branch: str, base: str, git: Callable[..., str], gh: Callable[..., subprocess.CompletedProcess[str]]
) -> bool:
    """Accept an immediate merge only when the forge names this exact head and base."""
    head = git("rev-parse", branch)
    done = gh("pr", "list", "--head", branch, "--state", "merged", "--json", "headRefOid,baseRefName")
    if done.returncode != 0 or not head:
        return False
    try:
        return any(row.get("headRefOid") == head and row.get("baseRefName") == base for row in json.loads(done.stdout))
    except (ValueError, TypeError, AttributeError):
        return False


def replay_local_ci(tree: Path, sha: str) -> bool:
    """True only when the complete contract passed on one commit, in a clean worktree of it. Posts nothing."""
    import tempfile

    with tempfile.TemporaryDirectory() as parent:
        clean = Path(parent) / "ci"
        subprocess.run(["git", "worktree", "add", "-q", "--detach", str(clean), sha], cwd=tree, check=True, timeout=600)
        try:
            env = {**os.environ, "CI_LOCAL_JOBS": ""}
            try:
                result = subprocess.run(
                    [str(clean / ".github" / "ci-local.sh")], cwd=clean, env=env, check=False, timeout=7200
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                print(f"land: local-ci NOT RUN or incomplete: {exc}")
                return False
            if result.returncode:
                print(f"land: local-ci did not pass on {sha[:12]} (exit {result.returncode})")
            return result.returncode == 0
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(clean)], cwd=tree, check=False, timeout=600)


def replay_once(tree: Path, head: str, git: Callable[..., str], cache: tuple, replay: Callable) -> bool:
    """The full replay of `head`, remembered by TREE like a clean-checkout pass (3.50.0 cached the gates,
    not this): a push refused after a green 574s replay re-ran the whole matrix on the same tree at the
    retry. The tree holds ci-local.sh and all it runs, so a changed contract is a changed key; only a PASS
    is kept, and an unrecorded pass costs one re-run, never a verdict. `cache` is (key_of, passed, record)."""
    key_of, passed, record = cache
    tree_id = git("rev-parse", f"{head}^{{tree}}")
    key = key_of(tree_id, [(["<full-replay>", ".github/ci-local.sh"], ".")], tree) if tree_id else ""
    if key and passed(key):
        print(f"  ok   full replay of tree {tree_id[:12]} already passed — not re-run")
        return True
    if not replay(tree, head):
        return False
    try:
        if key:
            record(key)
    except OSError:
        pass
    return True


def post_local_ci(branch: str, tree: Path, git: Callable[..., str], replayed: str = "") -> bool:
    """Post success only for a complete replay of the exact pushed atlas commit; `replayed` is one already run."""
    sha = git("rev-parse", "HEAD")
    if not sha or git("rev-parse", f"origin/{branch}") != sha:
        print("land: pushed branch does not match HEAD — local-ci NOT RUN")
        return False
    endpoint = f"repos/{{owner}}/{{repo}}/statuses/{sha}"

    def status(state: str) -> bool:
        result = subprocess.run(
            ["gh", "api", "-X", "POST", endpoint, "-f", f"state={state}", "-f", "context=local-ci"],
            cwd=tree,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
        if result.returncode:
            print(f"land: local-ci status post failed: {result.stderr.strip()[:300]}")
        return result.returncode == 0

    if not status("pending") or (sha != replayed and not replay_local_ci(tree, sha)):
        return False
    if git("rev-parse", "HEAD") != sha:
        print(f"land: HEAD moved off {sha[:12]} during local-ci")
        return False
    return status("success")


def _own_hook() -> Path | None:
    """The pre-push hook when it is this tool's to touch: a tracked core.hooksPath is this repository's code."""

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True, timeout=30).stdout.strip()

    if git("config", "--default", "", "core.hooksPath"):
        print(
            "ci-local.sh: core.hooksPath is set; add '.github/ci-local.sh fast' to that hook by hand", file=sys.stderr
        )
        return None
    hook = Path(git("rev-parse", "--git-path", "hooks")) / "pre-push"
    if hook.exists() and HOOK_MARK not in text_of(hook, errors="replace"):
        print(f"ci-local.sh: {hook} exists and is not ours; leaving it alone", file=sys.stderr)
        return None
    return hook


def install_hook() -> int:
    if not (hook := _own_hook()):
        return 1
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(
        f'#!/bin/sh\n{HOOK_MARK}\nexec "$(git rev-parse --show-toplevel)/.github/ci-local.sh" fast\n', "utf-8"
    )
    hook.chmod(0o755)
    print(f"ci-local.sh: installed {hook} (runs the fast job before every push; skip once with --no-verify)")
    return 0


def uninstall_hook() -> int:
    if not (hook := _own_hook()):
        return 1
    hook.unlink(missing_ok=True)
    print(f"ci-local.sh: removed {hook}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="headron ci", description="run the jobs scripts/cipipeline.py declares")
    parser.add_argument("jobs", nargs="*", help="default: $CI_LOCAL_JOBS, else the CONTRACT jobs (or --pipeline's)")
    parser.add_argument("--pipeline", default="", help="every job of one pipeline: atlas, polyglot, fuzz")
    parser.add_argument("--declared", default=PIPELINE, help="the declaration file, relative to the tree")
    parser.add_argument("--unit", help="one unit alone, in place: how a fanned-out child runs")
    parser.add_argument("--runner-temp", help="the scratch every unit of this run shares, artifacts included")
    parser.add_argument("--plan", action="store_true", help="print the units a run would start, in order; run nothing")
    parser.add_argument("--install-hook", action="store_true", help="OPT-IN: a pre-push hook that runs `fast`")
    parser.add_argument("--uninstall-hook", action="store_true", help="remove that hook, never one this did not write")
    args = parser.parse_args(argv)
    if args.install_hook:
        return install_hook()
    if args.uninstall_hook:
        return uninstall_hook()
    declared = load(args.declared)
    jobs, contract = tuple(declared.JOBS), tuple(declared.CONTRACT)
    if found := cipipeline.problems(jobs):
        print("\n".join(f"ci: {problem}" for problem in found))
        return 1
    alone = None
    if args.unit:
        if args.jobs or args.pipeline:
            parser.error("--unit runs one unit alone; name no jobs with it")
        alone = next((job for job in jobs if args.unit in job.units()), None)
        if alone is None:
            units = ", ".join(unit for job in jobs for unit in job.units())
            print(f"ci: no unit {args.unit!r}; declared: {units}")
            return 1
        names: list[str] = [alone.name]
    else:
        names = args.jobs or os.environ.get("CI_LOCAL_JOBS", "").split()
    chosen = cipipeline.selected(names, args.pipeline, jobs, contract)
    if args.plan:
        print(args.unit or " ".join(micrograph.order(cipipeline.nodes(chosen))))
        return 0
    if not args.runner_temp:
        parser.error("--runner-temp is required to run")
    temp = Path(args.runner_temp)
    if alone is not None:
        answer = run_unit(
            alone,
            args.unit,
            temp=temp,
            artifacts=Path(os.environ.get("HEADRON_CI_ARTIFACTS") or temp / ".artifacts"),
            timeout_s=alone.budget_s,
        )
        print(micrograph.summary([(args.unit, answer)]))
        return verdict([answer])
    whole = not names and not args.pipeline
    head = _committed_head() if whole else None
    return run_graph(chosen, temp, head=head, width=_width())


if __name__ == "__main__":
    with gaterunner.stop_children_on_sigterm():  # a cancelled job stops its units' sessions, not orphans them
        sys.exit(main())
