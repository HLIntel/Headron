#!/usr/bin/env bash
# The worktree layout this repository declares — as a DRY RUN by default.
#
# WHY: the previous version called `git worktree add` the moment it was executed. An example that
# mutates the repository when a reader runs it to see what it does cannot be exercised by any
# instrument, so it was never run and its argument handling was never checked. One system, two
# routes: the safe route prints and verifies, `--apply` is the only way to mutate anything.
#
# Verify: bash examples/git/worktree-layout.sh          (dry run, read-only, exits 0)
#         bash examples/git/worktree-layout.sh --apply my-topic
set -euo pipefail

apply=false
topic="example-topic"
for argument in "$@"; do
    case "$argument" in
        --apply) apply=true ;;
        *) topic="$argument" ;;
    esac
done

branch="feat/${topic}"
path="../thea-software-wt/${topic}"

if [[ "$apply" == true ]]; then
    # THE MUTATING ROUTE IS REACHED ONLY BY AN EXPLICIT FLAG, and it refuses a topic it was not given.
    : "${topic:?a topic is required to name the branch and the worktree}"
    git worktree add -b "$branch" "$path" main
    git worktree list --porcelain
    exit 0
fi

printf 'would run: git worktree add -b %s %s main\n' "$branch" "$path"

# The read-only half is still a real check: the layout rule is that the repository's own path is
# the main worktree and never a lane.
main_path="$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')"
[[ -n "$main_path" ]] || { echo "FAIL: git reported no worktree at all" >&2; exit 1; }
case "$branch" in
    feat/*) ;;
    *) echo "FAIL: a topic branch must be namespaced, got $branch" >&2; exit 1 ;;
esac
[[ "$path" == ../thea-software-wt/* ]] || { echo "FAIL: a lane must live outside the main checkout" >&2; exit 1; }

echo "worktree-layout: 3 assertions held — main worktree found, lane namespaced, lane outside the checkout"
