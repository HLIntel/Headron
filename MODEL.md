<!-- CODE-DEVELOPMENT MODEL CONTROL PLANE v0.5.1 -->
# MODEL.md

**Control plane version: 0.5.1**

Canonical model-aware operating layer for Claude, Cursor, OpenAI/Codex, OpenCode, Hermes, and generic LLM providers.

## Read order
1. MODEL.md
2. docs/INDEX.md
3. atlas.yaml
4. active model adapter
5. exact language/integration/system guide
6. relevant patterns
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

Synchronization rule: when an invariant, route, security rule, or verification requirement changes, update MODEL.md, VERSION, README.md, the relevant index/pattern/adapter, and atlas.yaml in the same commit.

## Code-to-route
Route by artifact when possible:
- .py/.pyi -> python
- .rs -> rust
- .go -> go
- .ts/.tsx -> typescript
- .c/.h -> c
- .cpp/.cc/.hpp -> cpp
- .zig -> zig
- .mojo -> mojo
- .jl -> julia
- .ex/.exs -> elixir
- .gleam -> gleam
- .nim -> nim
- .v -> v
- .odin -> odin
- .hs/.lhs -> haskell
- .fs/.fsx -> fsharp
- .chpl -> chapel
- .bqn -> bqn
- .ua -> uiua
- .lean -> lean4
- .cu/.cuh -> cuda
- .sql -> sql
- .sh/.bash -> bash
- .wat/.wasm -> webassembly

Then route by issue signature: memory -> ownership/allocator/sanitizer; concurrency -> scheduler/channel/race tools; endpoint -> schema/auth/timeout/idempotency; performance -> benchmark/profiler; security -> static/dependency/secret scans.

## Runtime adapters
| Runtime | Adapter |
|---|---|
| Claude Code | models/claude/README.md |
| Cursor | models/cursor/README.md |
| OpenAI/Codex | models/openai/README.md |
| OpenCode | models/opencode/README.md |
| Hermes | models/hermes/README.md |
| LLM/providers | models/llm/README.md |

Use model role based on uncertainty and verification need, not brand alone.

## Context/tool policy
Use progressive disclosure. Prefer focused retrieval and narrow tools. Skills are procedures; MCP/connectors are capabilities; hooks/CI/policy/sandboxing are enforcement; subagents isolate context; memory stores durable facts/decisions.

Do not let token optimization remove evidence, uncertainty, constraints, or requested detail.

## Versioning
Contract changes require synchronized versioned commits.