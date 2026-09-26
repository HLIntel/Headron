# Zed adapter

**Adapter, not a second contract.** The rules are generated into [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md); the roster of runtimes is generated into [MODEL.md](../../MODEL.md)
from `atlas.yaml`. This page carries only what is specific to Zed — how the atlas is loaded here,
and the mistake this runtime makes.

## It is a HOST, not a model

Zed appears in `runtime_roles` as `multi_agent_host` and in **no model route**, and that placement
is the whole point. Every other entry answers "which model does this kind of work"; Zed answers
"where are several agents reachable at once". Each agent arrives over its own adapter, so the
panel is a meeting place rather than a participant, and nothing here should be phrased as though
Zed decided anything.

## How it loads

`AGENTS.md`, generated — the same body every other terminal runtime reads. Zed also carries
project tasks, and those are the part that needs discipline:

```bash
python scripts/atlas.py route <path> --json       # what a task should shell out to
python scripts/atlas.py process <id> --json       # the named process, end to end
python scripts/atlas.py do <path>                 # every action this file's pack can run
```

## What it is routed for

Reading and driving several agents in one place, and running this repository's instruments without
leaving the editor. It is routed for **no model work of its own**, which is why it is absent from
`model_routes`.

## Native tools stay

Zed keeps every tool it ships with — file, shell, search, edit, subagent, browser — configured in its own settings, and it may add, replace or drop any of them without asking Thea. Thea is added to this layer, never swapped in for it: its own shell runs the `thea` / `python scripts/atlas.py` commands; git runs the pre-commit hook it already commits through. An install writes only the git hook and never edits this runtime's tool configuration (`atlas.yaml/native_agent_tools`, checked by `nativetools.native_agent_tool_errors`). A task contract narrows commands only inside a run that opted into one.

## The mistake it makes

**Putting a capability in the host.** A task that exists only in `.zed/tasks.json` is a capability
that disappears for anyone not in Zed — for CI, for a terminal session, for a reviewer on another
machine — and its absence is silent, because the task still looks present to whoever configured
it. The rule is the one that names this page's own risk:

> **Be highly compatible with the host; never depend on it.**

So every task here is a thin wrapper over a command that runs on its own, and `atlas.py check`
enforces exactly that through the `host_is_not_a_capability` invariant: a host task whose command
does not resolve to a file in this tree fails the build. The same rule binds `.vscode/tasks.json`,
and it was written after two host configs in this repository turned out not to parse at all — a
task that silently did nothing, in a file nothing checked.

Official: https://zed.dev/docs

## Cloudflare MCP in Zed

Wired in the owner's Zed settings, never in this tree (host config is not a capability). Remote
server, OAuth on first use, so no token is stored anywhere:

```json
{ "context_servers": { "cloudflare": { "url": "https://mcp.cloudflare.com/mcp" } } }
```

Apply with the host's `zed-apply.sh`, which restarts Zed, reads Zed's own log and reverts on
rejection — a settings file Zed refuses is otherwise replaced by defaults, silently. Deploys and
secret writes through it stay behind `atlas.yaml/agent_policy/approval`.
