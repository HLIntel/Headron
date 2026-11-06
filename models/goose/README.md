# goose adapter

**Adapter, not a second contract.** The rules are generated into [AGENTS.md](../../AGENTS.md), and the
roster of runtimes into [MODEL.md](../../MODEL.md) from `atlas.yaml`. This page carries only what is
specific to goose: how the atlas is loaded here.

## How it loads

goose reads `AGENTS.md` and `.goosehints` at each directory level by default, so nothing needs
configuring. Vendor reference: [providing hints to goose](https://goose-docs.ai/docs/guides/context-engineering/using-goosehints/).

## Use its strength

goose runs recipes and extensions unattended. Put the route at the start of a recipe and the verdict at
the end, so an unattended run ends on an exit code rather than on its own summary:

```bash
headron port <file> --frame agent --json
headron verify
```

## Native tools stay

goose keeps its extensions and tool permissions in `~/.config/goose/config.yaml`, outside any repository,
and it may add, replace or drop any of them without asking Headron. Headron is added to this layer,
never swapped in for it: its shell runs `headron`, git runs the pre-commit hook, and the read-only
route can be mounted as an MCP extension. An install writes only the git hook and never edits this
runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by
`nativetools.native_agent_tool_errors`).

## The mistake it makes

**A context override that drops the rules.** Setting `CONTEXT_FILE_NAMES` replaces the default list, so
a value that leaves out `AGENTS.md` stops loading it. Keep `AGENTS.md` in that list, and keep
`.goosehints` to what is specific to goose: a second copy of the rules is the drift this repository
refuses.
