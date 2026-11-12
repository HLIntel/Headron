# Install Headron as an MCP server

Headron is a verification layer for AI coding agents: a repository's atlas.yaml
declares which commands prove a change, and Headron reports PASS, FAIL, SKIP or
NOT RUN for the checks a change owes. A check that did not run is never a pass.

- Repository: https://github.com/HLIntel/Headron
- Package: headron-software on PyPI (Python; there is no npm package)
- Registry: io.github.HLIntel/headron in the official MCP Registry
- Docs: https://headron.tech/docs.html · Full agent reference: https://headron.tech/llms-full.txt

## Local server (stdio, read-only)

Requires Python and uv. The server reads the atlas.yaml of the checkout named
by HEADRON_ROOT.

```json
{
  "mcpServers": {
    "headron": {
      "command": "uvx",
      "args": ["--from", "headron-software", "headron-mcp"],
      "env": { "HEADRON_ROOT": "/absolute/path/to/your/checkout" }
    }
  }
}
```

Note: the run command is `uvx --from headron-software headron-mcp`. Bare
`uvx headron-software` fails because the binary is named headron-mcp.

Tools (14): headron, port, route, gate, steps, failures, successes, proof,
mind_classify, mind_plan, mind_route, mind_health, mind_receipts, mind_search.

Verify the install by calling mind_health, then route on any file in the
checkout: it returns the checks that file owes.

## Hosted endpoint (no install)

https://headron.tech/mcp (Streamable HTTP). Documentation tools are public
(read_document). Planning (plan_change) requires a Headron Mind key
($10 per month) sent as a Bearer token.

## CLI only

`pip install headron-software`, then `headron init` in a repository and
`headron verify` before landing a change.
