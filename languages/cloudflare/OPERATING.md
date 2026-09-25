# Cloudflare Operating Card

**Route:** `wrangler.toml|json|jsonc` by filename; the Worker's code routes to TypeScript.

**Fast path:** `wrangler types --check` → `wrangler deploy --dry-run --config <file>` → `vitest`.

**Native authority:** Wrangler and the Workers runtime; pin the Wrangler version the project builds with.

**Pair with:** TypeScript for the Worker; WebAssembly where a hot path compiles to Wasm.

**Boundary:** bindings (KV, D1, R2, queues) declared in the config, typed by `wrangler types`.

**Avoid:** deploying from an agent without approval; secrets in the config file; a cache key that omits an identity header.

**Reliability:** dry-run every change; test against the Workers runtime, not Node's.

**Verify:** type drift → dry-run build → runtime tests.

**AI learning loop:** read `atlas decide cdn` before caching a dynamic response at the edge.
