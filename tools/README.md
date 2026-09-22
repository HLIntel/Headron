# Language Tool Manifests

Machine-readable tool contracts live at `languages/<language>/tools.yaml`.

## Purpose

A manifest answers **what to activate**, not merely what exists. Atlas uses it to construct the smallest useful development environment for a file and task.

Required capability groups:

- `format`: formatter/normalizer
- `build`: compiler/interpreter/build system
- `typecheck`: type checker or static checker
- `lsp`: editor intelligence
- `debug`: debugger/runtime debugger
- `test`: unit/integration runner
- `property`: property/fuzz tooling
- `mutation`: mutation tooling where mature
- `profile`: profiler/benchmark tooling
- `package`: package/dependency manager
- `security`: native security/static-analysis tooling
- `mcp`: optional task-scoped MCP/connector capabilities
- `vscode`: useful extensions, never enforcement
- `runtime`: cloud/server/edge/container/runtime adapters

## Selection rule

`task + artifact + boundary + risk` selects tools. Do not activate the entire manifest by default.

Native language tooling is authoritative. MCPs, AI tools, and IDE extensions augment it.

## Warning policy

Warnings are classified as `blocker`, `error`, `warning`, `info`, or `baseline`. New violations are actionable; existing baseline findings do not become perpetual noise.

## Verification tiers

- **fast**: format + compile/typecheck + focused tests
- **standard**: fast + static analysis + dependency/security checks relevant to the change
- **deep**: standard + property/fuzz/mutation/performance or runtime checks selected by risk
- **release**: deep + full integration + artifact/supply-chain verification

See `atlas.yaml`, `MODEL.md`, and `docs/VERIFY.md` for enforcement.