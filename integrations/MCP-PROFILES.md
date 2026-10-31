# MCP Profiles and Capability Composition

Profiles keep the tool, permission, and context surface bounded.
`atlas.yaml/tool_profiles` is the machine-readable declaration; this page is the prose companion.

## Pick the smallest mechanism

| Mechanism | Best purpose | Authority |
|---|---|---|
| model instructions | always-true operating constraints | advisory |
| Skill | reusable procedure; routes to deep reference docs | procedural |
| hook | deterministic action / enforcement | execution |
| plugin | coherent capability bundle | capability |
| MCP | external tools / resources with explicit schemas | scoped capability |
| connector | maintained external service whose permission model fits the task | service boundary |
| subagent | context isolation, parallel investigation, bounded research | isolated reasoning |
| memory | durable facts / decisions with scope and provenance, never transcripts | persistent context |
| static analysis | source and supply-chain analysis | deterministic analysis |
| remediation proposal | AI-assisted fix suggestion, secondary review | AI proposal |
| dependency automation | update automation, introduced-risk CI gate | automation / CI gate |
| secret scanning | credential leak prevention | platform control |

```
route → native tool → semantic context if needed → external capability if needed
      → independent verifier → CI
```

Never make an AI tool the only verifier of an AI-generated change. Tool descriptions, connector
outputs, remote servers, and memory are NOT security boundaries: deterministic enforcement belongs
in code, policy, hooks, CI, or sandboxing.

## Designing an MCP tool

Narrow purpose, typed input, bounded and paginated output, explicit side effects, authorization,
timeout / cancellation, retryability, observability, stable deterministic names and order,
approval for high-impact calls. Scope connector data to the task: one record, never the whole
account. Follow the dated specification the runtime uses; the 2026-07-28 specification deprecated
roots and sampling — build filesystem boundaries on explicit server configuration and resource URIs
([specification](https://modelcontextprotocol.io/specification/2026-07-28)).

## Profiles

### core-code
Forge (remote repository, issues, PRs, CI, security context) + semantic code edit (LSP-backed)
+ native CLI / language server / compiler / debugger.

### docs
Add external documentation server for current library and framework documentation.

### browser
Add browser automation server for UI and integration tests and controlled web interaction.

### security
Add deterministic static security scanning (local CLI-backed) plus native security tooling.

### database
Add database inspection server for local / staging schema and query access with read-only,
row-count, query-time, and connection limits.

### polyglot
Use core-code + native toolchains for both sides + boundary contract / integration tests.
Add docs server only when API or version questions require it.

## Profile rule

One task → one profile. Add servers only when their capability is required for that task.

Project-wide MCP capability belongs in the workspace MCP config. Personal tools belong in user
configuration. Do not configure the same server in both places.

All local MCP servers are executable code: review source, permissions, environment,
filesystem / network access, and trust before enabling.

## The cost nobody counts

**An enabled server is paid for on EVERY request, not on the request that uses it.** Its tool
descriptions enter the model's context whether or not the task touches them, so an unused server
is a subscription rather than an option — and that cost is invisible, because nothing in the
output says which servers were loaded.

`atlas.yaml/developer_baseline/mcp` states the rule this page implements:

- **Enable the profile the task names, and nothing else. Disable it when the task ends.**
- **Before adding one, ask what already answers the question** — and what the server can reach
  that the task does not need. Native language tooling is authoritative; MCP augments it and
  never replaces it.
- `atlas.yaml/tool_profiles` caps what activates unasked, and `mcp_is_task_scoped` is a hard
  invariant: a server in the example config that no published profile names fails the build,
  and a literal credential in that file fails it too.

The entry-path budget in `context_policy` bounds what a session is handed before it asks anything.
Server descriptions are outside that measurement — precisely why they need a rule rather than
a good intention.

## Client setup

Copy-paste setup for the Headron MCP server across supported clients. Each configuration
sets `HEADRON_ROOT` to the repository root and connects over stdio.

The local server exposes read-only tools. A named gate is a proposed check, not a passing result;
inspect the returned verdict to see whether a check actually ran.
Set `HEADRON_MCP_VERBS` to a comma-separated subset of offered verbs to narrow an agent's access.
This is a process-level grant, so give the process only the filesystem and environment it needs.

Hosted Mind is optional. Setting `HEADRON_MIND_URL` sends Mind requests to that endpoint; requests
that name files include those paths in the request body. Use a trusted HTTPS endpoint, and supply
`HEADRON_MIND_KEY` through the client environment rather than a checked-in configuration file.
Plain HTTP is accepted only for loopback development. The local read-only route and a hosted Mind
service are distinct; enabling either does not create an account or prove a subscription is active.

### Claude Code

Add the server through the CLI:

```bash
claude mcp add headron -e HEADRON_ROOT="." -- python3 scripts/headron_mcp.py
```

Or configure in `~/.claude.json`:

```json
{
  "mcpServers": {
    "headron": {
      "command": "python3",
      "args": ["scripts/headron_mcp.py"],
      "env": {
        "HEADRON_ROOT": "."
      }
    }
  }
}
```

### Codex

Configure in `~/.codex/config.json`:

```json
{
  "mcpServers": {
    "headron": {
      "command": "python3",
      "args": ["scripts/headron_mcp.py"],
      "env": {
        "HEADRON_ROOT": "."
      }
    }
  }
}
```

### Cursor

Configure in Cursor MCP settings:

```json
{
  "mcpServers": {
    "headron": {
      "command": "python3",
      "args": ["scripts/headron_mcp.py"],
      "env": {
        "HEADRON_ROOT": "."
      }
    }
  }
}
```

### VS Code

Configure in VS Code (copy from `.vscode/mcp.json.example`):

```json
{
  "servers": {
    "headron": {
      "command": "python3",
      "args": [
        "scripts/headron_mcp.py"
      ],
      "env": {
        "HEADRON_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```
