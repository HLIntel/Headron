# Code-Development Index

Use this page as the routing table. Do not browse the repository randomly when the subsystem is known.

| Need | Start here |
|---|---|
| AI coding behavior | `AGENTS.md`, `docs/AI-AGENT-ENGINEERING.md` |
| Entire repository direction | `README.md` |
| Package/tool selection | `docs/PACKAGE-CATALOG.md` |
| Python | `languages/python/README.md` |
| Rust | `languages/rust/README.md` |
| Go | `languages/go/README.md` |
| TypeScript/JS | `languages/typescript/README.md` |
| C++ | `languages/cpp/README.md` |
| Zig | `languages/zig/README.md` |
| Mojo | `languages/mojo/README.md` |
| Julia | `languages/julia/README.md` |
| Elixir | `languages/elixir/README.md` |
| Lean 4 | `languages/lean4/README.md` |
| Git/worktrees | `docs/GIT-WORKTREES.md` |
| GitHub repo/API/CLI/rules | `integrations/GITHUB.md` |
| Webhooks | `integrations/WEBHOOKS.md` |
| MCP/connectors/tools | `integrations/MCP-CONNECTORS.md` |
| API contracts | `integrations/API-CONTRACTS.md` |
| Data/research/bots | `systems/DATA-RESEARCH-BOTS.md` |
| Uptime/operations | `systems/OPERATIONS-UPTIME.md` |
| No-unbounded design | `patterns/NO-UNBOUNDED.md` |
| Mutation control | `patterns/ANTI-MUTATION.md` |
| High-assurance delivery | `patterns/HIGH-ASSURANCE-WORKFLOW.md` |
| Architectural decisions | `docs/DECISIONS.md` |

## Standard reading order

`AGENTS.md` -> `README.md` -> this index -> relevant language/integration/system guide -> applicable pattern -> code/example -> verification.

## Repository layers

```text
LANGUAGES
  ↓
RUNTIMES / PACKAGES
  ↓
DATA CONTRACTS
  ↓
INTEGRATIONS
  ↓
SYSTEMS
  ↓
SECURITY / HYGIENE
  ↓
AI AGENTS
  ↓
OPERATIONS / UPTIME
```

Cross-cutting patterns should be reusable across every language.