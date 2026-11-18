# Devin adapter

Rules: [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Devin CLI reads `AGENTS.md` at the project root, and nothing needs configuring. Vendor reference:
[Devin CLI rules](https://docs.devin.ai/cli/extensibility/rules).

## Dynamic connectivity & unbreakable discovery

Devin takes long autonomous tasks on its own. To ensure unbreakable connectivity:
- **Dual-path invocation:** Run `headron port <file> --frame agent --json` (or fallback `python scripts/atlas.py port <file> --frame agent --json`).
- **Structured output:** Depend on `--json` records (`tools/atlas-output.schema.json`), never volatile progress logs.
- **Fail-safe verification:** Make the verdict the stopping condition, judging strictly by exit code:
  ```bash
  python scripts/atlas.py check && python scripts/verify.py
  ```

## Native tools stay

Devin keeps every tool it ships with, configured in its project and home settings, and it may add, replace or drop any of them without asking Headron. Headron is added
to this layer, never swapped in for it: its shell runs `headron` / `python scripts/atlas.py`, git runs the pre-commit hook, and an
MCP client may mount the read-only route. An install writes only the git hook and never edits this
runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by
`nativetools.native_agent_tool_errors`).

## The mistake it makes

**A rule the other agents cannot see.** `~/.config/devin/AGENTS.md` applies to every project on one
machine and is not in the repository. A project rule put there binds Devin alone, and only on that
machine. Keep project rules in `atlas.yaml`, which generates `AGENTS.md`.
