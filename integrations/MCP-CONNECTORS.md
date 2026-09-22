# MCP and Connectors

Model Context Protocol (MCP) is a protocol for connecting LLM applications to external context and tools. The architecture distinguishes hosts, clients/connectors, and servers and uses JSON-RPC messages.

Primary references:
- MCP specification: https://modelcontextprotocol.io/specification/draft
- MCP tools: https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- OpenAI MCP/connectors: https://developers.openai.com/api/docs/guides/tools-connectors-mcp

## Architecture

```text
LLM application
  ↓
host
  ↓
client / connector
  ↓
MCP server
  ↓
tool / resource / prompt
  ↓
external system
```

## Tool design

Every tool should have:
- narrow purpose
- explicit input schema
- explicit output schema when useful
- deterministic naming
- bounded execution
- clear side effects
- authorization boundary
- audit information
- timeout/cancellation behavior

Do not expose a single mega-tool that can perform arbitrary filesystem, shell, database, or GitHub operations.

## Tool descriptions are not policy

Tool descriptions and annotations can be useful metadata but should not be treated as the ultimate security control. The MCP security guidance treats tools as potentially powerful execution surfaces and recommends explicit user control/authorization.

## Determinism and prompt/cache efficiency

MCP tool lists should be stable and deterministic where the underlying tool set is stable. This improves discoverability and can help downstream caching/context efficiency.

Prefer concise, precise schemas over verbose tool catalogs.

## Connectors vs remote MCP

OpenAI's Responses API supports both connector IDs for supported services and remote MCP servers identified by `server_url`.

Do not assume a connector and an arbitrary remote MCP server have the same trust model. Remote servers require explicit trust and authorization decisions.

## AI-agent security

Apply:
- allowlisted tools
- least-privilege credentials
- bounded arguments
- bounded results
- approval for destructive actions
- network policy
- secret redaction
- audit logs
- timeouts
- rate limits
- rollback where state changes occur

## Connector failure model

Treat connector failures as normal:
timeout -> retry only within a budget -> circuit break/backoff -> controlled degradation

Never let an unavailable connector cause an infinite agent loop.