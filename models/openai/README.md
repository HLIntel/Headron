# OpenAI / Codex Adapter

Separate model reasoning, repo tools, shell execution, MCP, connectors, and application-side policy.

Responses API MCP usage supports remote MCP servers and supported connectors. Use narrow tool exposure, explicit approvals for sensitive sharing/side effects, and `allowed_tools` when a server exposes more than the task requires.

Keep authorization outside repository files. Prefer stable tool definitions and compact context handoffs.

Official: https://developers.openai.com/api/docs/guides/tools-connectors-mcp