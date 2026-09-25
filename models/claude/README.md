# Claude Code adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to Claude Code — how the atlas is loaded
here, and the mistake this runtime makes.

## How it loads

`CLAUDE.md` at the repository root is read automatically, and it is **generated** — so the rules a
session starts with cannot drift from `atlas.yaml`. Nothing else needs to be pasted in.

## Use in this order

```bash
python scripts/atlas.py gate  <path> <gate>      # FIRST: the one command — 90% fewer tokens, same accuracy
python scripts/atlas.py route <path> --json      # when the whole pack is needed
python scripts/atlas.py plan  <path> --task debugging --change source_change --json
```

## What this runtime maps to

| repository control | Claude Code surface |
|---|---|
| durable project behaviour | the generated `CLAUDE.md` |
| a procedure worth repeating | a Skill, loaded on demand |
| a deterministic restriction | a hook — **not** an instruction |
| an external capability | MCP, scoped to a task profile |
| broad exploration without polluting context | a subagent |

## The mistake it makes

**Reading breadth-first because the context window allows it.** A large window makes a
whole-repository read possible, not correct: `atlas.yaml/context_policy/forbidden_default` names
`whole_repo_dump` for that reason. Route, load the one pack, then act.

**And: model instructions are not a sandbox.** Anything that must not happen belongs in a hook, in
the contract, or in the ruleset — three things that do not depend on a model's cooperation.

Official: https://code.claude.com/docs/en/features-overview
