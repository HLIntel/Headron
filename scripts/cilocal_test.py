#!/usr/bin/env python3
"""Planted workflows through cilocal's public CLI: each translator is observed by what a real step saw."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from seats_test import _case

ROOT = Path(__file__).resolve().parents[1]

WORKFLOW = """
jobs:
  up:
    strategy:
      matrix:
        k: [a, b]
    env:
      JOB: job-${{ matrix.k }}
    steps:
      - uses: actions/checkout@v9
        with:
          token: ${{ secrets.NEVER_READ }}
      - name: see the matrix
        env:
          K: ${{ matrix.k }}
        run: echo "$JOB $K ${{ matrix.k }}" >> "$RUNNER_TEMP/seen" && echo "$K" > "${{ runner.temp }}/edge-$K.txt"
      - name: share it
        uses: actions/upload-artifact@v9
        with:
          name: edge-${{ matrix.k }}
          path: ${{ runner.temp }}/edge-${{ matrix.k }}.txt
          if-no-files-found: error
  down:
    needs: [up]
    steps:
      - uses: actions/download-artifact@v9
        with:
          pattern: edge-*
          path: ${{ runner.temp }}/joined
          merge-multiple: true
      - name: join
        run: cat "$RUNNER_TEMP/joined/edge-a.txt" "$RUNNER_TEMP/joined/edge-b.txt" > "$RUNNER_TEMP/union"
  gates:
    steps:
      - name: unknown
        run: echo "${{ github.sha }}" > "$RUNNER_TEMP/unknown"
      - name: odd condition
        if: github.event_name == 'push'
        run: touch "$RUNNER_TEMP/odd"
      - name: root install
        run: |
          curl --version > /dev/null
          sudo install -m 0755 gitleaks /usr/local/bin/gitleaks
      - name: breaks
        run: exit 3
      - name: after a failure
        run: touch "$RUNNER_TEMP/after"
      - name: cleanup
        if: ${{ always() }}
        run: touch "$RUNNER_TEMP/always"
  contract:
    needs: [down, up]
    steps:
      - run: "true"
"""


def run(module) -> None:
    with tempfile.TemporaryDirectory(prefix="headron-cilocal-") as directory:
        base = Path(directory)
        workflow = base / "ci.yml"
        workflow.write_text(textwrap.dedent(WORKFLOW), encoding="utf-8")

        def call(*argv: str, env: dict[str, str] | None = None, temp: str = "rt") -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "cilocal.py"),
                    "--workflow",
                    str(workflow),
                    "--runner-temp",
                    str(base / temp),
                    *argv,
                ],
                cwd=base,
                env={**os.environ, **(env or {})},
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )

        plan = call("--plan", env={"CI_LOCAL_JOBS": ""})
        _case(
            module,
            "with no job named, the plan is the contract job's needs, each after its own",
            "a hand-kept job list that drops a job the required check waits on",
            plan.returncode == 0 and plan.stdout.split() == ["up", "down"],
        )
        picked = call("--plan", env={"CI_LOCAL_JOBS": "down"})
        _case(
            module,
            "CI_LOCAL_JOBS picks the jobs, as ~/.claude/bin/ci-local -j exports it",
            "a -j subset that silently runs the full default set",
            picked.stdout.split() == ["down"],
        )

        joined = call("up", "down")
        rt = base / "rt"
        seen = (rt / "seen").read_text(encoding="utf-8").split("\n") if (rt / "seen").exists() else []
        _case(
            module,
            "a matrix runs once per value with job env, step env and the run text all translated",
            "env: blocks ignored, or a raw ${{ matrix }} handed to bash as a bad substitution",
            joined.returncode == 0 and seen[:2] == ["job-a a a", "job-b b b"],
        )
        _case(
            module,
            "an upload and a download join the shards through RUNNER_TEMP",
            "edge-coverage never replayed, so a local green is not the required check's green",
            (rt / "union").read_text(encoding="utf-8") == "a\nb\n" if (rt / "union").exists() else False,
        )
        _case(
            module,
            "a toolchain uses: step is passed over, even with an expression in with:",
            "a checkout reported SKIP for its token, burying the skips that matter",
            "secrets.NEVER_READ" not in joined.stdout,
        )

        gates = call("gates", temp="gt")
        gt = base / "gt"
        _case(
            module,
            "an expression nothing answers is SKIP with its text, never PASS and never run",
            "a step run with ${{ github.sha }} left raw",
            "SKIP gates: unknown — unresolved ${{ github.sha }}" in gates.stdout and not (gt / "unknown").exists(),
        )
        _case(
            module,
            "an untranslated if: is SKIP with the condition, not run",
            "a condition dropped, so a push-only step runs on every replay",
            "the condition \"github.event_name == 'push'\" is not translated" in gates.stdout
            and not (gt / "odd").exists(),
        )
        _case(
            module,
            "a step that needs sudo is SKIP: root installs are runner-only, never a password prompt FAIL",
            "the pinned scanner install failing locally on sudo and cascading success() skips over the job",
            "SKIP gates: root install — needs sudo" in gates.stdout,
        )
        _case(
            module,
            "after a failure, success() steps are skipped, always() steps run, and the exit is 1",
            "every step replayed after a failure as if if: did not exist",
            gates.returncode == 1
            and not (gt / "after").exists()
            and (gt / "always").exists()
            and "ci-local.sh: 1 failed" in gates.stdout,
        )
