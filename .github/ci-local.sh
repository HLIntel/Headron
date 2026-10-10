#!/bin/bash
# ci-local gate: `~/.claude/bin/ci-local` runs this on the Mac instead of replaying every workflow with act.
# WHY: under act every run posted local-ci=failure on code that never ran — act's image has no Go
# (`go: command not found` in "Fuzz the bounded pool", so ruff and the type check never ran),
# cflite-pr needs a real pull_request payload and dependency-review a repo-token.
# ONE CI, NOT TWO: this hand-copies no command. It replays the `run:` steps of atlas-ci.yml's
# `contract` job in order, so a step added there runs here too. `uses:` steps are the runner's
# toolchain setup; on the Mac that toolchain is already installed. A step whose command is not on
# PATH is reported SKIP with the reason, never PASS, and the exit code ignores it.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec </dev/null
# THE TREE UNDER TEST, NOT THE ONE THAT LAUNCHED IT: `heavy` runs this through `thea slot`, which
# exported THEA_ROOT as the main checkout, and every step then checked main instead of this branch.
export THEA_ROOT="$PWD"
unset CODE_DEVELOPMENT_ROOT
# A throwaway virtualenv, as GitHub's runner is: the install step adds hash-locked deps to a clean
# Python, never to the Mac's own (PIP_REQUIRE_VIRTUALENV refuses that anyway).
runner=$(command -v python3) # reads the workflow before the install step fills the venv
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
python3 -m venv "$work/venv"
export VIRTUAL_ENV="$work/venv" PATH="$work/venv/bin:$PATH"
"$runner" - "${@:-contract}" <<'PY'
import os, shlex, shutil, subprocess, sys, time
import yaml

WORKFLOW = ".github/workflows/atlas-ci.yml"
jobs = yaml.safe_load(open(WORKFLOW, encoding="utf-8"))["jobs"]
failed, skipped = [], []
for job in sys.argv[1:]:
    for step in jobs[job]["steps"]:
        if "run" not in step:
            continue
        name, script = step.get("name", step["run"]), step["run"]
        first = shlex.split(script.strip().splitlines()[0])[0]
        if first not in ("for", "if", "test") and shutil.which(first) is None:
            print(f"SKIP {job}: {name} — `{first}` is not on PATH", flush=True)
            skipped.append(name)
            continue
        print(f"::: {job}: {name}", flush=True)
        start = time.monotonic()
        rc = subprocess.run(["bash", "-eo", "pipefail", "-c", script],
                            cwd=step.get("working-directory", "."), env={**os.environ, "CI": "true"}).returncode
        verdict = "PASS" if rc == 0 else f"FAIL rc={rc}"
        print(f"{verdict} {job}: {name} ({time.monotonic() - start:.0f}s)", flush=True)
        if rc:
            failed.append(name)
print(f"ci-local.sh: {len(failed)} failed, {len(skipped)} skipped"
      + (f" — failed: {'; '.join(failed)}" if failed else "")
      + (f" — skipped: {'; '.join(skipped)}" if skipped else ""))
sys.exit(1 if failed else 0)
PY
