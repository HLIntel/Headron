# Cloudflare Workers

A **platform** pack, not a language: it routes a Worker's `wrangler.toml`, `wrangler.json` or
`wrangler.jsonc` by **filename** (the `project_manifest` precedence rule), because those extensions
belong to every other tool's config too. The Worker's own code is TypeScript or JavaScript and
routes to that pack; this one owns the build, the binding types and the platform boundary.

**The rule that shapes it:** a gate verifies, a deploy acts. `atlas gate wrangler.jsonc
compiler_or_typechecker` answers `wrangler deploy --dry-run --config`, which compiles without
touching live servers. Deploys, secret writes and DNS changes sit behind the approval control in
`atlas.yaml/agent_policy` and are never a gate.

- Tools and their sources: [tools.yaml](tools.yaml) · card: [OPERATING.md](OPERATING.md)
- Edge decisions (CDN, caching): `atlas decide cdn`, `atlas decide caching_strategies`
- In an editor: the Cloudflare MCP server is wired per [models/zed/README.md](../../models/zed/README.md)
