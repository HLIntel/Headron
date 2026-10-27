# About Headron Software

**Repository contract: v3.60.0**

**Headron Software**, by HLIntel LLC, tells an AI coding agent which commands prove a change to a file, and fails the build when a change skipped them. It spans many languages, Git and GitHub workflows, MCP, and agent controls. HLIntel stands for Headron Layer Intelligence.

The map of everything else is the **Find your way** table in [README.md](README.md); it is kept in one place only.

## HLIntel LLC, and this repository

**HLIntel LLC** is the company the work is done under; `HLIntel` is its GitHub account.
**Headron Software is the public verification toolkit.**

That single decision shapes everything here. It is public because a raw URL has to be fetchable by
any model or agent without a token: an atlas that requires credentials to read cannot route an
agent that has none. The cost of that choice is a hard rule, and it is not a preference:

> **This repository never contains a secret, a credential, a private-project path, or an internal
> hostname.** Not in a file, not in an example, not in history. Everything operational lives in a
> private repository; what lives here is the method.

So the division is by KIND, not by importance:

| | HLIntel LLC, private | Headron Software, public |
|---|---|---|
| holds | the running systems, their state, their keys | the routes, contracts, manifests and verification method |
| changes when | a system changes | the method changes |
| verified by | each project's own door and tests | `atlas.py check` plus its mutation harness |
| safe to hand an unknown agent | no | yes, entirely |

**What this repository is:** an installable, reusable verification toolkit and reference method.
It is not a product-specific application and does not record what any private system currently
does. Treat each claim as a method to apply, and measure it against your own tree before relying
on it.

## Build your own product

The MIT License permits anyone to use, modify, merge, publish, distribute, sublicense and sell
copies or products built with Headron Software, including commercial and closed-source products, while keeping
the required license notice. You do not need an HLIntel service, account or approval.

The public/private boundary protects operations; it does not reserve product categories. Public:
the CLI, MCP server, contracts, verification engine, adapters, schemas, examples and documentation.
Private to each operator: credentials, customer data, deployment state, internal hostnames and the
running infrastructure that uses them. Put your product-specific policy in your own repository and
keep secrets out of both this public tree and downstream public forks.

## Code-development principle

Start with the goal, code artifact, and failure class. Route to the smallest tool chain that can explain, change, and verify the behavior.

`goal -> artifact -> language -> native toolchain -> tool manifest -> boundary -> task -> scoped tool profile -> independent verification -> CI`

The repository treats compilers, LSPs, debuggers, test runners, profilers, database-native tools, and proof kernels as authoritative. AI, MCP, cloud tooling, and GitHub automation extend context and orchestration without replacing executable evidence.

## Reliability and data

Language cards pair language knowledge with production concerns: uptime/deadlines, cloud deployment shape, cache and queue state, database state, endpoint testing, mutation testing, observability, boundary compatibility, rollback, and failure isolation.

See [docs/wiki/LANGUAGE-OPERATIONS.md](docs/wiki/LANGUAGE-OPERATIONS.md), [docs/systems/OPERATIONS-UPTIME.md](docs/systems/OPERATIONS-UPTIME.md), [docs/systems/STORAGE-STATE.md](docs/systems/STORAGE-STATE.md), and [integrations/API-CONTRACTS.md](integrations/API-CONTRACTS.md#endpoints).

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

`agent-tooling` · `agents-md` · `ai-agents` · `ai-coding-agents` · `ci-cd` · `claude-code` · `code-quality` · `code-verification` · `developer-tools` · `github-actions` · `llm` · `llm-eval` · `mcp` · `openssf` · `polyglot` · `software-engineering` · `static-analysis` · `supply-chain-security` · `thea` · `verification`
<!-- END generated: topics -->
