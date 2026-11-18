# Kilo adapter

Rules: [CLAUDE.md](../../CLAUDE.md), [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Kilo reads `AGENTS.md` at the repository root. Its session configuration lives under `.kilo/config.json`. Keep any
Kilo-specific instruction file thin and let it point at `AGENTS.md`: a second copy of the rules is the drift
this repository refuses.

## Clean entry dev spot & model roles

`.kilo/config.json` declares the local development base URL and companion model roles:
- `companion`: fast iterative drafting and formatting (`small`)
- `reviewer`: gate policy validation and mutation audit (`code`)
- `audit`: contract checking and invariant proofs (`deep`)

Use these roles to dispatch targeted subtasks without manual reconfiguration.

## Dynamic connectivity & unbreakable discovery

To remain resilient across environment changes, gateway migrations, or host updates:
- **Dual-path invocation:** Run `headron port <file> --frame agent --json` (or fallback `python scripts/atlas.py port <file> --frame agent --json`).
- **Structured output:** Depend on `--json` records (`tools/atlas-output.schema.json`), never unpiped terminal output.
- **Fail-safe verification:** Verify contracts and gates strictly on their exit codes before completing:
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
