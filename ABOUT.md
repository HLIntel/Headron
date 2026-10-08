# About Thea Software

**Repository contract: v3.52.0**

**Thea Software**, by HLIntel LLC, tells an AI coding agent which commands prove a change to a file, and fails the build when a change skipped them. It spans many languages, Git and GitHub workflows, MCP, and agent controls. The name is an acronym: *The Heartland Engineering Atlas*.

The map of everything else is the **Find your way** table in [README.md](README.md); it is kept in one place only.

## HLIntel LLC, and this repository

**HLIntel LLC** is the company the work is done under; `HLIntel` is its GitHub account.
**Thea is one repository inside it, and the only public one — deliberately.**

That single decision shapes everything here. It is public because a raw URL has to be fetchable by
any model or agent without a token: an atlas that requires credentials to read cannot route an
agent that has none. The cost of that choice is a hard rule, and it is not a preference:

> **This repository never contains a secret, a credential, a private-project path, or an internal
> hostname.** Not in a file, not in an example, not in history. Everything operational lives in a
> private repository; what lives here is the method.

So the division is by KIND, not by importance:

| | HLIntel LLC, private | Thea, public |
|---|---|---|
| holds | the running systems, their state, their keys | the routes, contracts, manifests and verification method |
| changes when | a system changes | the method changes |
| verified by | each project's own door and tests | `atlas.py check` plus its mutation harness |
| safe to hand an unknown agent | no | yes, entirely |

**What this repository is not:** it is not an application, not a framework you install, and not a
record of what any private system currently does. Treat a claim here as a method to apply, and
measure it against your own tree before relying on it.

## Code-development principle

Start with the goal, code artifact, and failure class. Route to the smallest tool chain that can explain, change, and verify the behavior.

`goal -> artifact -> language -> native toolchain -> tool manifest -> boundary -> task -> scoped tool profile -> independent verification -> CI`

The repository treats compilers, LSPs, debuggers, test runners, profilers, database-native tools, and proof kernels as authoritative. AI, MCP, cloud tooling, and GitHub automation extend context and orchestration without replacing executable evidence.

## Reliability and data

Language cards pair language knowledge with production concerns: uptime/deadlines, cloud deployment shape, cache and queue state, database state, endpoint testing, mutation testing, observability, boundary compatibility, rollback, and failure isolation.

See [wiki/LANGUAGE-OPERATIONS.md](wiki/LANGUAGE-OPERATIONS.md), [systems/OPERATIONS-UPTIME.md](systems/OPERATIONS-UPTIME.md), [systems/STORAGE-STATE.md](systems/STORAGE-STATE.md), and [integrations/API-CONTRACTS.md](integrations/API-CONTRACTS.md#endpoints).

## Dynamic verification

Each change class selects its required gates in `atlas.yaml`; what blocks and what warns: [MODEL.md](MODEL.md).

## GitHub and AI assurance

The repository-host security controls this project relies on are declared in [config/github-controls.json](config/github-controls.json); languages the host's scanner does not cover keep their own pack's gates.

See [docs/GITHUB-BACKEND.md](docs/GITHUB-BACKEND.md) and [docs/GITHUB-FINALIZATION.md](docs/GITHUB-FINALIZATION.md).

## Topics

<!-- BEGIN generated: topics (python scripts/atlas.py index --write) -->
Declared in `config/github-controls.json` and asserted against the live repository by
`python scripts/ghaudit.py` — this page states the declaration, the instrument states
the fact.

`agent-tooling` · `ai-agents` · `code-quality` · `data-science` · `developer-tools` · `engineering-atlas` · `github-actions` · `heartland-intel` · `llm` · `mcp` · `openssf` · `polyglot` · `quantum-computing` · `software-engineering` · `static-analysis` · `supply-chain-security` · `thea` · `thea-software` · `verification`
<!-- END generated: topics -->
