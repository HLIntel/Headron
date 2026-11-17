#!/bin/bash
# THE ONE CI, NATIVE. `headron ci` and `~/.claude/bin/ci-local` run this; `branchstate --land` runs it on a clean
# worktree of the commit it lands and posts the `local-ci` commit status the default-branch ruleset requires.
# No GitHub-hosted runner checks a pull request and no workflow file is translated: the jobs are Python
# (scripts/cipipeline.py), run as one graph of microprograms by scripts/cilocal.py. A step that cannot run here
# (a tool not on PATH, a hosted runner's credential) answers unknown with what to do, never a passing skip.
#
# USAGE
#   .github/ci-local.sh                  the CONTRACT jobs the `local-ci` status waits on (fast, mutation, edge-coverage, exercises)
#   .github/ci-local.sh fast             the named jobs only, in place (lint, format, type check, contract check)
#   .github/ci-local.sh --pipeline polyglot   every job of one pipeline: polyglot (the example packs), fuzz (atheris)
#   .github/ci-local.sh --plan           the units a run would start, in order; runs nothing
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
# every step ran the Mac's Python and pip refused the install. It loads the job declaration before
# the install step fills the venv.
if [ -x "$PWD/.venv/bin/python" ]; then
    runner="$PWD/.venv/bin/python"
elif command -v uv >/dev/null 2>&1; then
    runner="$(uv run --frozen --extra crosscheck python -c 'import sys; print(sys.executable)' 2>/dev/null || python3 -c 'import sys; print(sys.executable)')"
else
    runner=$(python3 -c 'import sys; print(sys.executable)')
fi
case "${1:-}" in
    --install-hook | --uninstall-hook | --plan) exec "$runner" scripts/cilocal.py "$@" ;;
    --workflow)
        echo "ci-local.sh: --workflow is gone; the jobs are scripts/cipipeline.py. Run \`ci-local.sh --pipeline polyglot\` or \`ci-local.sh fuzz\`." >&2
        exit 2
        ;;
esac
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
# uv makes the venv in under a second (stdlib venv: 4-15 s, MEASURED) and seeds pip for any step that calls it;
# with no uv, the stdlib venv, and the install steps answer unknown (scripts/cipipeline.py install).
if command -v uv >/dev/null 2>&1; then
    uv venv --quiet --seed --python "$runner" "$work/venv"
else
    "$runner" -m venv "$work/venv" || python3 -m venv "$work/venv"
fi
export VIRTUAL_ENV="$work/venv" PATH="$work/venv/bin:$PATH"
# THE RUN: scripts/cilocal.py runs the declared jobs through scripts/micrograph.py. No job list here: it defaults
# to $CI_LOCAL_JOBS (what ~/.claude/bin/ci-local -j picked), else the CONTRACT jobs, edge-coverage included.
# Not exec (the EXIT trap removes $work), so a TERM or INT to this shell is forwarded: killing only the shell
# would orphan cilocal and every unit under it, then delete the tree they run in.
"$runner" scripts/cilocal.py --runner-temp "$work/runner" "$@" &
child=$!
trap 'kill -TERM "$child" 2>/dev/null' TERM INT
wait "$child"
rc=$?
while kill -0 "$child" 2>/dev/null; do
    wait "$child"
    rc=$?
done
exit "$rc"
