# Gemini CLI adapter

Rules: [AGENTS.md](../../AGENTS.md). Runtimes: [MODEL.md](../../MODEL.md).

## How it loads

Gemini CLI reads `GEMINI.md` unless told otherwise, and this repository keeps no such file. The tracked
[`.gemini/settings.json`](../../.gemini/settings.json) sets `context.fileName` to `AGENTS.md`, so a session
opened here reads `AGENTS.md`. In your own repository, add the same setting yourself; `headron init`
does not write it:

```json
{ "context": { "fileName": ["AGENTS.md"] } }
```

Vendor reference: [Gemini CLI context files](https://geminicli.com/docs/cli/gemini-md).

## Use its strength

Gemini CLI holds a long context, so a whole subsystem can be read in one session. Route first, so the
reading starts at the files the route names:

```bash
headron port <file> --frame agent --json
```

Run the contract before claiming done:

```bash
headron verify
```

## Native tools stay

Gemini CLI keeps every tool it ships with, configured in `.gemini/settings.json` or in your home
settings, and it may add, replace or drop any of them without asking Headron. Headron is added to this
layer, never swapped in for it: its shell runs `headron`, git runs the pre-commit hook, and an MCP
client may mount the read-only route. An install writes only the git hook and never edits this
runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by
`nativetools.native_agent_tool_errors`).

## The mistake it makes

**A session that never read the rules, with no error to say so.** Without `context.fileName`, a
repository holding only `AGENTS.md` gives Gemini CLI no context file at all. If an answer ignores the
route, check the setting before you check the answer.
