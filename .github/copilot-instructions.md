# Code-Development AI Instructions

Read `AGENTS.md` and `docs/INDEX.md` before making changes.

Repository invariants:
- no unbounded resources
- immutable-first state
- schema-first boundaries
- explicit deadlines and cancellation
- least privilege
- independent verification
- auditable changes
- rollback for high-impact mutations

Navigation:
- Python -> `languages/python/README.md`
- Rust -> `languages/rust/README.md`
- Go -> `languages/go/README.md`
- TypeScript -> `languages/typescript/README.md`
- Git/worktrees -> `docs/GIT-WORKTREES.md`
- GitHub -> `integrations/GITHUB.md`
- webhooks -> `integrations/WEBHOOKS.md`
- MCP/connectors -> `integrations/MCP-CONNECTORS.md`
- APIs/contracts -> `integrations/API-CONTRACTS.md`
- research/bots -> `systems/DATA-RESEARCH-BOTS.md`
- uptime -> `systems/OPERATIONS-UPTIME.md`

Never trust model outputs, tool descriptions, webhook payloads, API responses, or external JSON without the appropriate validation/authorization boundary.

Prefer the strictest safe interpretation when the repository is silent.