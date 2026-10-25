#!/bin/bash
# ci-local gate: `~/.claude/bin/ci-local` runs this on the Mac instead of replaying every workflow with act.
# WHY: under act every run posted local-ci=failure on code that never ran — act's image has no Go
# (`go: command not found` in "Fuzz the bounded pool", so ruff and the type check never ran),
# cflite-pr needs a real pull_request payload and dependency-review a repo-token.
# ONE CI, NOT TWO: this hand-copies no command. It replays the `run:` steps of atlas-ci.yml's
# contract jobs in needs order (scripts/cilocal.py), so a step added there runs here too. `uses:` steps are the runner's
# toolchain setup; on the Mac that toolchain is already installed. A step whose command is not on
# PATH is reported SKIP with the reason, never PASS, and the exit code ignores it.
#
# USAGE
#   .github/ci-local.sh                  every job the required `Contract` check waits on (read from the workflow)
#   .github/ci-local.sh fast             the cheap job only (lint, format, type check, workflows, contract check)
#   .github/ci-local.sh --install-hook   OPT-IN: a pre-push hook that runs `fast`; --uninstall-hook removes it
# Nothing installs the hook for you. It goes in `git rev-parse --git-path hooks`, refuses a tracked
# core.hooksPath (that directory is this repository's code) and never replaces a hook it did not write.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
MARK="# installed by .github/ci-local.sh --install-hook"
case "${1:-}" in
--install-hook | --uninstall-hook)
    if [ -n "$(git config core.hooksPath || true)" ]; then
        echo "ci-local.sh: core.hooksPath is set; add '.github/ci-local.sh fast' to that hook by hand" >&2
        exit 1
    fi
    hook="$(git rev-parse --git-path hooks)/pre-push"
    if [ -e "$hook" ] && ! grep -qF "$MARK" "$hook"; then
        echo "ci-local.sh: $hook exists and is not ours; leaving it alone" >&2
        exit 1
    fi
    if [ "$1" = --uninstall-hook ]; then
        rm -f "$hook" && echo "ci-local.sh: removed $hook"
        exit 0
    fi
    mkdir -p "$(dirname "$hook")"
    printf '#!/bin/sh\n%s\nexec "$(git rev-parse --show-toplevel)/.github/ci-local.sh" fast\n' "$MARK" >"$hook"
    chmod +x "$hook"
    echo "ci-local.sh: installed $hook (runs the fast job before every push; skip once with --no-verify)"
    exit 0
    ;;
esac
exec </dev/null
# THE TREE UNDER TEST, NOT THE ONE THAT LAUNCHED IT: `heavy` runs this through `thea slot`, which
# exported THEA_ROOT as the main checkout, and every step then checked main instead of this branch.
export THEA_ROOT="$PWD"
unset CODE_DEVELOPMENT_ROOT
# A throwaway virtualenv, as GitHub's runner is: the install step adds hash-locked deps to a clean
# Python, never to the Mac's own (PIP_REQUIRE_VIRTUALENV refuses that anyway).
# The REAL interpreter, never the pyenv shim: `pyenv exec` puts its own bin ahead of the venv's, so
# every step ran the Mac's Python and pip refused the install. It reads the workflow (PyYAML) before
# the install step fills the venv.
runner=$(python3 -c 'import sys; print(sys.executable)')
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
python3 -m venv "$work/venv"
export VIRTUAL_ENV="$work/venv" PATH="$work/venv/bin:$PATH"
# THE REPLAY: scripts/cilocal.py translates the runner-only constructs (matrix, env, if, runner.temp,
# artifacts) and runs each `run:` step as written. No job list here: it defaults to $CI_LOCAL_JOBS (what
# ~/.claude/bin/ci-local -j picked), else every job the required `contract` job needs, edge-coverage included.
"$runner" scripts/cilocal.py --runner-temp "$work/runner" "$@"
