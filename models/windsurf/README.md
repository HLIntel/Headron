# Windsurf adapter

Rules: [CLAUDE.md](../../CLAUDE.md), [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Windsurf reads `AGENTS.md` and `.windsurfrules`. Keep any `.windsurfrules` file thin and let it
point to `AGENTS.md`: a second copy of the rules is the drift this repository refuses.

## Use its strength

Windsurf pairs fast semantic indexing with real-time Cascade workspace diffs. Route first to load
only the specific tools and gates the file owes:

```bash
headron port <file> --frame agent --json
```

Verify the contract before claiming a change is finished:

```bash
headron verify
```

## Native tools stay

Windsurf keeps every tool it ships with — file, shell, search, edit, Cascade execution — configured in its own settings and MCP file, and it may add, replace or drop any of them without asking Headron. Headron is added to this layer, never swapped in for it: its own shell runs the `headron` / `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through; its MCP client may mount the read-only Headron route beside whatever servers it already has. An install writes only the git hook and never edits this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**Relying on editor diagnostics rather than running repo gates.** An in-editor linter pass that looks
clean does not prove that tests, mutation suites, or invariants passed. Always run `headron verify`
and check the exit code before claiming completion.
