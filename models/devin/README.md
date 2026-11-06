# Devin adapter

**Adapter, not a second contract.** The rules are generated into [AGENTS.md](../../AGENTS.md), and the
roster of runtimes into [MODEL.md](../../MODEL.md) from `atlas.yaml`. This page carries only what is
specific to Devin: how the atlas is loaded here.

## How it loads

Devin CLI reads `AGENTS.md` at the project root, and nothing needs configuring. Vendor reference:
[Devin CLI rules](https://docs.devin.ai/cli/extensibility/rules).

## Use its strength

Devin takes long tasks on its own. Give the task its route up front, and make the verdict its stopping
condition:

```bash
headron port <file> --frame agent --json
headron verify
```

## Native tools stay

Devin keeps every tool it ships with, configured in its project and home settings, and it may add, replace or drop any of them without asking Headron. Headron is added
to this layer, never swapped in for it: its shell runs `headron`, git runs the pre-commit hook, and an
MCP client may mount the read-only route. An install writes only the git hook and never edits this
runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by
`nativetools.native_agent_tool_errors`).

## The mistake it makes

**A rule the other agents cannot see.** `~/.config/devin/AGENTS.md` applies to every project on one
machine and is not in the repository. A project rule put there binds Devin alone, and only on that
machine. Keep project rules in `atlas.yaml`, which generates `AGENTS.md`.
