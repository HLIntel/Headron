# Code-Development

**Repository contract: v2.11.0**

Code-Development is an advanced model-aware code-development atlas and operating system for polyglot programming, AI coding agents, IDEs, Git/GitHub workflows, MCP/connectors, cloud/runtime operations, databases and Redis, testing, mutation analysis, security, reliability, research, and verification.

The map of the control plane and knowledge layer is the **Start Here** list in [README.md](README.md); it is kept in one place only.

## Apian Software, and this repository

**Apian Software** is the umbrella the work is done under; `ApianSoftware` is its GitHub account.
**Code-Development is one repository inside it, and the only public one — deliberately.**

That single decision shapes everything here. It is public because a raw URL has to be fetchable by
any model or agent without a token: an atlas that requires credentials to read cannot route an
agent that has none. The cost of that choice is a hard rule, and it is not a preference:

> **This repository never contains a secret, a credential, a private-project path, or an internal
> hostname.** Not in a file, not in an example, not in history. Everything operational lives in a
> private repository; what lives here is the method.

So the division is by KIND, not by importance:

| | Apian Software, private | Code-Development, public |
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

Language cards pair language knowledge with production concerns: uptime/deadlines, cloud deployment shape, Redis/Upstash usage where applicable, database state, endpoint testing, mutation testing, observability, boundary compatibility, rollback, and failure isolation.

See [wiki/LANGUAGE-OPERATIONS.md](wiki/LANGUAGE-OPERATIONS.md), [systems/OPERATIONS-UPTIME.md](systems/OPERATIONS-UPTIME.md), [systems/STORAGE-STATE.md](systems/STORAGE-STATE.md), and [integrations/ENDPOINTS.md](integrations/ENDPOINTS.md).

## Dynamic verification

Task-specific required gates are machine-readable in `atlas.yaml`: source, API, dependency, security, concurrency, and performance changes each select explicit verification requirements. Warnings remain visible without automatically blocking merges; blockers/errors do block; baselines cannot absorb new findings.

## GitHub and AI assurance

GitHub's public-repository security stack can combine CodeQL, Copilot Autofix, secret scanning/push protection, dependency graph/dependency review, and Dependabot. Supported languages use CodeQL where applicable; unsupported atlas languages retain their native verification stacks.

See [docs/GITHUB-BACKEND.md](docs/GITHUB-BACKEND.md) and [docs/GITHUB-FINALIZATION.md](docs/GITHUB-FINALIZATION.md).
