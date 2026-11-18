# OpenAI / Codex adapter

Rules: [CLAUDE.md](../../CLAUDE.md), [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

`AGENTS.md` at the repository root is the convention this runtime reads, and it is **generated**
from the same body as `CLAUDE.md` — one declaration, two files, no drift.

## Dynamic connectivity & unbreakable discovery

Codex executes deterministic repository edits and architecture tasks. To prevent brittle breakages:
- **Dual-path invocation:** Run `headron port <path> --frame agent --json` (or fallback `python scripts/atlas.py port <path> --frame agent --json`).
- **Structured output:** Depend on `--json` records (`tools/atlas-output.schema.json`), never unpiped text.
- **Fail-safe verification:** Run the contract and check that the exit code is zero:
  ```bash
  python scripts/atlas.py check
  ```

## What it is routed for

`deterministic_repo_edit` and `architecture`, per `atlas.yaml/model_routes`. It is strong at a
narrow, stated change across known files.

## Native tools stay

Codex keeps every tool it ships with — file, shell, search, edit, subagent, browser — configured in its own config file, and it may add, replace or drop any of them without asking Headron. Headron is added to this layer, never swapped in for it: its own shell runs the `headron` / `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP client may mount the read-only Headron route beside whatever servers it already has. An install writes only the git hook (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`); `headron init` adds one `headron` server to the project's Codex `config.toml`, keeps every server already there, and disables nothing. A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**Answering from the diff it can see rather than the route.** A change that touches two languages
has two manifests and two gates; the router says which. Ask before editing, not after.

Official: https://platform.openai.com/docs
