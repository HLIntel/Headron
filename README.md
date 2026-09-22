# Code-Development

**Repository contract: v0.7.0**

Advanced, model-aware engineering atlas for languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, and verification.

> Read first: [MODEL.md](MODEL.md) -> [docs/INDEX.md](docs/INDEX.md) -> [atlas.yaml](atlas.yaml) -> runtime/model adapter -> domain guide -> pattern -> verification.

## v0.7.0

Adds language-by-language MCP/VS Code routing and scoped MCP profiles while keeping native language toolchains authoritative.

## Core indexes
- [Languages](languages/ATLAS.md)
- [MCP language matrix](integrations/MCP-LANGUAGE-MATRIX.md)
- [MCP profiles](integrations/MCP-PROFILES.md)
- [Models and runtimes](models/README.md)
- [Integrations](integrations/README.md)
- [Systems](systems/README.md)
- [CLI engineering](docs/CLI-ENGINEERING.md)
- [Agent harness](systems/AGENT-HARNESS.md)
- [Research](research/PROGRAMMING-RESEARCH-2026.md)

## Multi-language design
Use one language per meaningful responsibility, then connect components through the least expensive boundary that provides the needed isolation.

Typical shapes:
Python -> Rust/C++/Mojo native core
TypeScript -> Go/Rust service
Python/Julia -> native/accelerator component
local process -> bounded stdio/schema
service -> versioned RPC/message schema
portable component -> WebAssembly/WASI

See [systems/POLYGLOT-ENGINEERING.md](systems/POLYGLOT-ENGINEERING.md).

## AI development
Use MCP only where it adds capability beyond native tools. Prefer one semantic repository layer over overlapping language-navigation MCPs. Enable browser, database, security, and documentation servers per task.

## VS Code + OpenCode
VS Code is the interactive workbench. OpenCode is the terminal-native agent/workspace layer. Share the same deterministic harness and use separate worktrees for concurrent writers.
