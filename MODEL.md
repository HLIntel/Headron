<!-- CODE-DEVELOPMENT MODEL CONTROL PLANE v0.4.0 -->
# MODEL.md

**Control plane version: 0.4.0**

This is the canonical model-aware operating layer for Code-Development. It adapts the same engineering contract to Claude, Cursor, OpenAI/Codex, OpenCode, Hermes, and generic LLM providers without making any one product the repository identity.

## Read order
1. Read `MODEL.md`.
2. Read `docs/INDEX.md`.
3. Read the adapter for the active runtime.
4. Route the task through the Atlas.
5. Read only the relevant language/integration/system/pattern documents.
6. Execute, verify, inspect the diff, then commit.

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
- primary/official documentation preferred for capability claims
- secrets remain outside version control

**Invariant synchronization rule:** whenever an invariant is added, removed, or materially changed, update this file, `VERSION`, README contract text, the affected index/pattern/adapter, and the version in the same commit.

## Runtime adapters
| Runtime | Primary use | Adapter |
|---|---|---|
| Claude Code | agentic coding, Skills, hooks, MCP, subagents | `models/claude/README.md` |
| Cursor | editor-first coding, scoped rules, Skills, MCP | `models/cursor/README.md` |
| OpenAI/Codex | coding/reasoning, tools, MCP, connectors, API orchestration | `models/openai/README.md` |
| OpenCode | provider-flexible terminal coding | `models/opencode/README.md` |
| Hermes | persistent agents, bots, Skills, memory, model switching | `models/hermes/README.md` |
| LLM | provider endpoints, credentials, routing metadata | `models/llm/README.md` |

## Capability routing
| Need | Route |
|---|---|
| find code | index -> symbol search -> focused file read |
| understand architecture | Atlas -> relevant language/system docs -> ADR |
| mechanical edit | fast model + direct repo tools + targeted verification |
| cross-file refactor | strong reasoning + dedicated worktree + diff review |
| broad research | isolated subagent/context + evidence-backed summary |
| repetitive generation | schema/table/generator + lower-cost model |
| security review | static analysis + dependency/secret scanning + reviewer model |
| external data | narrow API/client/MCP/connector + schema validation |
| deterministic guardrail | hook/policy/CI/sandbox |
| long-lived knowledge | versioned doc/memory record |
| performance | benchmark + profiler + workload-specific language/runtime |

## Context and token policy
Context is a budget, not a dump.

Use progressive disclosure: invariant -> index -> relevant section -> implementation -> verification.

Prefer focused retrieval, stable headings, line ranges, symbol references, compact structured handoffs, and diff-based review.

Do not save tokens by removing constraints, evidence, uncertainty, verification results, or requested output detail.

## Tool hierarchy
Use the smallest sufficient capability:
`native repository/language tools -> focused CLI/API -> MCP/connector -> broad shell/browser automation`

Use broad tools when the narrower layer cannot complete the job.

## Skills / plugins / MCP / connectors / subagents
- Skills: reusable procedures and deep reference, loaded on demand.
- Plugins: coherent bundles of capabilities.
- MCP: external tools/resources with schemas, authorization, bounded results, and explicit side effects.
- Connectors: maintained external-service integrations with scoped permissions.
- Hooks: deterministic lifecycle enforcement.
- Subagents: context isolation and parallel exploration.

Do not duplicate the same procedure across all layers. One canonical source plus thin adapters is preferred.

## Memory
Separate working context, durable facts, procedural Skills, model configuration, and secrets.

Durable memory should contain compact facts or decisions with scope, provenance, and version. Do not use memory as a transcript warehouse.

## Code efficiency
Optimize semantic density, not minimum line count.

Good compression: data-driven dispatch, shared contracts, common validators, generators for repetitive code, bounded-executor primitives, centralized configuration, and explicit types.

Bad compression: clever one-liners, hidden I/O, hidden retry loops, global mutable state, reflection-heavy magic, or abstractions that increase navigation cost.

## Dynamic language switching
Switch languages at explicit boundaries rather than rewriting entire systems to chase a theoretical speedup.

Typical boundary:
`Python orchestration -> Rust/C++/Mojo/Futhark kernel -> typed result`

or:
`TypeScript/Go API -> language-specific worker -> schema -> service boundary`.

The language Atlas defines when these boundaries are justified.