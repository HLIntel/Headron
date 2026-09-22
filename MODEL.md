<!-- CODE-DEVELOPMENT MODEL CONTROL PLANE v0.5.0 -->
# MODEL.md

**Control plane version: 0.5.0**

Canonical model-aware operating layer for Claude, Cursor, OpenAI/Codex, OpenCode, Hermes, and generic LLM providers.

## Read order
1. Read `MODEL.md`.
2. Read `docs/INDEX.md`.
3. Read `atlas.yaml` and the relevant model adapter.
4. Read the specific language/integration/system guide.
5. Read applicable patterns.
6. Implement in an isolated scope when risk/size warrants it.
7. Verify, inspect diff, and record the result.

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
- contract files and generated/derived indexes must agree
- primary/official documentation preferred for capability claims
- secrets remain outside version control

**Invariant synchronization rule:** if an invariant changes, the same commit must update `MODEL.md`, `VERSION`, `README.md`, the relevant pattern/index/adapter, and any machine-readable manifest or consistency check.

## Model routing
| Runtime | Primary use | Adapter |
|---|---|---|
| Claude Code | agentic coding, Skills, hooks, MCP, subagents | `models/claude/README.md` |
| Cursor | editor-first coding, rules, Skills, MCP | `models/cursor/README.md` |
| OpenAI/Codex | reasoning, coding, tools, MCP, connectors, API orchestration | `models/openai/README.md` |
| OpenCode | provider-flexible terminal coding | `models/opencode/README.md` |
| Hermes | persistent agents, bots, Skills, memory, provider switching | `models/hermes/README.md` |
| LLM | provider endpoints, credential references, routing metadata | `models/llm/README.md` |

## Capability routing
- navigation -> `docs/INDEX.md` -> symbol/search -> focused files
- task classification -> `atlas.yaml` capability tags
- implementation -> model role + language guide
- broad refactor -> strong reasoning + dedicated worktree
- research -> isolated context/subagent + provenance
- repetitive transformation -> generator/table/schema + fast model
- security -> scanners + verifier/reviewer model
- performance -> benchmark/profiler + specialized language when justified
- external service -> narrow endpoint/API/MCP/connector
- deterministic guardrail -> code/hook/policy/CI/sandbox
- durable fact/decision -> versioned document or memory record

## Context policy
Context is a bounded resource. Use progressive disclosure and avoid repeating stable material.

Prefer index -> focused file/symbol -> relevant lines -> implementation -> diff.

Use subagents for broad read-heavy investigation; pass compact evidence-backed results back to the parent.

Keep always-loaded instructions short. Put deep procedures into Skills/docs.

## Tool policy
Use the smallest sufficient capability: native repository/language tools -> focused CLI/API -> MCP/connector -> broad shell/browser automation.

Tool schemas should be narrow. Results should be bounded. Side effects should be explicit. Destructive actions should be approval-gated.

## Skills / plugins / MCP / connectors
Skills are procedures; plugins are coherent capability bundles; MCP exposes external tools/resources; connectors expose maintained external services; hooks enforce deterministic lifecycle policies; subagents isolate context and responsibility.

Do not duplicate a canonical procedure across several layers. Thin adapters may point to one source of truth.

## Memory
Separate working context, durable knowledge, Skills/procedures, model/provider configuration, and secrets.

Durable memory should preserve facts/decisions with scope, provenance, and version. Never store credentials.

## Code efficiency
Optimize semantic density, locality, and reusable guarantees rather than line count.

Prefer data-driven dispatch, schemas, common validators, bounded executors, centralized configuration, generated repetitive code, and explicit side-effect boundaries.

Avoid clever compression that hides control flow, ownership, retries, I/O, or resource growth.

## Language switching
Switch languages at explicit contracts. Keep orchestration in the productive host language when practical and isolate measured hot paths or specialized capabilities behind typed interfaces.

Example: `Python -> Rust/Mojo/Futhark kernel -> schema -> Python`.

## Completion
Compiles is not complete. Completion requires applicable formatting, linting, type checking, tests, security/dependency checks, resource-bound review, and final diff review.

## Versioning
Version tracks the behavioral/instructional contract. Contract changes require synchronized versioned commits.