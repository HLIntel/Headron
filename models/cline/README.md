# Cline adapter

Rules: [CLAUDE.md](../../CLAUDE.md), [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Cline reads `AGENTS.md` and path-scoped instruction files configured in the workspace. Keep any
additional rule file thin and let it point to `AGENTS.md`: a second copy of the rules is the
drift this repository refuses.

## Use its strength

Cline executes interactive terminal workflows and targeted edits with direct workspace awareness.
Route first to load only the checks the specific file owes:

```bash
headron port <file> --frame agent --json
```

Verify the contract before claiming a change is finished:

```bash
headron verify
```

## Native tools stay

Cline keeps every tool it ships with — file, shell, search, edit, browser — configured in its own settings and MCP file, and it may add, replace or drop any of them without asking Headron. Headron is added to this layer, never swapped in for it: its own shell runs the `headron` / `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP client may mount the read-only Headron route beside whatever servers it already has. An install writes only the git hook and never edits this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**Fabricated completion or truncated payload copy-paste.** A session that hits token or output
bounds claiming a wide merge or pasting line-number prefixes directly into source has not verified
the change. Run `headron verify` and verify the exit code, never an unpiped status text.
