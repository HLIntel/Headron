# OpenAI / Codex adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to Codex — how the atlas is loaded
here, and the mistake this runtime makes.

## How it loads

`AGENTS.md` at the repository root is the convention this runtime reads, and it is **generated**
from the same body as `CLAUDE.md` — one declaration, two files, no drift.

## Use in this order

```bash
python scripts/atlas.py route <path> --json
python scripts/atlas.py check                    # the exit code is the verdict
```

## What it is routed for

`deterministic_repo_edit` and `architecture`, per `atlas.yaml/model_routes`. It is strong at a
narrow, stated change across known files.

## Native tools stay

Codex keeps every tool it ships with — file, shell, search, edit, subagent, browser — configured in its own config file, and it may add, replace or drop any of them without asking Thea. Thea is added to this layer, never swapped in for it: its own shell runs the `thea` / `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP client may mount the read-only Thea route beside whatever servers it already has. An install writes only the git hook and never edits this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**Answering from the diff it can see rather than the route.** A change that touches two languages
has two manifests and two gates; the router says which. Ask before editing, not after.

Official: https://platform.openai.com/docs
