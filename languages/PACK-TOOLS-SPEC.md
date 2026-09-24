# Language Tool Manifest Contract

Every language pack carries `tools.yaml`: the machine-readable bridge between Atlas routing and
the smallest useful development environment for that language.

**The shape is declared once, in [tools/tools.schema.json](../tools/tools.schema.json)**, and read
from there by `scripts/atlas.py` (which fails the contract on a manifest that deviates),
`scripts/packprobe.py` (which classifies each entry from the same grammar), and by the block
below. A second copy of a required-field roster agrees with the first only until one is edited, so
the skeleton here is generated — never hand-maintained:

<!-- BEGIN generated: manifest-contract (python scripts/atlas.py index --write) -->
Derived from `tools/tools.schema.json` — 6 required top-level keys, 12 authority roles, 7 task profiles, 5 entry kinds.

```yaml
schema: 2
language: <the pack directory's own name>
provenance:
  since:
  basis:
  verify:
  none_means:
authority:
  compiler_or_runtime:  # entry
  package_manager:  # entry
  formatter:  # entry
  lsp:  # entry
  debugger:  # entry
  profiler:  # entry
  test:  # entry
  fuzz:  # entry
  mutation:  # entry
  security:  # entry
  docs:  # https URL
  research:  # https URL
profiles:
  implementation: []
  debugging: []
  endpoint: []
  security: []
  performance: []
  reliability: []
  polyglot: []
policy:
  default_tools:
  optional_tools:
  avoid_by_default:
  warnings:
  blockers:
notes:                     # optional: prose, keyed by the role it qualifies
```

Every entry is one of these kinds, and the kind is declared, never inferred:

| kind | written as | means |
|---|---|---|
| `command` | `go test` | the first word is a name PATH can resolve; `\|` separates equivalent alternatives (`lldb\|gdb`) |
| `lib` | `lib:hypothesis` | a package or crate reachable only through its ecosystem, which PATH cannot answer for |
| `builtin` | `builtin:EXPLAIN ANALYZE` | a facility inside the language, runtime or editor; there is no binary to find |
| `concept` | `concept:schema-or-ABI boundary` | a technique or a boundary rather than a tool |
| `none` | `none` | no established tool is known for this role; do not invent one |
<!-- END generated: manifest-contract -->

## Why an entry declares its kind

A role such as `test` or `profiler` is a single-purpose field, and prose used to live in it:
`Test (stdlib)`, `EXPLAIN ANALYZE`, `host toolchain tests under wasmtime`. An instrument that
wants to know whether a declared tool exists cannot evaluate those, so it skipped them — and a
skipped entry silently leaves the denominator. **Measured at 1.2.1: 49% of declared entries were
prose in fields that also held binaries, which is why no mechanical verification of the packs was
possible.** The kind markers move that prose to `notes`, where it is still read by people and no
longer counted as a tool.

`|` separates equivalent alternatives, and a role that genuinely needs several tools **together**
takes a list — `security: [ruff, bandit]`. It replaced `ruff+bandit`, which a probe read as
`either`, so a half-covered role reported as covered.

## Rules

1. Native compiler/runtime and package manager are authoritative.
2. One tool per capability; do not stack equivalent linters without a recorded reason.
3. Optional tools activate from a task profile or an explicit failure class, never by default.
4. MCP and connectors are capability adapters, not language authorities.
5. AI output is a hypothesis until native tooling or independent verification confirms it.
6. Warnings are visible but normally non-blocking; new errors and blockers fail CI.
7. Existing findings may be baselined; new findings must not raise the baseline silently.
8. Every external boundary declares schema, version, timeout, idempotency and error handling.
9. A manifest stays small enough to load as task-scoped context.
10. `none` means no established tool is known for the role. Do not invent one, and do not leave
    the field out — an absent role and a role with nothing in it are different claims.
11. Changing what a manifest routes to updates the pack's operating card and `atlas.yaml` in the
    same commit.

## What conformance does not prove

`atlas.py check` proves a manifest's shape. It cannot prove that `go test` is installed, that the
version is current, or that anyone has ever run it here — `packprobe.py` answers the first and
`provenance.verify` carries the rest as a named debt. See
[tools/README.md](../tools/README.md) for how a route turns a manifest into an activation.
