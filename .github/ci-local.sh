#!/bin/bash
# THE ONE CI. `~/.claude/bin/ci-local` runs this on the Mac and posts the `local-ci` commit status the
# default-branch ruleset requires; no GitHub-hosted runner checks a pull request.
# It hand-copies no command: it replays the `run:` steps of ci/atlas-ci.yml's contract jobs in needs
# order (scripts/cilocal.py), so a step added there runs here too. `uses:` steps are the runner's
# toolchain setup; on the Mac that toolchain is already installed. A step whose command is not on
# PATH is reported SKIP with the reason and makes the replay incomplete and unsuccessful.
#
# USAGE
#   .github/ci-local.sh                  every job the required `Contract` check waits on (read from the workflow)
#   .github/ci-local.sh fast             the cheap job only (lint, format, type check, workflows, contract check)
#   .github/ci-local.sh --workflow ci/polyglot.yml examples   the installed-toolchain example packs (weekly)
#   .github/ci-local.sh --workflow ci/fuzz-nightly.yml fuzz   the open-ended atheris campaign (nightly)
#   .github/ci-local.sh --install-hook   OPT-IN: a pre-push hook that runs `fast`; --uninstall-hook removes it
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
# A hook runs this with git's own variables set. A step's fixture repository would obey them over -C,
# and a `git init` there rewrites this repository's core.bare and user.*; the replay finds the tree by cwd.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_PREFIX
exec </dev/null
# THE TREE UNDER TEST, NOT THE ONE THAT LAUNCHED IT: `heavy` runs this through `headron slot`, which
# exported HEADRON_ROOT as the main checkout, and every step then checked main instead of this branch.
export HEADRON_ROOT="$PWD"
unset CODE_DEVELOPMENT_ROOT
# A throwaway virtualenv, as GitHub's runner is: the install step adds hash-locked deps to a clean
# Python, never to the Mac's own (PIP_REQUIRE_VIRTUALENV refuses that anyway).
# The REAL interpreter, never the pyenv shim: `pyenv exec` puts its own bin ahead of the venv's, so
# every step ran the Mac's Python and pip refused the install. It reads the workflow (PyYAML) before
# the install step fills the venv.
if [ -x "$PWD/.venv/bin/python" ]; then
    runner="$PWD/.venv/bin/python"
elif command -v uv >/dev/null 2>&1; then
    runner="$(uv run --frozen --extra crosscheck python -c 'import sys; print(sys.executable)' 2>/dev/null || python3 -c 'import sys; print(sys.executable)')"
else
    runner=$(python3 -c 'import sys; print(sys.executable)')
fi
case "${1:-}" in
--install-hook | --uninstall-hook) exec "$runner" scripts/cilocal.py "$1" ;;
esac
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
"$runner" -m venv "$work/venv" || python3 -m venv "$work/venv"
export VIRTUAL_ENV="$work/venv" PATH="$work/venv/bin:$PATH"
# THE REPLAY: scripts/cilocal.py translates the runner-only constructs (matrix, env, if, runner.temp,
# artifacts) and runs each `run:` step as written. No job list here: it defaults to $CI_LOCAL_JOBS (what
# ~/.claude/bin/ci-local -j picked), else every job the required `contract` job needs, edge-coverage included.
"$runner" scripts/cilocal.py --runner-temp "$work/runner" "$@"
