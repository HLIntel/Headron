# OpenAI / Codex Adapter

Separate reasoning, repo tools, shell, MCP, connectors, and application-side policy.

## MCP/connectors
Use narrow tool exposure, explicit approval where required, and `allowed_tools` when a remote MCP server provides a wider tool surface than the task needs.

## Routing
Use strong reasoning for architecture/debugging/security; use smaller/faster models for repetitive, schema-driven transformations.

## API orchestration
Normalize `model + provider + endpoint + auth_ref + timeout + retry_budget + tool_policy` so application logic does not depend on one model vendor.

Official: https://developers.openai.com/api/docs/guides/tools-connectors-mcp