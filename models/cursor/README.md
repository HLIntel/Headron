# Cursor adapter

Rules: [CLAUDE.md](../../CLAUDE.md), [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Cursor reads `AGENTS.md`, and path-scoped rules where they are configured. Keep any rule file thin
and let it point here: a second copy of the rules is the drift this repository refuses.

Cursor reads MCP servers only from `<your repo>/.cursor/mcp.json` and `~/.cursor/mcp.json`, never a root
`.mcp.json`. `headron init` adds a `headron` entry there and keeps your own when one is already
there: `uvx --from headron-software headron-mcp` with `HEADRON_CLIENT_DIR` set to `${workspaceFolder}`.
It holds no absolute path, so a committed copy works in every clone.

## Cursor-family engines (including Grok Bot)

Engines hosted inside Cursor — including Grok Bot — share this adapter: the same entry file, the
same git hook, and the same Headron CLI. Set `HEADRON_AGENT` to the engine name (`cursor`, `grok-bot`,
`cursor-grok`, …) so every verification records which agent produced the change. `scripts/runtime.py`
rolls those ids up to the `cursor` family for scoring; it never invents a second contract.

## What it is routed for

`interactive_edit` — fast local iteration with the editor's own diagnostics in the loop.

## Use its strength

The native language server is the authority while you type. Run the contract before you claim
done:

```bash
python scripts/atlas.py check && python scripts/atlas_test.py
```

## Native tools stay

Cursor keeps every tool it ships with — file, shell, search, edit, subagent, browser — configured in its own settings and MCP file, and it may add, replace or drop any of them without asking Headron. Headron is added to this layer, never swapped in for it: its own shell runs the `headron` / `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP client may mount the read-only Headron route beside whatever servers it already has. An install writes only the git hook (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`); `headron init` adds one `headron` server to its project MCP file (see How it loads), keeps every server already there, and disables nothing. A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**A wide edit because the suggestion was wide.** Accepting a multi-file completion skips the
route: the pack for each file declares a different formatter, test runner and gate. Narrow the
edit, or route each file.

Official: https://docs.cursor.com
