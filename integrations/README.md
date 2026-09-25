# Integrations

- [GitHub as a control plane](GITHUB.md) — surfaces, policy, and what is enforced here
- [Webhooks](WEBHOOKS.md)
- [MCP and Connectors](MCP-CONNECTORS.md)
- [AI Capabilities](AI-CAPABILITIES.md)
- [MCP Language Matrix](MCP-LANGUAGE-MATRIX.md)
- [MCP Profiles](MCP-PROFILES.md)
- [API Contracts](API-CONTRACTS.md)
- [Endpoints](ENDPOINTS.md)
- [VS Code](VS-CODE.md)

## What enforces the pages under here

- **A server no profile names** fails the contract — `mcp_is_task_scoped`, checked against
  `.vscode/mcp.json.example`, which also fails on a literal credential.
- **What a task may activate** is declared in `atlas.yaml/tool_profiles` and capped, because a
  manifest that defaults to everything is not a bounded tool surface.
- **What a person or agent should have at all** — and the `never_by_default` list that does the
  load-bearing half — is `atlas.yaml/developer_baseline`.
- **Boundary contracts** are the one thing no single pack answers for:
  `authority_classes/boundary` is deliberately empty and names what closes it instead.
