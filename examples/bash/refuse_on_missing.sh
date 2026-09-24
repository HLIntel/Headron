#!/usr/bin/env bash
# A script that REFUSES on a missing input instead of defaulting to one.
#
# The defect this kills: `${VAR:-default}` on a value that has no safe default. The run then
# succeeds against the wrong target and prints what a correct run prints.
#
# Verify: bash examples/bash/refuse_on_missing.sh   (exit 0, and the failure paths are asserted)
set -euo pipefail

target() {
    # THE COLON IS THE WHOLE DIFFERENCE, and this example was WRONG without it:
    #   ${VAR?msg}   refuses only when VAR is UNSET  — an empty value passes straight through
    #   ${VAR:?msg}  refuses when it is unset OR empty
    #   ${VAR:-x}    invents a value, which is how a run succeeds against the wrong target
    # The first version of this file used the second form, accepted DEPLOY_TARGET= and printed
    # "deploying to " — demonstrating the defect it claims to kill. It was caught by RUNNING it.
    printf 'deploying to %s\n' "${DEPLOY_TARGET:?DEPLOY_TARGET is not set, and there is no safe default}"
}

main() {
    # EACH REFUSAL IS TESTED IN A SUBSHELL, and this file was wrong without them: a failed
    # `${VAR:?}` expansion is fatal to the SHELL, not just to the function, so `if target; then`
    # killed the whole script instead of reporting a handled refusal. The subshell is the boundary.
    if ( DEPLOY_TARGET= target ) 2>/dev/null; then
        echo "FAIL: an empty target was accepted" >&2
        return 1
    fi
    if ( unset DEPLOY_TARGET; target ) 2>/dev/null; then
        echo "FAIL: a missing target was accepted" >&2
        return 1
    fi
    DEPLOY_TARGET=staging target >/dev/null
    echo "refuse_on_missing: 3 assertions held — empty refused, unset refused, declared accepted"
}

main "$@"
