# Code-Development

**Repository contract: v0.5.1**

Advanced, model-aware engineering atlas for programming languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, and verification.

> Read first: MODEL.md -> docs/INDEX.md -> atlas.yaml -> runtime adapter -> exact domain guide -> pattern -> example/prompt -> verification.

## Purpose
This is a practical engineering atlas. Every stack is scoped by purpose, fit, guarantees, tools, common mistakes, streamlining, learning direction, AI usage, and verification rather than popularity.

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

## Version discipline
v0.5.1 adds artifact-to-language routing and tighter contract consistency checks. Any future contract change must update all relevant surfaces in the same commit.

## Architecture
MODEL.md -> atlas.yaml -> runtime/task/artifact routing -> language/integration/system -> Skills/Plugins/MCP/Connectors/APIs -> implementation -> verification/security/performance -> diff/provenance -> release

## Core indexes
- languages/ATLAS.md
- atlas.yaml
- models/README.md
- prompts/README.md
- integrations/AI-CAPABILITIES.md
- systems/STORAGE-STATE.md
- systems/BACKEND-ARCHITECTURE.md
- patterns/CONTEXT-EFFICIENCY.md
- patterns/COGNITIVE-CODE-DESIGN.md
- docs/CONSISTENCY.md

## Language families
Application/orchestration: Python, TypeScript.
Systems/infrastructure: Rust, Go, C, C++, Zig, Nim, V, Hare, Odin.
Data/accelerator/HPC: Julia, Mojo, Futhark, Chapel, CUDA.
Functional/correctness: Haskell, F#, Elixir, Gleam, Roc, Lean 4.
Language research: Carbon, BQN, Uiua.
Boundary/runtime: SQL, Bash, WebAssembly/WASI.
Quantum: Q#, Silq, Qiskit.

Odin is placed under data-oriented native systems, game/graphics, and simulation.

## Efficiency
Optimize the whole reasoning path: less duplicated context + narrower tools + stronger contracts + reusable primitives + bounded resources + independent verification.