# Code-Development

**Repository contract: v0.4.0**

An advanced, model-aware engineering atlas for programming languages, AI coding systems, developer tooling, APIs, Git/GitHub, MCP/connectors/Skills/plugins, data/research systems, storage, backends, performance, security, reliability, and verification.

> **Read first:** `MODEL.md` -> `docs/INDEX.md` -> `ATLAS`/relevant model adapter -> language/integration/system guide -> applicable pattern -> examples -> verification.

## Purpose
This is not a universal language or package ranking. It is a practical engineering atlas. Every language/tool is scoped by purpose, when it fits, what it is good at, what it makes easier, what it makes harder, common failure modes, how to streamline it, what to learn next, what to avoid, and how an AI coding system should use it.

## Contract
- No unbounded growth without explicit justification.
- Immutable-first state and explicit ownership of mutable state.
- Schema-first external boundaries.
- Explicit deadlines, cancellation, and shutdown.
- Least privilege.
- Independent verification.
- Reproducible/auditable changes.
- Rollback for high-impact mutations.
- One source of truth.
- No secrets in Git.

## Version discipline
**v0.4.0** introduces the standardized language stack format, cross-language Atlas, dynamic routing layer, storage/backend design layer, prompt patterns, and expanded language coverage.

Changing a hard invariant requires a synchronized versioned commit across `MODEL.md`, `VERSION`, README, affected docs, patterns, and model adapters.

## Architecture
```text
MODEL.md
   ↓
model runtime adapter
   ↓
DYNAMIC ROUTER
   ↓
language / tool / system selection
   ↓
Skills | Plugins | MCP | Connectors | APIs
   ↓
implementation
   ↓
verification + security + profiling
   ↓
diff / policy review
   ↓
commit / release
```

## Major layers
- [Language Atlas](languages/ATLAS.md)
- [Model layer](models/README.md)
- [Tooling and capabilities](integrations/AI-CAPABILITIES.md)
- [GitHub engineering](integrations/GITHUB.md)
- [Endpoint engineering](integrations/ENDPOINTS.md)
- [Storage and state](systems/STORAGE-STATE.md)
- [Backend architecture](systems/BACKEND-ARCHITECTURE.md)
- [Data/research/bots](systems/DATA-RESEARCH-BOTS.md)
- [Operations/uptime](systems/OPERATIONS-UPTIME.md)
- [Context efficiency](patterns/CONTEXT-EFFICIENCY.md)
- [Cognitive code design](patterns/COGNITIVE-CODE-DESIGN.md)
- [No Unbounded](patterns/NO-UNBOUNDED.md)
- [Anti-Mutation](patterns/ANTI-MUTATION.md)

## Versioned contract
The README, `MODEL.md`, `VERSION`, and relevant adapter/pattern/index are intentionally redundant at the top level so model runtimes that only inspect one entry point still see the current contract.

## Source discipline
Use official specifications, official language documentation, official project repositories, and primary research for capability claims. Provider/model availability, pricing, context limits, and endpoints are time-sensitive.