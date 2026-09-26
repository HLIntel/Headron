# Cursor adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to Cursor — how the atlas is loaded
here, and the mistake this runtime makes.

## How it loads

Cursor reads `AGENTS.md`, and path-scoped rules where they are configured. Keep any rule file thin
and let it point here: a second copy of the rules is the drift this repository refuses.

## What it is routed for

`interactive_edit` — fast local iteration with the editor's own diagnostics in the loop.

## Use its strength

The native language server is the authority while you type. Run the contract before you claim
done:

```bash
python scripts/atlas.py check && python scripts/atlas_test.py
```

## Native tools stay

Cursor keeps every tool it ships with — file, shell, search, edit, subagent, browser — configured in its own settings and MCP file, and it may add, replace or drop any of them without asking Thea. Thea is added to this layer, never swapped in for it: its own shell runs the `thea` / `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP client may mount the read-only Thea route beside whatever servers it already has. An install writes only the git hook and never edits this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**A wide edit because the suggestion was wide.** Accepting a multi-file completion skips the
route: the pack for each file declares a different formatter, test runner and gate. Narrow the
edit, or route each file.

Official: https://docs.cursor.com
