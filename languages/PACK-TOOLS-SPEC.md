# Language Tool Manifest Contract

Each language pack may contain `tools.yaml`. It is the machine-readable bridge between Atlas routing and the language's smallest useful development environment.

Required fields:

```yaml
schema: 1
authority:
  compiler_or_runtime:
  package_manager:
  formatter:
  lsp:
  debugger:
  profiler:
  test:
  fuzz:
  mutation:
  security:
  docs:
  research:
profiles:
  implementation: []
  debugging: []
  endpoint: []
  security: []
  performance: []
  reliability: []
  polyglot: []
policy:
  default_tools: []
  optional_tools: []
  avoid_by_default: []
  warnings: non_blocking
  blockers: []
```

Rules:

1. Native compiler/runtime and package manager are authoritative.
2. Prefer one tool per capability; do not stack equivalent linters without a reason.
3. Optional tools activate only from a task profile or explicit failure class.
4. MCP/connectors are capability adapters, not language authorities.
5. AI output is a hypothesis until native tooling or independent verification confirms it.
6. Warnings are visible but normally non-blocking; new errors/blockers fail CI.
7. Existing findings may be baselined; new findings must not increase technical debt silently.
8. Every external boundary gets schema/version/timeout/idempotency/error handling where applicable.
9. Tool manifests must remain small enough to load as task-scoped context.
10. Update the language operating card and Atlas when a manifest changes routing semantics.
