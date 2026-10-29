# Headron Enterprise API

**Status:** Public scaffold (3.60.0). The intended paid Enterprise service and private deployment are not implemented here.

## What this is

The Enterprise API adds HTTP transport to Headron's capabilities:

1. **MCP over HTTP** — An experimental HTTP wrapper around the local MCP handler. The stream endpoint is a placeholder, not a complete streaming transport.

2. **Mind API as REST** — The orchestration layer (classify, plan, route, health, receipts) exposed as typed REST endpoints with proper status codes.

3. **API key authentication** — Stateless key checks via the `HEADRON_API_KEYS` environment variable. This is not billing or an entitlement system.

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

| Method | Path          | Description                                            |
| ------ | ------------- | ------------------------------------------------------ |
| POST   | `/mcp`        | MCP JSON-RPC over HTTP                                 |
| GET    | `/mcp/stream` | Experimental session placeholder; no message streaming |
| GET    | `/tools`      | List available MCP tools                               |

### Mind API REST

| Method | Path                       | Description                   |
| ------ | -------------------------- | ----------------------------- |
| GET    | `/mind/classify?files=...` | Classify files by change type |
| GET    | `/mind/plan?files=...`     | Generate verification plan    |
| GET    | `/mind/route?files=...`    | Select authorized agent       |
| GET    | `/mind/health`             | Mind API health telemetry     |
| GET    | `/mind/receipts`           | Gather audit receipts         |

### System

| Method | Path      | Description                              |
| ------ | --------- | ---------------------------------------- |
| GET    | `/health` | Server liveness probe (no auth required) |

## Usage

```bash
# Start a loopback-only server with an API key
HEADRON_API_KEYS="dev:$DEV_TOKEN" \
  python integrations/enterprise/server.py serve 8788

# Self-test
python integrations/enterprise/server.py --check
```

## Examples

```bash
# Health check (no auth)
curl http://localhost:8788/health

# List MCP tools
curl -H "Authorization: Bearer $DEV_TOKEN" http://localhost:8788/tools

# Classify a file via Mind API
curl "http://localhost:8788/mind/classify?files=scripts/mind.py" \
  -H "Authorization: Bearer $DEV_TOKEN"

# MCP JSON-RPC call
curl -X POST http://localhost:8788/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEV_TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Environment Variables

| Variable           | Description                                          |
| ------------------ | ---------------------------------------------------- |
| `HEADRON_API_KEYS` | Comma-separated `name:key` pairs for authentication  |
| `HEADRON_ROOT`     | Path to the Headron atlas (auto-detected if not set) |

## Design Decisions

- **Stdlib only** — No FastAPI, Flask, or other web framework. Follows `githubapp.py` pattern.
- **Subprocess isolation** — Each command runs in a fresh process with cache cleared, like `headron_mcp.py`.
- **API keys, not JWT** — Simple, stateless, fast to implement. Can add JWT later if needed.
- **Product boundary** — The CLI, local MCP, and Mind implementation are in this public repository. A private, paid Enterprise offering needs its own service, access controls, entitlements, and billing; this scaffold does not provide them.
- **Local boundary** — The server binds loopback and refuses to start without valid keys. `/health` is unauthenticated. The scaffold does not provide TLS and is not ready for public exposure.

## Next Steps

- [ ] Add SSE streaming for long-running MCP calls
- [ ] Add rate limiting per API key
- [ ] Add OpenAPI spec generation
- [ ] Add WebSocket support for real-time updates
- [ ] Add session persistence for MCP streams
- [ ] Add dual embeddings endpoint (when implemented)
- [ ] Add web console for browser-based agent connection
