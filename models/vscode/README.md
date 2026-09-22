# VS Code Runtime / Agent-Host Adapter

VS Code is the interactive editor, debugger, task launcher, remote-development client, source-control surface, and optional AI/MCP host.

Use native editor/LSP/debugger/test tools first. Use MCP for specialized or external capability.

Recommended profiles:
- core-code
- docs
- browser
- security
- database
- polyglot

See integrations/MCP-LANGUAGE-MATRIX.md and integrations/MCP-PROFILES.md.

Serena is the main optional semantic-code MCP. Current upstream licensing is GPL-3.0-or-later for the overall Serena distribution; SolidLSP components are separately MIT-licensed. Review the current LICENSE before redistributing bundled changes.

GitHub MCP Server is the official GitHub integration. Playwright is for browser/UI tasks, Context7 for current external docs, Semgrep for security scanning, and DBHub for bounded SQL/database access.

Use workspace MCP configuration for genuinely shared project capabilities and user configuration for personal tools. Never commit API keys.
