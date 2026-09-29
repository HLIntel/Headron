# Multica adapter

Multica is a **host, not a model.** It appears in `runtime_roles` as
`multi_agent_host` and in no model route, and that placement is the whole point.
Every other entry answers "which model does this kind of work"; Multica answers
"in what am I reachable". Nothing routes *to* Multica, because Multica never
decided anything — the agent it drives did.

It replaced Zed in this role at 3.39.0.

## What it is

An interface over agents that stay **native**. Multica assigns work as Issues,
shows status, comments, blockers and a per-agent overview, and a daemon on a
*runtime* you control spawns the agent CLIs you already have installed and
authenticated. The agents' sessions, transcripts and resume remain their own.

## Entry file: none of its own

Multica has **no `runtime_entry` row**, unlike Zed, which had one claiming
`AGENTS.md`. That was true of Zed because Zed shipped a native agent that read
the file itself. Multica ships none. Each CLI it drives — `claude`, `codex`,
`opencode`, `cursor-agent` — loads its own entry file through its own adapter,
and those rows already exist. Giving Multica a row would assert a second reader
of `AGENTS.md` that does not exist.

Same treatment as `vscode`: a host in `runtime_roles` and in `models/`, absent
from `runtime_entry` and `native_agent_tools`.

## Tool configuration: not in the repository

Multica has **no `native_agent_tools` row** because it keeps no tool
configuration inside a repository. MCP servers are registered in Multica and
then assigned per agent from that agent's **MCP tab** — in Multica's own store,
not in a tracked file. Zed kept a settings file in its own dotdir here; there
is no Multica equivalent, and that directory was deleted from this tree with the
swap.

Thea reaches agents running under Multica exactly as before, through mechanisms
they already have: a shell runs the `thea` / `python scripts/atlas.py` commands,
and git runs the pre-commit hook. An install writes only the git hook. Nothing
here touches a runtime's tool configuration, and nothing may.

## Assignment is the thing to get right

Registering an MCP server in Multica does **not** expose it — it must also be
assigned to an agent. An unassigned server is visibly unassigned, which is an
improvement on what it replaced: under Zed, servers enabled at top level but
absent from every profile allowlist surfaced as nothing at all, silently.

Placement is a context decision. Every assigned server's tool definitions are
re-sent every turn, so a server that only one agent needs, and only sometimes,
belongs in neither that agent's native config nor Multica — call the CLI.

## Putting a capability in the host

A capability that exists only inside Multica disappears for anyone not in
Multica — for CI, for a terminal session, for a reviewer elsewhere. The rule Zed
carried applies unchanged: **every host task is a thin wrapper over a command
that runs without the host.** Multica's quick actions are the surface to watch;
if one grows logic of its own, that logic lives nowhere a terminal or CI can
reach it.

## Hosted vs self-hosted

The owner's runtime is the **hosted** plane (`api.multica.ai`), so Issue text,
comments and agent activity transit Multica's servers while code stays on the
runtime. Self-hosting is available (`multica setup self-host`; Go + Postgres +
Docker) if that boundary matters. `DO_NOT_TRACK=1` applies only to a
self-hosted API server.

Upstream: https://github.com/multica-ai/multica
