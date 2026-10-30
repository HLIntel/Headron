# Headron Index

<!-- BEGIN generated: glance (python scripts/atlas.py index --write) -->
**40** languages · **60** extensions · **64** gates · **10** runtimes · **122** failure shapes · **46** success moves · **48** invariants · **94** instruments · **353** agreement edges · **2** dependency
<!-- END generated: glance -->

| Need | Start |
|---|---|
| model control/routing | [MODEL.md](../MODEL.md) |
| code-development wiki | [docs/wiki/README.md](wiki/README.md) |
| code-specific routing | [CODE-ROUTING.md](wiki/CODE-ROUTING.md) |
| tool orchestration | [TOOL-ORCHESTRATION.md](wiki/TOOL-ORCHESTRATION.md) |
| language operations | [LANGUAGE-OPERATIONS.md](wiki/LANGUAGE-OPERATIONS.md) |
| language packs | [languages/README.md](../languages/README.md) |
| language pack contract | [languages/README.md](../languages/README.md#operating-cards) |
| the `.headron` task surface | [HEADRON-LANGUAGE.md](HEADRON-LANGUAGE.md) |
| tool manifest contract | [languages/PACK-TOOLS-SPEC.md](../languages/PACK-TOOLS-SPEC.md) · [tools.schema.json](../tools/tools.schema.json) |
| GitHub backend/control plane | [GITHUB-BACKEND.md](GITHUB-BACKEND.md) |
| GitHub finalization | [GITHUB-FINALIZATION.md](GITHUB-FINALIZATION.md) |
| language selection | [languages/ATLAS.md](../languages/ATLAS.md) |
| MCP language matrix | [MCP-LANGUAGE-MATRIX.md](../integrations/MCP-LANGUAGE-MATRIX.md) |
| MCP profiles | [MCP-PROFILES.md](../integrations/MCP-PROFILES.md) |
| CLI/harness | [CLI-ENGINEERING.md](CLI-ENGINEERING.md) |
| agent engineering | [models/agents](../models/agents/README.md) |
| concepts paired with mechanisms | [ENGINEERING-CONCEPTS.md](ENGINEERING-CONCEPTS.md) |
| consistency | [CONSISTENCY.md](CONSISTENCY.md) |
| where decisions are recorded | [DECISIONS.md](DECISIONS.md) |
| Git/worktrees | [GIT-WORKTREES.md](GIT-WORKTREES.md) |
| JSON | [JSON.md](JSON.md) |
| package/tool catalog | [PACKAGE-CATALOG.md](PACKAGE-CATALOG.md) |
| dependencies: closure, micro-deps, wiring | [DEPENDENCIES.md](DEPENDENCIES.md) |
| encoding & compression: adopt, measure, refuse | [ENCODING.md](ENCODING.md) |
| security hygiene | [SECURITY-HYGIENE.md](SECURITY-HYGIENE.md) |
| symlinks/paths | [SYMLINKS-PATHS.md](SYMLINKS-PATHS.md) |
| verification | [VERIFY.md](VERIFY.md) |
| entry and landing: short front, same verdict | [ENTRY-PLAN.md](ENTRY-PLAN.md) |
| version contract | [VERSIONING.md](VERSIONING.md) |
| integrations | [integrations](../integrations/HEADRON.md) |
| systems | [systems](systems/README.md) |
| certification, per check | [CERTIFICATION.md](CERTIFICATION.md) |
| security policy and platform controls | [SECURITY.md](../SECURITY.md) · [github-controls.json](../config/github-controls.json) |
| what each instrument proves | [instruments table](INSTRUMENTS.md) |
| machine-readable entry point | [llms.txt](../llms.txt) · [CLAUDE.md](../CLAUDE.md) · [AGENTS.md](../AGENTS.md) — one body, three conventions, all generated |
| using this atlas from elsewhere | [CONSUMING.md](CONSUMING.md) |
| licence | [LICENSE](../LICENSE) |
| product strategy, pricing, deployment | [PRODUCT-STRATEGY.md](PRODUCT-STRATEGY.md) |
| OpenSSF Scorecard improvement plan | [SCORECARD-IMPROVEMENT.md](SCORECARD-IMPROVEMENT.md) |

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
