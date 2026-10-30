# Junie adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to Junie: how the atlas is loaded
here, and where its session artifacts go.

## How it loads

Junie reads `AGENTS.md` at the repository root. Its session artifacts (plans, state, temporary
working files) live under [`.junie/`](../../.junie/HEADRON.md), which is declared as a directory
scope in `atlas.yaml/directory_scopes/.junie`. Keep any Junie-specific rule file thin and let it
point at `AGENTS.md`: a second copy of the rules is the drift this repository refuses.

## Use its strength

Junie plans multi-step edits. Put the route first, then let the plan follow the gates the route
names:

```bash
python scripts/atlas.py port <file> --frame agent --json
```

Run the contract before claiming done:

```bash
python scripts/atlas.py check && python scripts/verify.py
```

## Native tools stay

Junie keeps every tool it ships with — file, shell, search, edit, and its planning and session
tools — configured in its own settings, and it may add, replace or drop any of them without asking
Headron. Headron is added to this layer, never swapped in for it: its shell runs the `headron` /
`python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through. An
install writes only the git hook and never edits this runtime's tool configuration
(`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract
narrows commands only inside a run that opted into one.

## The mistake it makes

**A plan that finishes before the gates run.** A plan step that says "done" after the edit skips
the route: the pack for each file declares its own formatter, test runner and gate. End each plan
with the verify command, and read its exit code.
