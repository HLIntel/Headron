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

## Native tools stay

opencode keeps every tool it ships with — file, shell, search, edit, subagent, browser — configured in its own config file, and it may add, replace or drop any of them without asking Thea. Thea is added to this layer, never swapped in for it: its own shell runs the `thea` / `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP client may mount the read-only Thea route beside whatever servers it already has. An install writes only the git hook and never edits this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**Two sessions writing the same worktree.** One mutable writer per worktree; a lane merges to the
default branch only, and a lane with `ahead=0` is finished and removed by the session that merged
it. Parallelism is in the worktrees, never in the writers.

Official: https://opencode.ai/docs
