# Cloudflare Workers

A **platform** pack, not a language: it routes a Worker's `wrangler.toml`, `wrangler.json` or
`wrangler.jsonc` by **filename** (the `project_manifest` precedence rule), because those extensions
belong to every other tool's config too. The Worker's own code is TypeScript or JavaScript and
routes to that pack; this one owns the build, the binding types and the platform boundary.

**The rule that shapes it:** a gate verifies, a deploy acts. `atlas gate wrangler.jsonc
compiler_or_typechecker` answers `wrangler deploy --dry-run --config`, which compiles without
touching live servers. Deploys, secret writes and DNS changes sit behind the approval control in
`atlas.yaml/agent_policy` and are never a gate.

- Tools and their sources: [tools.yaml](tools.yaml) · card: [Operating card](#operating-card)
- Edge decisions (CDN, caching): `headron decide cdn`, `headron decide caching_strategies`
- In an editor: an MCP server is registered in the host's own store, never in this repository

## Operating card

**Route:** `wrangler.toml|json|jsonc` by filename; the Worker's code routes to TypeScript.

**Fast path:** `wrangler types --check` → `wrangler deploy --dry-run --config <file>` → `vitest`.

**Native authority:** Wrangler and the Workers runtime; pin the Wrangler version the project builds with.

**Pair with:** TypeScript for the Worker; WebAssembly where a hot path compiles to Wasm.

**Boundary:** bindings (KV, D1, R2, queues) declared in the config, typed by `wrangler types`.

**Avoid:** deploying from an agent without approval; secrets in the config file; a cache key that omits an identity header.

**Reliability:** dry-run every change; test against the Workers runtime, not Node's.

**Verify:** type drift → dry-run build → runtime tests.

**AI learning loop:** read `headron decide cdn` before caching a dynamic response at the edge.

**Research:** https://developers.cloudflare.com/workers/wrangler/commands/ · https://developers.cloudflare.com/workers/runtime-apis/
