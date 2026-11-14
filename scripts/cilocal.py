#!/usr/bin/env python3
"""Replay atlas-ci.yml's contract jobs on this machine, translating the GitHub expressions they use.

ONE CI, NOT TWO: no command is copied. Each `run:` step runs as written once the few runner-only constructs
the contract jobs lean on are translated: `${{ matrix.<k> }}` and `${{ runner.temp }}`, step and job `env:`,
`if: success() | always() | failure()`, a single-level `strategy.matrix`, and the upload/download-artifact pair
the edge-coverage job joins its shards through. Anything else is SKIP with its reason: never a PASS, and never
the bash `bad substitution` FAIL a raw `${{ }}` produced. Untranslated setup actions make the replay incomplete.
"""

from __future__ import annotations

import argparse
import fnmatch
import itertools
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from atlascore import strict_yaml, text_of
from resilience import wait_until
from slot import spare_cores

WORKFLOW = "ci/atlas-ci.yml"
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
SUDO = re.compile(r"(^|[\s;&|(])sudo\s", re.MULTILINE)
UPLOAD, DOWNLOAD = "actions/upload-artifact", "actions/download-artifact"
HOOK_MARK = "# installed by .github/ci-local.sh --install-hook"
WIDTH = 3  # units at once: the contract DAG never has more ready, and each is one process beside a bounded example pool
# bash's own builtins and keywords (exit, cd, for, if, ...): never on PATH, always runnable. Asked of bash, not hand-listed.
SHELL_WORDS = frozenset(
    subprocess.run(["bash", "-c", "compgen -bk"], capture_output=True, text=True, check=True, timeout=10).stdout.split()
)


def _needs(job: dict[str, Any]) -> list[str]:
    needs = job.get("needs") or []
    return [needs] if isinstance(needs, str) else list(needs)


def contract_jobs(jobs: dict[str, Any]) -> list[str]:
    """The jobs the required `contract` job waits on, each after its own needs: read, never hand-listed."""
    order: list[str] = []
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in order:
            return
        if name in visiting:
            raise ValueError(f"cyclic job dependency: {name}")
        visiting.add(name)
        for need in _needs(jobs[name]):
            visit(need)
        visiting.remove(name)
        order.append(name)

    required = _needs(jobs["contract"])
    if not required:
        raise ValueError("contract has no required jobs")
    for name in required:
        visit(name)
    return order


def matrix_rows(job: dict[str, Any]) -> list[dict[str, str]] | None:
    """One row per combination of a plain list matrix; None for include/exclude or expression matrices."""
    matrix = (job.get("strategy") or {}).get("matrix")
    if not matrix:
        return [{}]
    if not isinstance(matrix, dict) or not all(isinstance(values, list) for values in matrix.values()):
        return None
    keys = list(matrix)
    return [dict(zip(keys, map(str, combo), strict=True)) for combo in itertools.product(*(matrix[k] for k in keys))]


def _label(job_name: str, row: dict[str, str]) -> str:
    return job_name + "".join(f"[{k}={v}]" for k, v in row.items())


def _selected(job: dict[str, Any], name: str) -> list[dict[str, str]] | None:
    """The rows `name` asks for: all of them for a bare job, one for a `job[k=v]` unit, none for an unknown row."""
    rows = matrix_rows(job)
    if rows is None or "[" not in name:
        return rows
    return [row for row in rows if _label(name.split("[")[0], row) == name]


def translate(text: str, context: dict[str, str]) -> tuple[str, list[str]]:
    """Substitute every expression the context answers; return the text and the expressions it could not."""
    unresolved: list[str] = []

    def one(match: re.Match[str]) -> str:
        if match.group(1) in context:
            return context[match.group(1)]
        unresolved.append(match.group(0))
        return match.group(0)

    return EXPRESSION.sub(one, text), unresolved


def condition(expression: object, failed: bool) -> bool | None:
    """GitHub's default is success(); the status functions are answered, any other condition is None (SKIP)."""
    text = str(expression or "success()").strip()
    match = EXPRESSION.fullmatch(text)
    text = match.group(1) if match else text
    return {"success()": not failed, "always()": True, "failure()": failed}.get(text)


def minutes(step: dict[str, Any], job: dict[str, Any]) -> float:
    """The runner's own bound: the step's timeout-minutes, else the job's, else GitHub's default of 360."""
    return float(step.get("timeout-minutes") or job.get("timeout-minutes") or 360)


def _setup(action: str, given: dict[str, str]) -> str | None:
    """Accept only locally verifiable setup; None means the narrow adapter matched."""
    if action == "actions/checkout":
        unsupported = set(given) - {"persist-credentials", "fetch-depth"}
        if unsupported or given.get("persist-credentials", "false").lower() != "false":
            return "checkout options are not translated"
        return None
    allowed = {
        "actions/setup-python": {"python-version", "check-latest", "cache", "cache-dependency-path"},
        "actions/setup-go": {"go-version-file", "cache"},
        "astral-sh/setup-uv": {"version", "enable-cache", "cache-dependency-glob"},
    }
    if action not in allowed or set(given) - allowed[action]:
        return "action is not translated"
    if action == "actions/setup-python":
        if given.get("check-latest", "false").lower() != "false":
            return "check-latest is not translated"
        expected = given.get("python-version", "")
        command = ["python", "--version"]
    elif action == "actions/setup-go":
        try:
            content = text_of(Path(given["go-version-file"]))
            match = re.search(r"^go\s+(\d+\.\d+(?:\.\d+)?)\s*$", content, re.MULTILINE)
            expected = match.group(1) if match else ""
        except (KeyError, OSError):
            return "Go version file is unavailable"
        command = ["go", "version"]
    else:
        expected = given.get("version", "")
        command = ["uv", "--version"]
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", expected) or not shutil.which(command[0]):
        return "tool version is unpinned or unavailable"
    if action == "astral-sh/setup-uv" and not shutil.which("uvx"):
        return "uvx is unavailable"
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    actual = re.search(r"(?<!\d)(\d+\.\d+(?:\.\d+)?)", result.stdout)
    if result.returncode or not actual:
        return "tool version is unpinned or unavailable"
    if action == "actions/setup-go":
        try:
            actual_parts = [int(p) for p in actual.group(1).split(".")]
            expected_parts = [int(p) for p in expected.split(".")]
            if actual_parts < expected_parts:
                return f"host Go version {actual.group(1)} does not satisfy {expected}"
        except ValueError:
            return f"host tool version does not match {expected}"
    elif not (actual.group(1) == expected or actual.group(1).startswith(expected + ".")):
        return f"host tool version does not match {expected}"
    if action == "astral-sh/setup-uv":
        uvx = subprocess.run(["uvx", "--version"], capture_output=True, text=True, check=False, timeout=10)
        if uvx.returncode or not re.search(rf"\b{re.escape(actual.group(1))}\b", uvx.stdout):
            return "uv and uvx versions differ"
    return None


def _artifact(step: dict[str, Any], given: dict[str, str], store: Path) -> str | None:
    """Upload copies `path` into the local store under `name`; download copies matching artifacts to `path`."""
    uses = str(step["uses"]).split("@")[0]
    if uses == UPLOAD:
        source = Path(given["path"])
        if not source.exists():
            return None if given.get("if-no-files-found", "warn") != "error" else f"no file at {source}"
        target = store / given["name"]
        target.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target / source.name, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target / source.name)
        return None
    pattern = given.get("name") or given.get("pattern") or "*"
    found = sorted(path for path in store.glob("*") if fnmatch.fnmatch(path.name, pattern))
    if not found:
        return f"no artifact matches {pattern}"
    for artifact in found:
        merge = str(given.get("merge-multiple", "false")).lower() == "true" or "name" in given
        shutil.copytree(artifact, Path(given["path"]) / ("" if merge else artifact.name), dirs_exist_ok=True)
    return None


def replay(workflow: Path, names: list[str], runner_temp: Path) -> int:
    jobs = strict_yaml(text_of(workflow), str(workflow))["jobs"]
    store = Path(os.environ.get("HEADRON_CI_ARTIFACTS") or runner_temp / ".artifacts")
    runner_temp.mkdir(parents=True, exist_ok=True)
    failed: list[str] = []
    skipped: list[str] = []
    incomplete: list[str] = []

    def skip(label: str, name: str, why: str, *, expected: bool = False) -> None:
        print(f"SKIP {label}: {name} — {why}", flush=True)
        skipped.append(name)
        if not expected:
            incomplete.append(name)

    for job_name in names:
        job = jobs[job_name.split("[")[0]]
        rows = _selected(job, job_name)
        if rows is None:
            skip(job_name, "(whole job)", "a matrix with include/exclude or an expression is not translated")
            continue
        if not rows:
            skip(job_name, "(whole job)", "no matrix row has this label")
            continue
        for row in rows:
            label = _label(job_name.split("[")[0], row)
            context = {f"matrix.{k}": v for k, v in row.items()} | {"runner.temp": str(runner_temp)}
            job_failed = False
            for step in job.get("steps") or []:
                name = step.get("name") or step.get("run") or step.get("uses")
                run = condition(step.get("if"), job_failed)
                if run is None:
                    skip(label, name, f"the condition {step['if']!r} is not translated")
                    continue
                if not run:
                    skip(label, name, "its condition is false", expected=True)
                    continue
                env = {**(job.get("env") or {}), **(step.get("env") or {})}
                given = {**(step.get("with") or {})}
                env, env_open = _translated(env, context)
                given, with_open = _translated(given, context)
                script, run_open = translate(str(step.get("run", "")), context)
                if unresolved := env_open + with_open + run_open:
                    skip(label, name, f"unresolved {', '.join(sorted(set(unresolved)))}")
                    continue
                if "uses" in step:
                    action = str(step["uses"]).split("@")[0]
                    if action not in (UPLOAD, DOWNLOAD):
                        problem = "setup environment is not translated" if env else _setup(action, given)
                        if problem:
                            skip(label, name, problem)
                        else:
                            print(f"PASS {label}: {name} (local setup adapter)", flush=True)
                        continue
                    print(f"::: {label}: {name}", flush=True)
                    problem = _artifact(step, given, store)
                    print(f"{'PASS' if problem is None else 'FAIL ' + problem} {label}: {name}", flush=True)
                    if problem is not None:
                        failed.append(name)
                        job_failed = True
                    continue
                if SUDO.search(script):
                    skip(label, name, "needs sudo: a runner-only root install")
                    continue
                first = shlex.split(script.strip().splitlines()[0])[0]
                if first not in SHELL_WORDS and shutil.which(first) is None:
                    skip(label, name, f"`{first}` is not on PATH")
                    continue
                print(f"::: {label}: {name}", flush=True)
                start = time.monotonic()
                rc = subprocess.run(
                    ["bash", "-eo", "pipefail", "-c", script],
                    cwd=step.get("working-directory", "."),
                    env={**os.environ, **env, "CI": "true", "RUNNER_TEMP": str(runner_temp)},
                    check=False,
                    timeout=60 * minutes(step, job),
                ).returncode
                print(
                    f"{'PASS' if rc == 0 else f'FAIL rc={rc}'} {label}: {name} ({time.monotonic() - start:.0f}s)",
                    flush=True,
                )
                if rc:
                    failed.append(name)
                    job_failed = True
    print(
        f"ci-local.sh: {len(failed)} failed, {len(skipped)} skipped"
        + (f" — failed: {'; '.join(failed)}" if failed else "")
        + (f" — skipped: {'; '.join(skipped)}" if skipped else "")
    )
    return 1 if failed or incomplete else 0


def _translated(values: dict[str, Any], context: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    out: dict[str, str] = {}
    unresolved: list[str] = []
    for key, value in values.items():
        out[str(key)], missing = translate(str(value), context)
        unresolved += missing
    return out, unresolved


def units_of(jobs: dict[str, Any], names: list[str]) -> dict[str, list[str]]:
    """Every job or matrix row as one schedulable unit, with the units it waits on."""
    labels = {name: [_label(name, row) for row in matrix_rows(jobs[name]) or [{}]] for name in names}
    return {
        unit: [needed for need in _needs(jobs[name]) for needed in labels.get(need, [])]
        for name in names
        for unit in labels[name]
    }


def _width() -> int:
    raw = os.environ.get("CI_LOCAL_WORKERS", "")
    if raw and (not raw.isdigit() or int(raw) < 1):
        raise SystemExit(f"cilocal: CI_LOCAL_WORKERS={raw!r} is not a positive integer; refusing to guess a width")
    return int(raw or WIDTH)


def _committed_head() -> str | None:
    """HEAD when the tree IS HEAD. A dirty tree replays in place: a worktree of HEAD would pass without its edits."""
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=False, timeout=600)
    if status.returncode or status.stdout.strip():
        return None
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=600
    ).stdout.strip()


def _start_unit(unit: str, tree: Path, head: str, workflow: str, env: dict[str, str]) -> subprocess.Popen[bytes]:
    subprocess.run(["git", "worktree", "add", "-q", "--detach", str(tree), head], check=True, timeout=600)
    print(f"::: started {unit}", flush=True)
    with tree.with_suffix(".log").open("wb") as log:
        return subprocess.Popen(
            [str(tree / ".github" / "ci-local.sh"), "--workflow", workflow, unit],
            cwd=tree,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def _finish_unit(unit: str, tree: Path, rc: int, began: float) -> None:
    """One unit's whole log at once, so two units' lines never interleave; then its worktree goes."""
    print(text_of(tree.with_suffix(".log"), errors="replace"), end="")
    print(f"{'PASS' if rc == 0 else f'FAIL rc={rc}'} unit {unit} ({time.monotonic() - began:.0f}s)", flush=True)
    subprocess.run(["git", "worktree", "remove", "--force", str(tree)], check=True, timeout=600)


def fan_out(workflow: str, units: dict[str, list[str]], head: str, runner_temp: Path, width: int) -> int:
    """Replay each unit in its own detached worktree, when its needs passed: each plants defects in its own tree.

    Each child is `.github/ci-local.sh <unit>`, the same replay and the same verdict as a serial run: its own
    throwaway virtualenv, HEADRON_ROOT and RUNNER_TEMP, and only the artifact store shared. A unit past the first
    starts only while slot.spare_cores() says so: a loaded machine falls back to one at a time. Width 1 never gets
    here; it replays in place.
    """
    trees = runner_temp / "units"
    trees.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "HEADRON_CI_ARTIFACTS": str(runner_temp / ".artifacts")}
    env.pop("VIRTUAL_ENV", None)
    waiting, verdicts = list(units), {}
    running: dict[str, tuple[subprocess.Popen[bytes], Path, float]] = {}
    began = time.monotonic()
    try:
        while waiting or running:
            for unit in [u for u in waiting if any(verdicts.get(need, 0) for need in units[u])]:
                print(f"SKIP unit {unit} — a unit it needs did not pass", flush=True)
                verdicts[unit] = 1
                waiting.remove(unit)
            for unit in [u for u in waiting if all(verdicts.get(need) == 0 for need in units[u])]:
                if len(running) >= width or (running and not spare_cores()):
                    break
                tree = trees / str(len(verdicts) + len(running))
                running[unit] = (_start_unit(unit, tree, head, workflow, env), tree, time.monotonic())
                waiting.remove(unit)
            for unit, (process, tree, start) in list(running.items()):
                if (rc := process.poll()) is not None:
                    del running[unit]
                    verdicts[unit] = rc
                    _finish_unit(unit, tree, rc, start)
            # A bounded wait, not until an exit: a loaded machine can clear while every unit is still running.
            processes = [process for process, _, _ in running.values()]
            if processes:
                wait_until(lambda: any(p.poll() is not None for p in processes), timeout=2.0, interval=0.2)
    finally:
        for process, _, _ in running.values():
            os.killpg(process.pid, signal.SIGTERM)
    failed = [unit for unit, rc in verdicts.items() if rc]
    print(
        f"ci-local.sh: {len(failed)} failed, 0 skipped — {len(units)} units, width {width}, "
        f"{time.monotonic() - began:.0f}s" + (f" — failed: {'; '.join(failed)}" if failed else "")
    )
    return 1 if failed else 0


# WHY A LANDING NEEDS A HAND, declared (field ledger 2026-11: 47 of 182 landings exited 65, cause unrecorded,
# so no fix could be ranked). Every 65 in branchstate._land_once names one; one that names none is "unattributed".
LAND_REFUSALS = ("uninspectable", "diverged", "rebase", "merge", "gate", "replay", "post_ci")
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
        body.update(refusal or {"reason": "unattributed"})
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
    parser = argparse.ArgumentParser(prog="cilocal", description="replay atlas-ci.yml's contract jobs on this machine")
    parser.add_argument("jobs", nargs="*", help="default: $CI_LOCAL_JOBS, else every job the contract job needs")
    parser.add_argument("--workflow", default=WORKFLOW)
    parser.add_argument("--runner-temp", help="the RUNNER_TEMP every job shares, artifacts included")
    parser.add_argument("--plan", action="store_true", help="print the jobs a run would replay, run nothing")
    parser.add_argument("--install-hook", action="store_true", help="OPT-IN: a pre-push hook that runs `fast`")
    parser.add_argument("--uninstall-hook", action="store_true", help="remove that hook, never one this did not write")
    args = parser.parse_args(argv)
    if args.install_hook:
        return install_hook()
    if args.uninstall_hook:
        return uninstall_hook()
    if not args.runner_temp:
        parser.error("--runner-temp is required to replay")
    workflow = Path(args.workflow)
    jobs = strict_yaml(text_of(workflow), str(workflow))["jobs"]
    named = args.jobs or os.environ.get("CI_LOCAL_JOBS", "").split()
    names = named or contract_jobs(jobs)
    if args.plan:
        print(" ".join(names))
        return 0
    if not named and (width := _width()) > 1 and (head := _committed_head()):
        return fan_out(args.workflow, units_of(jobs, names), head, Path(args.runner_temp), width)
    return replay(workflow, names, Path(args.runner_temp))


if __name__ == "__main__":
    sys.exit(main())
