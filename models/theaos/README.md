# TheaOS adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to a host that runs other agents' engines.

## How it loads

`llms.txt`, vendored verbatim into the app and put ahead of each code thread's instructions (`CHAT.md`
for a chat thread). Per turn it adds `thea intake --brief --json`, a packet held to
`atlas.yaml/context_policy/per_turn_bytes`.

## What a host is for

One window over several engines, each with its own login. TheaOS wires its own hooks from
`thea process hosted_turn --json`: the event, the step, the argv and the deadline of each call. Every call
fails open, and a shell refusal asks rather than denies. `atlas.yaml/companions/theaos/consumes` lists
every call, and `thea check` refuses a release that drops one.

## Native tools stay

Each engine TheaOS hosts keeps every tool it ships with, configured in the app's own settings outside any
repository, and may add, replace or drop any of them without asking Thea. Thea is added to this layer,
never swapped in for it: the host's hooks run the `thea` CLI, an engine may mount the read-only MCP route,
and an install writes only the git hook (`atlas.yaml/native_agent_tools`, checked by
`nativetools.native_agent_tool_errors`).

## The mistake it makes

**Injecting context nobody measured.** A per-turn packet is paid on every request, so it ships behind a
flag that is off until an evaluation shows the gain, and its bytes are a ratchet.
