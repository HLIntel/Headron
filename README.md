# Code-Development

**Repository contract: v0.8.0**

Advanced, model-aware engineering atlas and operating system for programming languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, routing, and verification.

> Read first: [MODEL.md](MODEL.md) -> [docs/INDEX.md](docs/INDEX.md) -> [atlas.yaml](atlas.yaml) -> runtime/model adapter -> domain guide -> pattern -> verification.

## Start Here

- [Code-development wiki](wiki/README.md)
- [Languages](languages/ATLAS.md)
- [Language guide index](languages/README.md)
- [Code-specific routing](wiki/CODE-ROUTING.md)
- [Branch/worktree model](wiki/BRANCH-WORKTREES.md)
- [Labels and tags](wiki/LABELS-TAGS.md)
- [Language lanes](wiki/LANGUAGE-LANES.md)
- [MCP language matrix](integrations/MCP-LANGUAGE-MATRIX.md)
- [MCP profiles](integrations/MCP-PROFILES.md)
- [Models and runtimes](models/README.md)
- [Integrations](integrations/README.md)
- [Systems](systems/README.md)
- [CLI engineering](docs/CLI-ENGINEERING.md)
- [Agent harness](systems/AGENT-HARNESS.md)
- [Research](research/PROGRAMMING-RESEARCH-2026.md)

## Code routing

Use the artifact route before choosing a model or MCP:

```text
python scripts/atlas.py route path/to/file
```

The route resolves the language guide. The guide then determines native tooling, runtime adapter, applicable MCP profile, and verification path.

## Multi-language design

Use one language per meaningful responsibility, then connect components through the least expensive boundary that provides the required isolation.

Typical shapes:

```text
Python -> Rust/C++/Mojo native core
TypeScript -> Go/Rust service
Python/Julia -> native/accelerator component
local process -> bounded stdio/schema
service -> versioned RPC/message schema
portable component -> WebAssembly/WASI
```

See [systems/POLYGLOT-ENGINEERING.md](systems/POLYGLOT-ENGINEERING.md).

## v0.8.0

Adds a repository-native code-development wiki layer, explicit code-routing guidance, bounded GitHub label/tag taxonomy, and a language-lane branch/worktree policy while keeping `main` as the canonical contract baseline.
