# Code-Development

**Repository contract: v0.9.0**

Advanced, model-aware engineering atlas and operating system for programming languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, routing, and verification.

> Read first: [MODEL.md](MODEL.md) -> [docs/INDEX.md](docs/INDEX.md) -> [atlas.yaml](atlas.yaml) -> runtime/model adapter -> domain guide -> task route -> scoped tools -> verification.

## Start Here

- [Code-development wiki](wiki/README.md)
- [Code-specific routing](wiki/CODE-ROUTING.md)
- [Tool orchestration](wiki/TOOL-ORCHESTRATION.md)
- [Language operations](wiki/LANGUAGE-OPERATIONS.md)
- [Branch/worktree model](wiki/BRANCH-WORKTREES.md)
- [Labels and tags](wiki/LABELS-TAGS.md)
- [GitHub finalization](docs/GITHUB-FINALIZATION.md)
- [Languages](languages/ATLAS.md)
- [MCP language matrix](integrations/MCP-LANGUAGE-MATRIX.md)
- [Models and runtimes](models/README.md)
- [Systems](systems/README.md)
- [Research](research/PROGRAMMING-RESEARCH-2026.md)

## Code routing

Use the artifact route before choosing a model or tool:

```bash
python scripts/atlas.py route path/to/file.py
python scripts/atlas.py plan path/to/file.py --task debugging
```

The route resolves language, native authority, runtime, MCP profile, operations, labels, branch lane, worktree, and verification. The plan command adds task-specific assurance.

## Assurance chain

```text
route
 -> native compiler/LSP/debugger/tester
 -> semantic repository context
 -> targeted docs/browser/database capability
 -> security/dependency analysis
 -> independent verification
 -> CI
```

Do not load every tool or MCP. Activate only the capability needed by the failure class.

## Multi-language design

Use one language per meaningful responsibility, then connect components through the least expensive boundary that provides the required isolation.

```text
Python -> Rust/C++/Mojo native core
TypeScript -> Go/Rust service
Python/Julia -> native/accelerator component
local process -> bounded stdio/schema
service -> versioned RPC/message schema
portable component -> WebAssembly/WASI
```

See [systems/POLYGLOT-ENGINEERING.md](systems/POLYGLOT-ENGINEERING.md).

## v0.9.0

Adds a production-operations language matrix, tool-inside-tool orchestration model, endpoint/boundary assurance guidance, code-blob prevention, GitHub security/AI finalization guidance, Dependabot configuration, dependency review, Scorecard, and stronger Copilot routing.
