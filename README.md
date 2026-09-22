# Code-Development

**Repository contract: v1.0.1**

Advanced, model-aware engineering atlas and operating system for programming languages, AI coding systems, agents, Git/GitHub, APIs, MCP/connectors/Skills/plugins, data/research, storage, backends, performance, security, reliability, routing, and verification.

> **Read first:** [MODEL.md](MODEL.md) → [docs/INDEX.md](docs/INDEX.md) → [atlas.yaml](atlas.yaml) → runtime/model adapter → language guide → operating card → tool manifest → boundary → task route → scoped tools → verification.

## Start Here

- [Code-development wiki](wiki/README.md)
- [Code-specific routing](wiki/CODE-ROUTING.md)
- [Tool orchestration](wiki/TOOL-ORCHESTRATION.md)
- [Language operations](wiki/LANGUAGE-OPERATIONS.md)
- [Language packs](languages/README.md)
- [Language pack contract](languages/PACK-SPEC.md)
- [Language tool manifest contract](tools/README.md)
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

The route resolves language, native authority, runtime, MCP profile, operating card, tool manifest, labels, branch lane, worktree, and verification. The plan command adds task-specific assurance.

```bash
python scripts/atlas.py learn rust
```

`learn` turns a language's operating card and tool manifest into the seven-pass mastery loop, so an agent or developer deepens exactly one language at a time.

## The harness is tested

`scripts/atlas_test.py` plants a real defect on disk for each rule the contract
claims to enforce — a hand-edited generated block, a version skew, a manifest with
a missing or mismatched key, a route whose label is not in the catalog, a route
with no pack — and asserts the check fails on each, that a clean tree passes, that
`index --write` repairs the drift it reports and is idempotent, and that ten route
edge cases behave (no extension, uppercase, a path outside the repository, a nested
pack). It asserts its own case count, because a harness that silently skips cases
prints a full pass. CI runs it before the contract.

## Dynamic verification

The repository selects the smallest sufficient verification surface from the task and risk. Required gates are explicit:

<!-- BEGIN generated: verification-gates (python scripts/atlas.py index --write) -->
```text
source_change      -> formatter + compiler_or_typechecker + unit_tests
api_change         -> schema_validation + contract_tests + endpoint_tests + compatibility_check
dependency_change  -> dependency_graph + dependency_review + vulnerability_scan + tests
security_sensitive -> codeql + secret_scan + static_analysis + tests
concurrency_change -> race_detection + cancellation_tests + timeout_tests + stress_test
performance_change -> benchmark + profiler + representative_workload + regression_threshold
```
<!-- END generated: verification-gates -->

Use four severity classes: `blocker/error` are merge-blocking; `warning` is visible and actionable but normally non-blocking; `info` is report-only; `baseline` is limited to already-known findings. New findings must never be hidden by baseline growth.

## Assurance chain

```text
GOAL
 -> route
 -> native compiler/LSP/debugger/tester
 -> language tool manifest
 -> semantic repository context
 -> boundary contract
 -> targeted docs/browser/database capability
 -> security/dependency analysis
 -> independent verification
 -> CI
```

Do not load every tool, MCP, or language guide. Activate only the capability needed by the goal/failure class.

## Codespaces

A codespace boots from [.devcontainer](.devcontainer/README.md): Python plus the
harness dependency, with the contract run on create. Its purpose is confirming a
language pack against the real toolchain — add that one language as a devcontainer
feature, run `atlas.py learn <language>`, confirm the names in that pack's
`provenance.verify`, then remove the feature. Editing documents is faster locally.

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

Prefer primary documentation and repository examples over copied summaries. Each language pack includes a fast path, an operating card, and research links so an AI or developer can deepen only the language currently in use. Every route carries a machine-readable `tools.yaml`; entries listed under `provenance.verify` are to be confirmed against the language's documentation before a task relies on them, and `none` means no established tool is known for that role.

Release notes: [docs/VERSIONING.md](docs/VERSIONING.md) (one line per version, the only changelog).
