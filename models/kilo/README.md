# Kilo adapter

Rules: [CLAUDE.md](../../CLAUDE.md), [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Kilo reads `AGENTS.md` at the repository root. Its session configuration lives under `.kilo/`. Keep any
Kilo-specific instruction file thin and let it point at `AGENTS.md`: a second copy of the rules is the drift
this repository refuses.

## Use its strength

Kilo provides multi-model reasoning and companion task execution across engineering pipelines. Route the file
first, then let the execution plan follow the gates the pack declares:

```bash
python scripts/atlas.py port <file> --frame agent --json
```

Verify contracts and gates on their exit codes before completing:

```bash
python scripts/atlas.py check && python scripts/verify.py
```

## Native tools stay

Kilo keeps every native tool it ships with — file, shell, search, edit, terminal, and agent execution tools —
configured in its own settings, and it may add, replace or drop any of them without asking Headron. Headron is
added to this layer, never swapped in for it: its shell runs `python scripts/atlas.py` commands; git runs the
pre-commit hook it already commits through. An install writes only the git hook and never edits this runtime's tool
configuration (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract
narrows commands only inside a run that opted into one.

## The mistake it makes

**Finishing before verification passes.** An edit is not complete when files are changed: the route for each file
declares its own verification suite. Run the verification command and check that the exit code is zero.
