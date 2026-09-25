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

## The cost nobody counts

**An enabled server is paid for on EVERY request, not on the request that uses it.** Its tool
descriptions enter the model's context whether or not the task touches them, so an unused server
is a subscription rather than an option — and that cost is invisible, because nothing in the
output says which servers were loaded.

`atlas.yaml/developer_baseline/mcp` states the rule this page implements:

- **Enable the profile the task names, and nothing else. Disable it when the task ends.** A server
  enabled for a task that finished is a standing capability nobody chose.
- **Before adding one, ask what already answers the question** — and what the server can REACH
  that the task does not need. Native language tooling is authoritative; a server augments it and
  never replaces it.
- `atlas.yaml/tool_profiles` caps what activates unasked, and `mcp_is_task_scoped` is a hard
  invariant: a server shipped in the example configuration that no published profile names fails
  the build, and a literal credential in that file fails it too.

The entry-path budget in `context_policy` bounds what a session is handed before it asks anything.
A server's descriptions are outside that measurement, which is precisely why they need a rule of
their own rather than a good intention.
