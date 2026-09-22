# Code-Development

**Repository contract: v0.3.1**

Advanced programming languages, AI coding systems, developer tooling, APIs, Git/GitHub, MCP/connectors/Skills/plugins, data and research systems, performance, security, reliability, and high-assurance engineering.

> **Read first:** `MODEL.md` -> `docs/INDEX.md` -> the matching model adapter -> the relevant language/integration/system guide -> applicable pattern -> verification.

## What this repository is
This is a technical engineering reference and builder system, not a universal ranking of languages or packages. Each technology is scoped by purpose, when to use it, what guarantees it provides, important limitations/defaults, how to verify it, and how it fits AI-assisted development.

## Contract
- No unbounded resource, work, time, retry, queue, cache, recursion, network, or autonomous-agent growth unless explicitly justified.
- Immutable-first state and explicit ownership of mutable state.
- Schema-first external boundaries.
- Explicit deadlines and cancellation.
- Least-privilege tools, credentials, paths, network, and GitHub access.
- Independent verification of AI-generated code.
- Reproducible and auditable changes.
- Rollback or snapshot capability for high-impact mutations.
- Secrets stay outside version control.

## Version discipline
**v0.3.1** records the model-control refactor plus its contract synchronization. When a hard invariant changes, update `MODEL.md`, `VERSION`, this README contract, the affected index/pattern/adapters, and commit them together.

## Control plane
- [MODEL.md](MODEL.md) — dynamic model-aware repository contract
- [models/](models/README.md) — Claude, Cursor, OpenAI/Codex, OpenCode, Hermes, provider/LLM routing
- [docs/INDEX.md](docs/INDEX.md) — navigation/routing
- [docs/VERSIONING.md](docs/VERSIONING.md) — contract-versioning rule

## Repository map
```text
MODEL.md                         model control plane
models/                          model adapters + LLM/provider routing
languages/                       language-specific engineering
integrations/                    GitHub, webhooks, endpoints, MCP/connectors
systems/                         data, research, bots, operations
docs/                            indexes, packages, verification, architecture
patterns/                        reusable engineering guarantees
examples/                        small executable patterns
.github/                         platform-specific instructions
```

## Language system
| Domain | Primary role |
|---|---|
| Python | AI, orchestration, data, automation |
| Rust | systems, safety, performance, security |
| Go | services, concurrency, infrastructure |
| TypeScript/JS | AI applications, APIs, tooling |
| C++ | native, HPC, graphics |
| Zig | low-level tooling, explicit allocation |
| Mojo | AI kernels, GPU/HPC exploration |
| Julia | scientific/numerical computing |
| Elixir | fault tolerance/distribution |
| Gleam | typed BEAM systems |
| Carbon | experimental C++ successor research |
| Roc | experimental functional systems |
| Odin | data-oriented native systems |
| Futhark | data-parallel GPU/CPU kernels |
| Hare | minimalist systems |
| Lean 4 | formal verification |
| Q# / Silq / Qiskit | quantum programming and tooling |

## AI capability system
```text
model
  ↓
context + capability routing
  ↓
language/repo tooling
  ↓
Skills / plugins / MCP / connectors
  ↓
implementation
  ↓
tests + static analysis + security
  ↓
diff + policy review
  ↓
commit/release
```

Use the smallest sufficient model, tool surface, context, and runtime. Reduce repetition, not useful information.

## Engineering pillars
### No Unbounded
Explicit limits for memory, tasks, goroutines, queues, batches, caches, retries, recursion, JSON, HTTP bodies, pagination, streams, logs, and agent loops.

### Anti-Mutation
Prevent -> detect -> isolate -> version -> recover.

### Schema First
External JSON, webhooks, API responses, model outputs, and tool outputs are untrusted until they pass the appropriate validation/authorization boundary.

### Efficiency
Prefer focused retrieval, stable indexes, narrow tool schemas, bounded tool results, deterministic interfaces, reusable primitives, data-driven logic, and semantic code compression.

### Verification
Generated code is incomplete until the applicable formatting, linting, type checking, tests, security/dependency checks, and diff review pass.

## Integration surface
- Git worktrees for isolated parallel implementation and experiments.
- GitHub CLI/API/GraphQL, Actions, Apps, rulesets, permissions, and automation.
- Signed webhook ingestion with replay/idempotency and backpressure controls.
- Endpoint contracts, health/readiness, rate limits, idempotency, and versioning.
- MCP, connectors, plugins, Skills, subagents, and memory as separate capability layers.

## Model/provider separation
`models/llm/` contains provider references and environment-variable names only. It is a routing/configuration layer, not a place for actual API keys.

Provider/model/endpoint details are time-sensitive and must be verified before operational use.

## Design principle
Optimize for **semantic density and guarantees**, not the fewest lines of code. Shorter code is valuable when it removes duplication or accidental complexity; longer code is valuable when it makes ownership, failure, limits, and side effects explicit.