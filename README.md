# Code-Development

**Repository contract: v0.5.0**

Advanced, model-aware engineering atlas for programming languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, and verification.

> **Read first:** `MODEL.md` -> `docs/INDEX.md` -> `atlas.yaml` -> model adapter -> language/integration/system guide -> pattern -> example/prompt -> verification.

## What this repo is
A practical engineering atlas. Technologies are organized by **purpose, fit, guarantees, limits, tradeoffs, common mistakes, streamlining, learning path, AI usage, and verification** rather than popularity.

## Repository contract
- No unbounded resource/work/time/retry/queue/cache/recursion/network/storage/agent growth without explicit justification.
- Immutable-first state; explicit ownership of mutable state.
- Schema-first external boundaries.
- Explicit deadlines, cancellation, and shutdown.
- Least privilege.
- Independent verification.
- Reproducible/auditable changes.
- Rollback/snapshot for high-impact mutation.
- One source of truth.
- No secrets in Git.
- Canonical docs and machine-readable metadata must agree.

## Version discipline
v0.5.0 adds a machine-readable Atlas, systems/boundary language tier, prompt templates, and repository consistency checks. Any future contract change must update all relevant surfaces in the same commit.

## Architecture
```text
MODEL.md
  ↓
runtime adapter
  ↓
atlas.yaml + routing
  ↓
language / tool / system
  ↓
Skills | Plugins | MCP | Connectors | APIs
  ↓
implementation
  ↓
tests | static analysis | security | profiling
  ↓
diff | policy | provenance
  ↓
commit | release
```

## Core indexes
- [Language Atlas](languages/ATLAS.md)
- [Machine-readable Atlas](atlas.yaml)
- [Model layer](models/README.md)
- [Prompt Atlas](prompts/README.md)
- [Tool/capability Atlas](integrations/AI-CAPABILITIES.md)
- [GitHub tools](integrations/GITHUB-TOOLS.md)
- [Storage/state](systems/STORAGE-STATE.md)
- [Backend architecture](systems/BACKEND-ARCHITECTURE.md)
- [Context efficiency](patterns/CONTEXT-EFFICIENCY.md)
- [Cognitive code design](patterns/COGNITIVE-CODE-DESIGN.md)
- [Contract/versioning](docs/VERSIONING.md)

## Language classes
### Application / orchestration
Python, TypeScript

### Systems / infrastructure
Rust, Go, C++, Zig, Nim, V, Hare, Odin

### Data / numerical / accelerator
Julia, Mojo, Futhark, Chapel, CUDA

### Functional / correctness
Haskell, F#, Elixir, Gleam, Roc, Lean 4

### Experimental language design
Carbon, BQN, Uiua

### Quantum
Q#, Silq, Qiskit

### Boundary / foundational
C, SQL, Bash, WebAssembly/WASI

## Odin placement
Odin is cataloged as a **data-oriented native systems** language with strong game/graphics/simulation fit. It is not treated as a universal C++ replacement; its value here is explicit data layout and native simplicity.

## Efficiency principle
Do not optimize token count, source line count, or tool count independently. Optimize the whole reasoning path:
`less duplicated context + narrower tools + stronger contracts + reusable primitives + independent verification`.

## Source discipline
Use official specifications/docs and primary research for capability claims. Treat experimental status, package maturity, model availability, pricing, context limits, endpoints, and benchmarks as changeable.