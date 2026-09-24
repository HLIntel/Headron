# OpenCode adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to OpenCode — how the atlas is loaded
here, and the mistake this runtime makes.

## How it loads

`AGENTS.md`, generated. OpenCode runs in a terminal workspace, so the instruments are directly
available — there is no reason to describe the repository to it when it can ask:

```bash
python scripts/atlas.py route <path> --json
python scripts/atlas.py doctor                   # what this machine can actually run
python scripts/exrun.py                          # every example, run, with skips explained
```

## What it is routed for

`terminal_parallelism` and `deterministic_repo_edit`. Several sessions in several worktrees is its
advantage — and the branch rules are the constraint that makes it safe:
[wiki/BRANCH-WORKTREES.md](../../wiki/BRANCH-WORKTREES.md).

## The mistake it makes

**Two sessions writing the same worktree.** One mutable writer per worktree; a lane merges to the
default branch only, and a lane with `ahead=0` is finished and removed by the session that merged
it. Parallelism is in the worktrees, never in the writers.

Official: https://opencode.ai/docs
