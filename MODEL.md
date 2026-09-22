<!-- CODE-DEVELOPMENT MODEL CONTROL PLANE v0.5.3 -->
# MODEL.md

**Control plane version: 0.5.3**

Canonical model-aware operating layer for Claude, Cursor, OpenAI/Codex, OpenCode, Hermes, VS Code, and generic LLM providers.

## Read order
1. MODEL.md
2. docs/INDEX.md
3. atlas.yaml
4. active model/runtime adapter
5. exact language/integration/system guide
6. relevant pattern
7. implement -> verify -> diff -> record

## Hard invariants
- no unbounded resource, work, time, retry, queue, cache, recursion, network, storage, or autonomous-agent growth unless explicitly justified
- immutable-first state and explicit ownership of mutable state
- schema-first external boundaries
- explicit deadlines, cancellation, and shutdown
- least-privilege tools, credentials, paths, network, and repository access
- independent verification of AI-generated code
- reproducible and auditable changes
- rollback/snapshot capability for high-impact mutations
- one source of truth for important contracts, endpoints, versions, and policy
- contract files and machine-readable indexes must agree
- primary/official documentation preferred for capability claims
- secrets remain outside version control
- IDE tasks, launch configurations, and workspace settings are developer tooling, not a substitute for CI, repository policy, sandboxing, or production controls

Synchronization rule: if an invariant, route, security rule, verification requirement, or canonical runtime/tool role changes, update MODEL.md, VERSION, README.md, relevant index/pattern/adapter, and atlas.yaml in one commit.

## Code-to-route
Artifact extension -> language guide. Then route by issue signature.

Python: .py/.pyi
Rust: .rs
Go: .go
TypeScript: .ts/.tsx
C: .c/.h
C++: .cpp/.cc/.hpp
Zig: .zig
Mojo: .mojo
Julia: .jl
Elixir: .ex/.exs
Gleam: .gleam
Nim: .nim
V: .v
Odin: .odin
Haskell: .hs/.lhs
F#: .fs/.fsx
Chapel: .chpl
BQN: .bqn
Uiua: .ua
Lean: .lean
CUDA: .cu/.cuh
SQL: .sql
Bash: .sh/.bash
WASM: .wat/.wasm

Issue routing:
memory -> ownership/allocator/sanitizer
concurrency -> scheduler/channel/race tools
debugging -> VS Code debugger + language/runtime debugger
GPU -> kernel/profiler/memory-transfer analysis
endpoint -> schema/auth/timeout/idempotency
performance -> benchmark/profiler/workload
security -> static/dependency/secret scans
agent -> model router/narrow tools/sandbox/budget/audit

## Runtime adapters
Claude Code -> models/claude/README.md
Cursor -> models/cursor/README.md
OpenAI/Codex -> models/openai/README.md
OpenCode -> models/opencode/README.md
Hermes -> models/hermes/README.md
VS Code -> models/vscode/README.md
LLM/providers -> models/llm/README.md

## Context/tool policy
Use progressive disclosure and the smallest sufficient tool surface. Skills are procedures, MCP/connectors are capabilities, hooks/CI/policy/sandbox are enforcement, subagents isolate context, memory stores durable facts/decisions, and VS Code provides interactive inspection/orchestration.

Never let token optimization remove evidence, constraints, uncertainty, or requested detail.

## Versioning
Contract changes require synchronized versioned commits.
