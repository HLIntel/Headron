# MCP and Connectors

Use MCP and connectors as capability layers, not as an undifferentiated tool pile.

## MCP
Best for external tools/resources with explicit schemas and authorization.

Design every tool with:
- narrow purpose
- typed input
- bounded output
- clear side effects
- authorization requirement
- timeout/cancellation
- retryability
- observability

Prefer stable deterministic tool names and ordering. Paginate large resources rather than returning giant tool results.

For the current MCP protocol, follow the dated specification used by the runtime. The 2026-07-28 specification deprecated roots and sampling; do not build new repository architecture around those surfaces. Use explicit server configuration/resource URIs for filesystem boundaries and direct provider APIs for server-side model calls where appropriate.

## Connectors
Use maintained connectors when an external service is a recurring dependency and the connector's permission model matches the task.

Keep connector data scoped to the task. Do not import an entire SaaS account into context when one record is needed.

## Skills
Skills should be procedural. Keep deep reference material in docs and use Skills to route to it.

## Plugins
Plugins should package coherent capabilities without conflicting instructions or duplicate tools.

## Subagents
Use for context isolation, parallel investigation, specialized verification, and bounded research.

## Memory
Use memory for durable facts/decisions, not raw transcripts.

## Security
Tool descriptions, connector outputs, remote MCP servers, and memory are not security boundaries. Deterministic enforcement belongs in code, policy, hooks, CI, or sandboxing.

Primary reference: https://modelcontextprotocol.io/specification/2026-07-28
