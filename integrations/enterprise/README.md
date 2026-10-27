# Headron Enterprise API

**Status:** Scaffold (3.60.0) — MCP HTTP transport and Mind API REST endpoints.

## What this is

The Enterprise API adds HTTP transport to Headron's capabilities:

1. **MCP over HTTP** — The same 12 MCP tools available via HTTP POST with SSE streaming, not just stdio. Agents on any host can connect.

2. **Mind API as REST** — The orchestration layer (classify, plan, route, health, receipts) exposed as typed REST endpoints with proper status codes.

3. **API key authentication** — Simple, stateless auth via `HEADRON_API_KEYS` environment variable.

## Architecture

```
Client (agent, web, script)
    ↓ HTTP
Enterprise API Server (server.py)
    ↓ subprocess / import
headron_mcp.py (MCP tools)
mind.py (Mind API orchestration)
    ↓
atlas.py (CLI commands)
```

The server uses Python stdlib `http.server` — no external dependencies. It imports `headron_mcp.py` to ensure the same tools, same schema, same read-only construction as the stdio server.

## Endpoints

### MCP Transport

| Method | Path | Description |
|--------|------|-------------|
| POST | `/mcp` | MCP JSON-RPC over HTTP |
| GET | `/mcp/stream` | SSE stream for MCP session |
| GET | `/tools` | List available MCP tools |

### Mind API REST

| Method | Path | Description |
|--------|------|-------------|
| GET | `/mind/classify?files=...` | Classify files by change type |
| GET | `/mind/plan?files=...` | Generate verification plan |
| GET | `/mind/route?files=...` | Select authorized agent |
| GET | `/mind/health` | Mind API health telemetry |
| GET | `/mind/receipts` | Gather audit receipts |

### System

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Server liveness probe (no auth required) |

## Usage

```bash
# Start the server (open, for local development)
python integrations/enterprise/server.py serve 8080

# Start with API key authentication
HEADRON_API_KEYS="dev:mysecretkey,prod:prodkey123" \
  python integrations/enterprise/server.py serve 8080

# Self-test
python integrations/enterprise/server.py --check
```

## Examples

```bash
# Health check (no auth)
curl http://localhost:8080/health

# List MCP tools (requires auth if keys configured)
curl -H "Authorization: Bearer mysecretkey" http://localhost:8080/tools

# Classify a file via Mind API
curl "http://localhost:8080/mind/classify?files=scripts/mind.py" \
  -H "Authorization: Bearer mysecretkey"

# MCP JSON-RPC call
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mysecretkey" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HEADRON_API_KEYS` | Comma-separated `name:key` pairs for authentication |
| `HEADRON_ROOT` | Path to the Headron atlas (auto-detected if not set) |

## Design Decisions

- **Stdlib only** — No FastAPI, Flask, or other web framework. Follows `githubapp.py` pattern.
- **Subprocess isolation** — Each command runs in a fresh process with cache cleared, like `headron_mcp.py`.
- **API keys, not JWT** — Simple, stateless, fast to implement. Can add JWT later if needed.
- **Mind API is private** — The Enterprise API wraps it; products can build on top with additional capabilities.

## Next Steps

- [ ] Add SSE streaming for long-running MCP calls
- [ ] Add rate limiting per API key
- [ ] Add OpenAPI spec generation
- [ ] Add WebSocket support for real-time updates
- [ ] Add session persistence for MCP streams
- [ ] Add dual embeddings endpoint (when implemented)
- [ ] Add web console for browser-based agent connection
