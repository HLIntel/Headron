# Muse adapter

Rules: [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Muse reads `AGENTS.md` and repository task contracts. The MCP server can be mounted via stdio
(`headron-mcp`) or pointed at `https://headron.tech/mcp` for hosted documentation.

## Dynamic connectivity & unbreakable discovery

Muse connects directly to the repository and respects tool boundaries:

- **Dual-path invocation:** Run `headron port <target> --frame agent --json` (or `python scripts/atlas.py port <target> --frame agent --json`).
- **Structured output:** Depend on `--json` records (`tools/atlas-output.schema.json`), never raw terminal text.
- **Fail-safe verification:** Judge outcomes strictly by exit code (`0` = PASS, non-zero = FAIL).

## Native tools stay

Muse keeps every tool it ships with — file, search, shell, and editor mechanisms — configured in its
own environment, and it may add, replace or drop any of them without asking Headron. Headron is
added to this layer, never swapped in for it: its shell runs `headron`, git runs the pre-commit hook,
and an MCP client may mount the read-only route. An install writes only the git hook and never edits
this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by
`nativetools.native_agent_tool_errors`).

## The mistake it makes

**Claiming verification without running the proving gate.** An agent cannot infer a pass from a plan
or prompt context alone. Name the gates from `port`, execute them, and verify the exit code is 0.
