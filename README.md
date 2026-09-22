# Code-Development

**Repository contract: v0.9.5**

Advanced, model-aware engineering atlas and operating system for programming languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, routing, and verification.

> **Read first:** [MODEL.md](MODEL.md) → [docs/INDEX.md](docs/INDEX.md) → [atlas.yaml](atlas.yaml) → runtime/model adapter → language guide → operating card → boundary → task route → scoped tools → verification.

## Start Here

- [Code-development wiki](wiki/README.md)
- [Code-specific routing](wiki/CODE-ROUTING.md)
- [Tool orchestration](wiki/TOOL-ORCHESTRATION.md)
- [Language operations](wiki/LANGUAGE-OPERATIONS.md)
- [Language packs](languages/README.md)
- [Language pack contract](languages/PACK-SPEC.md)
- [Branch/worktree model](wiki/BRANCH-WORKTREES.md)
- [Labels and tags](wiki/LABELS-TAGS.md)
- [GitHub backend/control plane](docs/GITHUB-BACKEND.md)
- [GitHub finalization](docs/GITHUB-FINALIZATION.md)
- [Security policy](SECURITY.md)
- [Languages](languages/ATLAS.md)
- [MCP language matrix](integrations/MCP-LANGUAGE-MATRIX.md)
- [Models and runtimes](models/README.md)
- [Systems](systems/README.md)
- [Research](research/PROGRAMMING-RESEARCH-2026.md)

## Goal-first code routing

Use the artifact route before choosing a model or tool:

```bash
python scripts/atlas.py route path/to/file.py
python scripts/atlas.py plan path/to/file.py --task debugging
```

The route resolves language, native authority, runtime, MCP profile, operating card, labels, branch lane, worktree, and verification. The plan command adds task-specific assurance.

## Assurance chain

```text
GOAL
 -> route
 -> native compiler/LSP/debugger/tester
 -> semantic repository context
 -> boundary contract
 -> targeted docs/browser/database capability
 -> security/dependency analysis
 -> independent verification
 -> CI
```

Do not load every tool, MCP, or language guide. Activate only the capability needed by the goal/failure class.

## Multi-language design

Use multiple languages only when a language contributes a distinct guarantee, runtime property, ecosystem, or performance characteristic. Define the boundary first, then assign ownership.

```text
Python -> Rust/C++/Mojo native core
TypeScript -> Go/Rust service
Python/Julia -> native/accelerator component
local process -> bounded stdio/schema
service -> versioned RPC/message schema
portable component -> WebAssembly/WASI
```

See [systems/POLYGLOT-ENGINEERING.md](systems/POLYGLOT-ENGINEERING.md).

## Learning / mastery loop

`read reference → trace real code → reproduce tiny example → modify → break intentionally → verify → benchmark → record lesson`.

Prefer primary documentation and repository examples over copied summaries. Each language pack includes a fast path and research links so an AI or developer can deepen only the language currently in use.

## v0.9.5

Adds per-language operating cards, model/runtime routing, progressive context policy, goal-first task routing, and a GitHub backend control-plane guide while keeping the repository contract synchronized.
