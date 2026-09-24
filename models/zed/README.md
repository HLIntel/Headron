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
