# Code-Development

**Repository contract: v0.7.3**

Advanced, model-aware engineering atlas for programming languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, and verification.

> Read first: [MODEL.md](MODEL.md) -> [docs/INDEX.md](docs/INDEX.md) -> [atlas.yaml](atlas.yaml) -> runtime/model adapter -> domain guide -> pattern -> verification.

## v0.7.3

Completes the language route graph and restores full documentation reachability after CI found missing language targets and dropped index edges.

Core indexes:
- [Languages](languages/ATLAS.md)
- [Language guide index](languages/README.md)
- [MCP language matrix](integrations/MCP-LANGUAGE-MATRIX.md)
- [MCP profiles](integrations/MCP-PROFILES.md)
- [Models and runtimes](models/README.md)
- [Integrations](integrations/README.md)
- [Systems](systems/README.md)
- [CLI engineering](docs/CLI-ENGINEERING.md)
- [Agent harness](systems/AGENT-HARNESS.md)
- [Research](research/PROGRAMMING-RESEARCH-2026.md)

## Multi-language design
Use one language per meaningful responsibility, then connect components through the least expensive boundary that provides the required isolation.

Typical shapes:
Python -> Rust/C++/Mojo native core
TypeScript -> Go/Rust service
Python/Julia -> native/accelerator component
local process -> bounded stdio/schema
service -> versioned RPC/message schema
portable component -> WebAssembly/WASI

See [systems/POLYGLOT-ENGINEERING.md](systems/POLYGLOT-ENGINEERING.md).
