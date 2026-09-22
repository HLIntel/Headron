# MODEL.md

**Control plane version: 0.7.0**

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
- no unbounded resource/work/time/retry/queue/cache/recursion/network/storage/agent growth without explicit justification
- immutable-first state and explicit ownership of mutable state
- schema-first external boundaries
- explicit deadlines and cancellation
- least-privilege tools, credentials, paths, network, and repository access
- independent verification of AI-generated code
- reproducible and auditable changes
- rollback/snapshot capability for high-impact mutation
- one source of truth for important contracts, endpoints, versions, and policy
- contract files and machine-readable indexes must agree
- secrets remain outside version control
- IDE tasks are convenience, not repository enforcement
- cross-language boundaries require ownership/schema/compatibility/failure/observability contracts
- durable artifacts need a discoverable owner or reference path
- MCP is task-scoped; native language tooling remains authoritative

Synchronization rule: if an invariant, route, security rule, verification requirement, runtime/tool role, or canonical structure changes, update MODEL.md, VERSION, README.md, relevant index/pattern/adapter, and atlas.yaml in one commit.

## Runtime adapters
Claude -> models/claude/README.md
Cursor -> models/cursor/README.md
OpenAI/Codex -> models/openai/README.md
OpenCode -> models/opencode/README.md
Hermes -> models/hermes/README.md
VS Code -> models/vscode/README.md
LLM/providers -> models/llm/README.md

## Tool routing
CLI/native tools -> deterministic local operations and language/runtime authority
VS Code -> interactive source navigation, debugger, tests, tasks, remote development
MCP -> external or specialized capabilities
GitHub MCP -> GitHub repo, PR, issue, Actions, security context
Serena -> semantic code navigation/editing across supported LSP languages
Playwright -> browser/UI automation and integration testing
Context7 -> current library/framework documentation
DBHub -> bounded database/schema/query access
Semgrep MCP -> deterministic security scanning through the Semgrep CLI

## Code-to-route
Python .py/.pyi
Rust .rs
Go .go
TypeScript .ts/.tsx
C .c/.h
C++ .cpp/.cc/.hpp
Zig .zig
Mojo .mojo
Julia .jl
Elixir .ex/.exs
Gleam .gleam
Nim .nim
V .v
Odin .odin
Hare .ha
Futhark .fut
Haskell .hs/.lhs
F# .fs/.fsx
Chapel .chpl
BQN .bqn
Uiua .ua
Lean .lean
Carbon .carbon
Roc .roc
Q# .qs
CUDA .cu/.cuh
SQL .sql
Bash .sh/.bash
WASM .wat/.wasm

## Issue routing
memory -> ownership/allocator/sanitizer
concurrency -> scheduler/channel/race tools
debugging -> VS Code debugger + runtime debugger
GPU -> kernel/profiler/memory-transfer analysis
security -> static/dependency/secret scans
polyglot -> schema/interop/compatibility/integration testing
drift -> links/routes/orphans/dependencies/environment
MCP -> integrations/MCP-LANGUAGE-MATRIX.md + integrations/MCP-PROFILES.md

Never add a duplicate tool merely because it is available. Use progressive disclosure and the smallest sufficient context/tool surface.
