# Code-Development

**Repository contract: v0.9.7**

Code-Development is an advanced model-aware code-development atlas and operating system for polyglot programming, AI coding agents, IDEs, Git/GitHub workflows, MCP/connectors, cloud/runtime operations, databases and Redis, testing, mutation analysis, security, reliability, research, and verification.

The map of the control plane and knowledge layer is the **Start Here** list in [README.md](README.md); it is kept in one place only.

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
