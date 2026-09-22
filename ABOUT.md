# Code-Development

**Repository contract: v0.9.3**

Code-Development is an advanced model-aware code-development atlas and operating system for polyglot programming, AI coding agents, IDEs, Git/GitHub workflows, MCP/connectors, cloud/runtime operations, databases and Redis, testing, mutation analysis, security, reliability, research, and verification.

The repository is structured as a control plane plus a code-development knowledge layer:
- **Control:** [MODEL.md](MODEL.md)
- **Machine routing:** [atlas.yaml](atlas.yaml)
- **Human navigation:** [docs/INDEX.md](docs/INDEX.md)
- **Code wiki:** [wiki/README.md](wiki/README.md)
- **Language routing:** [languages/ATLAS.md](languages/ATLAS.md)
- **Language operations:** [wiki/LANGUAGE-OPERATIONS.md](wiki/LANGUAGE-OPERATIONS.md)
- **Runtime adapters:** [models/README.md](models/README.md)
- **MCP routing:** [integrations/MCP-LANGUAGE-MATRIX.md](integrations/MCP-LANGUAGE-MATRIX.md)
- **GitHub security/finalization:** [docs/GITHUB-FINALIZATION.md](docs/GITHUB-FINALIZATION.md)
- **Security policy:** [SECURITY.md](SECURITY.md)
- **Deterministic verification:** [scripts/atlas.py](scripts/atlas.py) and [docs/VERIFY.md](docs/VERIFY.md)

## Code-development principle

Start with the code artifact and failure class. Route to the smallest tool chain that can explain, change, and verify the behavior.

`artifact -> language -> native toolchain -> task -> scoped tool profile -> independent verification -> CI`

The repository treats compilers, LSPs, debuggers, test runners, profilers, database-native tools, and proof kernels as authoritative. AI, MCP, cloud tooling, and GitHub automation extend context and orchestration without replacing executable evidence.

## Reliability and data

Language guides are paired with production concerns: uptime/deadlines, cloud deployment shape, Redis/Upstash usage where applicable, database state, endpoint testing, mutation testing, observability, boundary compatibility, rollback, and failure isolation.

See [wiki/LANGUAGE-OPERATIONS.md](wiki/LANGUAGE-OPERATIONS.md), [systems/OPERATIONS-UPTIME.md](systems/OPERATIONS-UPTIME.md), [systems/STORAGE-STATE.md](systems/STORAGE-STATE.md), and [integrations/ENDPOINTS.md](integrations/ENDPOINTS.md).

## GitHub and AI assurance

GitHub's public-repository security stack can combine CodeQL, Copilot Autofix, secret scanning/push protection, dependency graph/dependency review, and Dependabot. CodeQL currently supports C/C++, C#, Go, Java/Kotlin, JavaScript/TypeScript, Python, Ruby, Rust, Swift, and GitHub Actions; unsupported atlas languages retain their native verification stacks.

See [docs/GITHUB-FINALIZATION.md](docs/GITHUB-FINALIZATION.md).
