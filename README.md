# Code-Development

**Repository contract: v0.6.0**

Advanced, model-aware engineering atlas for programming languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, and verification.

> Read first: [MODEL.md](MODEL.md) -> [docs/INDEX.md](docs/INDEX.md) -> [atlas.yaml](atlas.yaml) -> runtime/model adapter -> exact domain guide -> pattern -> example/prompt -> verification.

## Purpose
Practical engineering atlas. Every stack is scoped by purpose, fit, guarantees, tools, project structure, common mistakes, streamlining, learning direction, AI usage, and verification.

## Contract
- no unbounded resource/work/time/retry/queue/cache/recursion/network/storage/agent growth without explicit justification
- immutable-first state and explicit ownership of mutable state
- schema-first boundaries
- explicit deadlines, cancellation, and shutdown
- least privilege
- independent verification
- reproducible/auditable changes
- rollback/snapshot for high-impact mutation
- one source of truth
- secrets never enter Git
- machine-readable Atlas and human-readable indexes must agree
- IDE configuration is convenience/orchestration; CI and repository policy remain authoritative
- cross-language boundaries carry explicit contracts
- durable artifacts must be reachable or intentionally declared

## Version discipline
v0.6.0 adds CLI/harness orchestration, anti-orphan and anti-drift checks, polyglot engineering patterns, and research/evaluation guidance.

## Core indexes
- [Languages](languages/ATLAS.md)
- [Models and runtimes](models/README.md)
- [Integrations](integrations/README.md)
- [Systems](systems/README.md)
- [CLI engineering](docs/CLI-ENGINEERING.md)
- [Agent harness](systems/AGENT-HARNESS.md)
- [Research](research/PROGRAMMING-RESEARCH-2026.md)

## Architecture
MODEL.md -> atlas.yaml -> runtime/task/artifact routing -> language/integration/system -> editor/agent host -> Skills/Plugins/MCP/Connectors/APIs -> implementation -> verification/security/performance -> diff/provenance -> release

## Language families
Application/orchestration: Python, TypeScript.
Systems/infrastructure: Rust, Go, C, C++, Zig, Nim, V, Hare, Odin.
Data/accelerator/HPC: Julia, Mojo, Futhark, Chapel, CUDA.
Functional/correctness: Haskell, F#, Elixir, Gleam, Roc, Lean 4.
Language research: Carbon, BQN, Uiua.
Boundary/runtime: SQL, Bash, WebAssembly/WASI.
Quantum: Q#, Silq, Qiskit.

## Multi-language design
Use one language per meaningful responsibility, then connect components through the least expensive boundary that provides the needed isolation.

Typical shapes:
- Python host -> Rust/C++/Mojo native core or accelerator
- TypeScript product/API -> Go/Rust service
- Python/Julia research -> native or accelerator component
- local process -> bounded stdio/message schema
- service -> versioned RPC/message schema
- portable component -> WebAssembly/WASI

See [systems/POLYGLOT-ENGINEERING.md](systems/POLYGLOT-ENGINEERING.md).

## VS Code and OpenCode
VS Code is the interactive workbench for navigation, debugging, tests, Git, task orchestration, remote execution, and AI/MCP interaction.

OpenCode is the terminal-native agent/workspace layer for autonomous or long-running coding. Separate worktrees when writers operate concurrently.

## GitHub Actions
CI verifies the Atlas itself. Local CLI and VS Code provide rapid feedback; GitHub Actions provides repository-level repeatability.

## Efficiency
Optimize the complete reasoning path: fewer repeated tokens/tools + stronger contracts + reusable primitives + bounded resources + independent verification.
