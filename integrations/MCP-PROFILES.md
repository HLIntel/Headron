# MCP Profiles

Profiles keep the tool, permission, and context surface bounded.

## core-code
GitHub MCP + Serena + native CLI/LSP/compiler/debugger.

## docs
Add Context7 for current library/framework documentation.

## browser
Add Playwright for browser/UI integration testing and controlled web interaction.

## security
Add Semgrep MCP through the local Semgrep CLI plus native security tooling.

## database
Add DBHub for local/staging database inspection with read-only, row, query-time, and connection limits.

## polyglot
Use core-code + native toolchains for both sides + boundary contract/integration tests. Add Context7 only when API/version questions require it.

## Profile rule
One task -> one profile. Add servers only when their capability is required.

Workspace MCP belongs in .vscode/mcp.json when a capability is genuinely project-wide. Personal tools belong in user configuration. Do not configure the same server in both places.

All local MCP servers are executable code: review source, permissions, environment, filesystem/network access, and trust before enabling.
