<!-- CODE-DEVELOPMENT MODEL CONTROL PLANE v0.3.0 -->
# MODEL.md

**Control plane version: 0.3.0**

This is the primary model-aware operating layer for Code-Development. It adapts the repository to Claude, Cursor, OpenAI/Codex, OpenCode, Hermes, and generic LLM providers without making any single product the repository identity.

## Read order
1. Read `MODEL.md`.
2. Read `docs/INDEX.md`.
3. Read the matching model adapter under `models/`.
4. Read the relevant language, integration, system, and pattern guides.
5. Run focused verification while iterating.
6. Run the complete applicable verification loop before completion.

## Invariants
- no unbounded resource, work, time, retry, queue, cache, recursion, network, or autonomous-agent growth unless explicitly justified
- immutable-first state and explicit ownership of mutable state
- schema-first external boundaries
- explicit deadlines and cancellation
- least-privilege tools, credentials, paths, network, and repository access
- independent verification of AI-generated code
- reproducible and auditable changes
- rollback or snapshot capability for high-impact mutations
- primary/official documentation preferred for capability claims
- secrets stay outside version control

Any invariant change must update `MODEL.md`, `VERSION`, the README contract, the affected pattern/index, and affected model adapters in the same commit.

## Model routing
| Runtime | Use | Adapter |
|---|---|---|
| Claude Code | agentic coding, Skills, hooks, MCP, subagents | `models/claude/README.md` |
| Cursor | editor-first AI coding, rules, skills, MCP | `models/cursor/README.md` |
| OpenAI/Codex | reasoning, coding, tools, MCP, connectors, API orchestration | `models/openai/README.md` |
| OpenCode | provider-flexible terminal coding | `models/opencode/README.md` |
| Hermes | persistent agent, messaging bots, memory, skills, provider switching | `models/hermes/README.md` |
| LLM | provider credentials, endpoints, normalized routing | `models/llm/README.md` |

## Capability routing
Route by capability, not brand:
- navigation -> language server/symbol search/focused retrieval
- code generation -> model + typed boundaries + direct repo tools
- broad refactor -> strong reasoning + isolated worktree
- research -> isolated context/subagent + evidence-backed summary
- repetitive transformation -> smaller/faster model + deterministic generator
- security -> static analysis/security tools + reasoning review
- external service -> narrow API/MCP/connector
- deterministic enforcement -> hook, policy, CI, or sandbox
- durable knowledge -> versioned document/memory record

## Context and token policy
Context is a resource. Reduce repeated information, not useful information.
Prefer focused retrieval, stable file anchors, progressive disclosure, compact structured handoffs, deterministic tool catalogs, and isolated subagents for high-volume exploration.
Keep always-loaded directives short. Put procedures into skills/docs. Do not paste full repositories or raw tool logs into every context window.
Do not optimize token count by deleting constraints, evidence, uncertainty, verification results, or requested output detail.

## Tool policy
Use the smallest sufficient capability: native repo/language tools -> focused CLI/API -> MCP/connector -> broad shell/browser automation.
Broad capabilities require stronger policy and verification.

## Skills, plugins, MCP, connectors
Use Skills for reusable procedures/reference, hooks for deterministic lifecycle enforcement, plugins for coherent capability bundles, MCP for external tools/resources, connectors for maintained service integrations, and subagents for context isolation.
Keep schemas narrow, outputs bounded, side effects explicit, credentials least-privilege, and destructive operations approval-gated.

## Memory
Separate working context, durable facts, procedures, model configuration, and secrets.
Store durable facts/decisions with scope, provenance, and version. Never store API keys or bearer tokens in ordinary memory.

## Code efficiency
Optimize semantic density, not raw line count.
Good compression: table-driven logic, declarative configuration, shared validators, generated repetitive surfaces, reusable bounded executors, common error models, and one source of truth.
Bad compression: clever one-liners, hidden retries, hidden I/O, global mutable state, reflection-heavy magic, and mega-functions.

## Completion
A model cannot declare success because code looks correct or compiles. Completion requires the applicable formatter, linter, type checker, tests, security checks, dependency checks, and final diff review.

## Versioning
The repository version tracks the behavioral/instructional contract. Every change to invariants, routing, security policy, tool policy, or verification requirements increments the version and changes the related contract files together.