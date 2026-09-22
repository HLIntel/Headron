#!/usr/bin/env bash
set -euo pipefail

branch="feat/${1:?feature-name}"
path="../Code-Development-wt/${1}"

git worktree add -b "$branch" "$path" main
git worktree list --porcelain