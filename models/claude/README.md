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
python scripts/atlas.py gate  <path> <gate>      # FIRST: the cheapest answer, and the most accurate
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

## Whatever model you are

**Nothing here names a model version, and nothing should.** Claude Code runs whichever model the session
was given; the contract is the same for all of them, and the parts that must bend are declared rather
than assumed:

| you are | do this |
|---|---|
| a smaller or cheaper model | `thea steps <file> --tier small` — the same facts plus a work loop, a scope fence and an explicit stop rule |
| a frontier model | `thea steps <file> --tier frontier` — the commands and the return point, nothing else |
| unsure what the user wants | `thea intake "<their words>"` — it routes the files, reads the change class, and asks only what blocks action |
| directed into a role | `thea role <name>` — what that role may do, may not do, hands back, and when it ends |
| picking up interrupted work | `thea resume` — the lane, the leftovers and one next action, rebuilt from the tree, never from memory |
| working to a clock | `thea cadence` — the phases, the reserved verification budget, and what to do when the box expires |

Two things follow from this. A measured figure belongs in a generated block, never typed into a page that
outlives the run that measured it. And the co-authorship line on a commit names the model that actually
ran — read it from the session, never copy a version out of a document.

## Native tools stay

Claude Code keeps every tool it ships with — file, shell, search, edit, subagent, browser — configured in its settings and permission files, and it may add, replace or drop any of them without asking Thea. Thea is added to this layer, never swapped in for it: its own shell runs the `thea` / `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP client may mount the read-only Thea route beside whatever servers it already has. An install writes only the git hook and never edits this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**Reading breadth-first because the context window allows it.** A large window makes a
whole-repository read possible, not correct: `atlas.yaml/context_policy/forbidden_default` names
`whole_repo_dump` for that reason. Route, load the one pack, then act.

**And: model instructions are not a sandbox.** Anything that must not happen belongs in a hook, in
the contract, or in the ruleset — three things that do not depend on a model's cooperation.

Official: https://code.claude.com/docs/en/features-overview
