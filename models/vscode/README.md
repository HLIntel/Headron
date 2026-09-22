# VS Code Runtime / Agent-Host Adapter

VS Code is the interactive editor, debugger, task launcher, remote-development client, source-control surface, and optional AI/MCP host.

Use native editor/LSP/debugger/test tools first. Use MCP for external or specialized capability.

Recommended profiles:
- core-code
- docs
- browser
- security
- database
- polyglot

See integrations/MCP-LANGUAGE-MATRIX.md and integrations/MCP-PROFILES.md.

Serena is the primary optional semantic-code MCP because it uses LSP-backed symbolic operations across many languages. In IDE integrations, use an IDE-oriented context when supported to reduce duplication.

Use the official GitHub MCP Server for GitHub repository/issues/PRs/Actions/security context.

Use Playwright only for browser/UI work, Context7 for current external docs, Semgrep for deterministic security scans, and DBHub for bounded SQL/database access.

Use .vscode/mcp.json for project-wide shared servers and user configuration for personal tools. Never commit API keys. Review trust and source before enabling local MCP servers.

Official VS Code MCP docs: https://code.visualstudio.com/docs/agent-customization/mcp-servers
