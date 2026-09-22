# VS Code Runtime / Agent-Host Adapter

VS Code is the interactive editor, debugger, task launcher, remote-development client, source-control surface, and optional AI/MCP host.

Use native editor/LSP/debugger/test tools first. Use MCP only for specialized or external capability.

Profiles: core-code, docs, browser, security, database, polyglot.

Serena is the main optional semantic-code MCP. Current upstream licensing is GPL-3.0-or-later for the overall Serena distribution; SolidLSP components are separately MIT-licensed.

GitHub MCP Server is the official GitHub integration. Playwright is for browser/UI tasks, Context7 for current external docs, Semgrep for security analysis, and DBHub for bounded SQL/database access.

Use workspace MCP configuration only for genuinely shared project capabilities; user configuration is for personal tools. Never commit API keys.
