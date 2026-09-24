# Subagent pattern

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to a subagent — how the atlas is loaded
here, and the mistake this runtime makes.

## When a subagent earns its cost

Broad, read-only work whose *conclusion* is what you need — a sweep across many files, an
inventory, a cross-document audit. The reason is context, not speed: the agent reads the files and
you keep the finding.

## When it does not

- **A single fact you can route to.** `atlas.py route <path>` is cheaper than any agent.
- **Anything that writes.** Two writers in one tree is the conflict this repository's worktree
  rules exist to prevent. Give a writing agent its own worktree or do it yourself.
- **Verification.** An agent's report is a hypothesis; the exit code is the verdict.

## What to give one

The route, not the repository. A subagent handed `atlas.yaml` and one pack works; a subagent
handed the tree spends its window on navigation — the same failure the atlas exists to prevent,
one level down.

## What to ask for back

Findings as `path:line — what is wrong — what it should be`, ranked, capped. A narrative costs
more to read than the sweep cost to run.
