# Headron Index

<!-- BEGIN generated: glance (python scripts/atlas.py index --write) -->
**40** languages · **60** extensions · **64** gates · **10** runtimes · **122** failure shapes · **46** success moves · **48** invariants · **94** instruments · **353** agreement edges · **2** dependency
<!-- END generated: glance -->

## Use it

Start with the task below and follow the linked page; the index is a map, not a reading list.

| Need | Start |
|---|---|
| install, then wire a repository | [README quickstart](../README.md#quickstart) |
| using this atlas from another repository | [CONSUMING.md](CONSUMING.md) |
| verification: gates, verdicts, receipts | [VERIFY.md](VERIFY.md) |
| what each instrument proves | [instruments table](INSTRUMENTS.md) · [certification, per check](CERTIFICATION.md) |
| interpret reported measurements | [measured evidence](../README.md#what-it-measurably-buys) |
| the `.headron` task surface | [HEADRON-LANGUAGE.md](HEADRON-LANGUAGE.md) |
| security policy and platform controls | [SECURITY.md](../SECURITY.md) · [github-controls.json](../config/github-controls.json) |
| version contract | [VERSIONING.md](VERSIONING.md) |
| licence | [LICENSE](../LICENSE) |

## Agents and integrations

| Need | Start |
|---|---|
| machine-readable entry point | [llms.txt](../llms.txt) · [CLAUDE.md](../CLAUDE.md) · [AGENTS.md](../AGENTS.md) — one body, three conventions, all generated |
| model control/routing | [MODEL.md](../MODEL.md) |
| agent engineering | [models/agents](../models/agents/README.md) |
| integrations | [integrations](../integrations/HEADRON.md) |
| MCP profiles and language matrix | [MCP-PROFILES.md](../integrations/MCP-PROFILES.md) · [MCP-LANGUAGE-MATRIX.md](../integrations/MCP-LANGUAGE-MATRIX.md) |
| tool orchestration | [TOOL-ORCHESTRATION.md](wiki/TOOL-ORCHESTRATION.md) |
| CLI/harness | [CLI-ENGINEERING.md](CLI-ENGINEERING.md) |

## Languages

| Need | Start |
|---|---|
| language selection | [languages/ATLAS.md](../languages/ATLAS.md) |
| language packs and their contract | [languages/README.md](../languages/README.md) · [operating cards](../languages/README.md#operating-cards) |
| tool manifest contract | [languages/PACK-TOOLS-SPEC.md](../languages/PACK-TOOLS-SPEC.md) · [tools.schema.json](../tools/tools.schema.json) |
| code-specific routing | [CODE-ROUTING.md](wiki/CODE-ROUTING.md) |
| language operations | [LANGUAGE-OPERATIONS.md](wiki/LANGUAGE-OPERATIONS.md) |
| JSON | [JSON.md](JSON.md) |

## How it is built

| Need | Start |
|---|---|
| code-development wiki | [docs/wiki/README.md](wiki/README.md) |
| systems | [systems](systems/README.md) |
| concepts paired with mechanisms | [ENGINEERING-CONCEPTS.md](ENGINEERING-CONCEPTS.md) |
| consistency | [CONSISTENCY.md](CONSISTENCY.md) |
| dependencies: closure, micro-deps, wiring | [DEPENDENCIES.md](DEPENDENCIES.md) |
| encoding & compression: adopt, measure, refuse | [ENCODING.md](ENCODING.md) |
| Git/worktrees | [GIT-WORKTREES.md](GIT-WORKTREES.md) |
| symlinks/paths | [SYMLINKS-PATHS.md](SYMLINKS-PATHS.md) |
| entry and landing: short front, same verdict | [ENTRY-PLAN.md](ENTRY-PLAN.md) |
| reduce context and document duplication | [CONTEXT-EFFICIENCY.md](patterns/CONTEXT-EFFICIENCY.md) · [ENCODING.md](ENCODING.md) |
| GitHub backend, control plane, finalization | [GITHUB-BACKEND.md](GITHUB-BACKEND.md) · [GITHUB-FINALIZATION.md](GITHUB-FINALIZATION.md) |
| OpenSSF Scorecard improvement plan | [SCORECARD-IMPROVEMENT.md](SCORECARD-IMPROVEMENT.md) |
| product strategy, pricing, deployment | [PRODUCT-STRATEGY.md](PRODUCT-STRATEGY.md) |
| retired pages, kept so old links resolve | [DECISIONS.md](DECISIONS.md) · [PACKAGE-CATALOG.md](PACKAGE-CATALOG.md) · [SECURITY-HYGIENE.md](SECURITY-HYGIENE.md) |

## Assurance patterns

- [No Unbounded](patterns/NO-UNBOUNDED.md)
- [Anti-Mutation](patterns/ANTI-MUTATION.md)
- [Anti-Drift](patterns/ANTI-DRIFT.md)
- [Anti-Orphans](patterns/ANTI-ORPHANS.md)
- [Boundary Breakage](patterns/BOUNDARY-BREAKAGE.md)
- [Anti-Blobs](patterns/ANTI-BLOBS.md)
- [High-Assurance Workflow](patterns/HIGH-ASSURANCE-WORKFLOW.md)
- [Context Efficiency](patterns/CONTEXT-EFFICIENCY.md)
- [Cognitive Code Design](patterns/COGNITIVE-CODE-DESIGN.md)

**This page is a convenience, not the reachability guarantee.** `atlas.py check` fails on a broken
link and on any durable document no other document reaches, so a file missing from this table is
still reachable — but a link here that points nowhere fails the contract like any other.
