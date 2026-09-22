# Code-Development Index

Route first. Read deeply only where the task requires it.

| Need | Start |
|---|---|
| repository/model contract | `MODEL.md` |
| machine routing | `atlas.yaml` |
| language choice | `languages/ATLAS.md` |
| language stack standard | `docs/LANGUAGE-SPEC.md` |
| language update procedure | `docs/LANGUAGE-UPDATE.md` |
| package/tool selection | `docs/PACKAGE-CATALOG.md` |
| verification | `docs/VERIFY.md` |
| contract/versioning | `docs/VERSIONING.md` |
| consistency checks | `docs/CONSISTENCY.md` + `scripts/check_contract.py` |
| prompts | `prompts/` |
| model adapters | `models/` |
| Git/worktrees | `docs/GIT-WORKTREES.md` |
| GitHub tools | `integrations/GITHUB.md` + `integrations/GITHUB-TOOLS.md` |
| webhooks/endpoints | `integrations/WEBHOOKS.md` + `integrations/ENDPOINTS.md` |
| MCP/connectors/Skills/plugins | `integrations/AI-CAPABILITIES.md` |
| API contracts | `integrations/API-CONTRACTS.md` |
| data/research/bots | `systems/DATA-RESEARCH-BOTS.md` |
| storage/state | `systems/STORAGE-STATE.md` |
| backend architecture | `systems/BACKEND-ARCHITECTURE.md` |
| operations/uptime | `systems/OPERATIONS-UPTIME.md` |
| cognitive code | `patterns/COGNITIVE-CODE-DESIGN.md` |
| context/tokens | `patterns/CONTEXT-EFFICIENCY.md` |
| no unbounded | `patterns/NO-UNBOUNDED.md` |
| anti-mutation | `patterns/ANTI-MUTATION.md` |

## Standard read order
`MODEL.md -> INDEX -> atlas -> runtime adapter -> specific guide -> pattern -> example/prompt -> verify`

## Agreement rule
Every canonical path referenced here must exist. Alias docs should be intentional symlinks. Run `python scripts/check_contract.py` before a contract-level commit.