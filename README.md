# Code-Development

**Repository contract: v0.5.4**

Advanced, model-aware engineering atlas for programming languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, and verification.

> Read first: MODEL.md -> docs/INDEX.md -> atlas.yaml -> runtime/model adapter -> exact domain guide -> pattern -> example/prompt -> verification.

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

## Version discipline
v0.5.4 adds an authoritative GitHub Actions contract-check workflow and keeps IDE validation subordinate to CI.

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

## Atlas
Use languages/ATLAS.md for workload selection and each language README for implementation details.

Odin is placed under data-oriented native systems, game/graphics, and simulation.

## VS Code and OpenCode
VS Code is the interactive workbench for source navigation, breakpoints, stack/variable inspection, test/debug loops, Git diffs, task orchestration, remote environments, and AI/MCP interaction.

OpenCode remains the terminal-native agent/workspace layer for autonomous or long-running coding. Prefer separate Git worktrees when both are editing different tasks; do not use simultaneous writers on the same worktree accidentally.

## GitHub Actions
The repository uses CI to verify its own control contract. IDE tasks provide local feedback; Actions provide repository-level repeatability for pushes and pull requests.

## Efficiency
Optimize the complete reasoning path: fewer repeated tokens/tools + stronger contracts + reusable primitives + bounded resources + independent verification.
