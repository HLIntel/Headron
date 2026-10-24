#!/usr/bin/env python3
"""Replay atlas-ci.yml's contract jobs on this machine, translating the GitHub expressions they use.

ONE CI, NOT TWO: no command is copied. Each `run:` step runs as written once the few runner-only constructs
the contract jobs lean on are translated: `${{ matrix.<k> }}` and `${{ runner.temp }}`, step and job `env:`,
`if: success() | always() | failure()`, a single-level `strategy.matrix`, and the upload/download-artifact pair
the edge-coverage job joins its shards through. Anything else is SKIP with its reason: never a PASS, and never
the bash `bad substitution` FAIL a raw `${{ }}` produced. Other `uses:` steps are runner toolchain setup that
this machine already has, so they are passed over.
"""

from __future__ import annotations

import argparse
import fnmatch
import itertools
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from atlascore import strict_yaml

WORKFLOW = ".github/workflows/atlas-ci.yml"
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
SUDO = re.compile(r"(^|[\s;&|(])sudo\s", re.MULTILINE)
UPLOAD, DOWNLOAD = "actions/upload-artifact", "actions/download-artifact"
# bash's own builtins and keywords (exit, cd, for, if, ...): never on PATH, always runnable. Asked of bash, not hand-listed.
SHELL_WORDS = frozenset(
    subprocess.run(["bash", "-c", "compgen -bk"], capture_output=True, text=True, check=True, timeout=10).stdout.split()
)


def _needs(job: dict[str, Any]) -> list[str]:
    needs = job.get("needs") or []
    return [needs] if isinstance(needs, str) else list(needs)


def contract_jobs(jobs: dict[str, Any]) -> list[str]:
    """The jobs the required `contract` job waits on, each after its own needs: read, never hand-listed."""
    wanted = set(_needs(jobs["contract"]))
    order: list[str] = []

    def visit(name: str) -> None:
        if name in order:
            return
        for need in _needs(jobs[name]):
            if need in wanted:
                visit(need)
        order.append(name)

    for name in jobs:
        if name in wanted:
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
    jobs = strict_yaml(workflow.read_text(encoding="utf-8"), str(workflow))["jobs"]
    store = runner_temp / ".artifacts"
    runner_temp.mkdir(parents=True, exist_ok=True)
    failed: list[str] = []
    skipped: list[str] = []

    def skip(label: str, name: str, why: str) -> None:
        print(f"SKIP {label}: {name} — {why}", flush=True)
        skipped.append(name)

    for job_name in names:
        job = jobs[job_name]
        rows = matrix_rows(job)
        if rows is None:
            skip(job_name, "(whole job)", "a matrix with include/exclude or an expression is not translated")
            continue
        for row in rows:
            label = job_name + "".join(f"[{k}={v}]" for k, v in row.items())
            context = {f"matrix.{k}": v for k, v in row.items()} | {"runner.temp": str(runner_temp)}
            job_failed = False
            for step in job.get("steps") or []:
                name = step.get("name") or step.get("run") or step.get("uses")
                if "uses" in step and str(step["uses"]).split("@")[0] not in (UPLOAD, DOWNLOAD):
                    continue  # runner toolchain setup: this machine already has it
                run = condition(step.get("if"), job_failed)
                if run is None:
                    skip(label, name, f"the condition {step['if']!r} is not translated")
                    continue
                if not run:
                    skip(label, name, "its condition is false: an earlier step failed")
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
    return 1 if failed else 0


def _translated(values: dict[str, Any], context: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    out: dict[str, str] = {}
    unresolved: list[str] = []
    for key, value in values.items():
        out[str(key)], missing = translate(str(value), context)
        unresolved += missing
    return out, unresolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cilocal", description="replay atlas-ci.yml's contract jobs on this machine")
    parser.add_argument("jobs", nargs="*", help="default: $CI_LOCAL_JOBS, else every job the contract job needs")
    parser.add_argument("--workflow", default=WORKFLOW)
    parser.add_argument("--runner-temp", required=True, help="the RUNNER_TEMP every job shares, artifacts included")
    parser.add_argument("--plan", action="store_true", help="print the jobs a run would replay, run nothing")
    args = parser.parse_args(argv)
    workflow = Path(args.workflow)
    names = args.jobs or os.environ.get("CI_LOCAL_JOBS", "").split()
    if not names:
        names = contract_jobs(strict_yaml(workflow.read_text(encoding="utf-8"), str(workflow))["jobs"])
    if args.plan:
        print(" ".join(names))
        return 0
    return replay(workflow, names, Path(args.runner_temp))


if __name__ == "__main__":
    sys.exit(main())
