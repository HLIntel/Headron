# Code-Specific Routing

Routing should answer four questions before an agent edits code:

1. **What language/toolchain owns this artifact?**
2. **What task is being performed?**
3. **Which runtime/model/MCP profile is justified?**
4. **How will the result be verified?**

## Precedence

Use the first unambiguous signal:

<!-- BEGIN generated: routing-precedence (python scripts/atlas.py index --write) -->
```text
explicit_path_or_task_override
    -> artifact_extension
    -> project_manifest
    -> language_directory
    -> issue_labels
    -> generic_fallback
```
<!-- END generated: routing-precedence -->

When signals conflict, the more specific artifact or explicit task wins and the conflict should be recorded rather than silently guessed.

## Extension route

<!-- BEGIN generated: route-table (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/artifact_routes`. The authority for a route is its manifest — no
tool is named here, because a tool named in prose is a tool nothing can check.

| artifact | route | authority (declared per pack) |
|---|---|---|
| `.bash` `.sh` | `bash` | [tools.yaml](../languages/bash/tools.yaml) · [card](../languages/bash/OPERATING.md) |
| `.bqn` | `bqn` | [tools.yaml](../languages/bqn/tools.yaml) · [card](../languages/bqn/OPERATING.md) |
| `.c` `.h` | `c` | [tools.yaml](../languages/c/tools.yaml) · [card](../languages/c/OPERATING.md) |
| `.carbon` | `carbon` | [tools.yaml](../languages/carbon/tools.yaml) · [card](../languages/carbon/OPERATING.md) |
| `.chpl` | `chapel` | [tools.yaml](../languages/chapel/tools.yaml) · [card](../languages/chapel/OPERATING.md) |
| `.cc` `.cpp` `.hpp` | `cpp` | [tools.yaml](../languages/cpp/tools.yaml) · [card](../languages/cpp/OPERATING.md) |
| `.cu` `.cuh` | `cuda` | [tools.yaml](../languages/cuda/tools.yaml) · [card](../languages/cuda/OPERATING.md) |
| `.ex` `.exs` | `elixir` | [tools.yaml](../languages/elixir/tools.yaml) · [card](../languages/elixir/OPERATING.md) |
| `.4th` `.fth` | `forth` | [tools.yaml](../languages/forth/tools.yaml) · [card](../languages/forth/OPERATING.md) |
| `.fs` `.fsx` | `fsharp` | [tools.yaml](../languages/fsharp/tools.yaml) · [card](../languages/fsharp/OPERATING.md) |
| `.fut` | `futhark` | [tools.yaml](../languages/futhark/tools.yaml) · [card](../languages/futhark/OPERATING.md) |
| `.gleam` | `gleam` | [tools.yaml](../languages/gleam/tools.yaml) · [card](../languages/gleam/OPERATING.md) |
| `.go` | `go` | [tools.yaml](../languages/go/tools.yaml) · [card](../languages/go/OPERATING.md) |
| `.ha` | `hare` | [tools.yaml](../languages/hare/tools.yaml) · [card](../languages/hare/OPERATING.md) |
| `.hs` `.lhs` | `haskell` | [tools.yaml](../languages/haskell/tools.yaml) · [card](../languages/haskell/OPERATING.md) |
| `.jl` | `julia` | [tools.yaml](../languages/julia/tools.yaml) · [card](../languages/julia/OPERATING.md) |
| `.lean` | `lean4` | [tools.yaml](../languages/lean4/tools.yaml) · [card](../languages/lean4/OPERATING.md) |
| `.mojo` | `mojo` | [tools.yaml](../languages/mojo/tools.yaml) · [card](../languages/mojo/OPERATING.md) |
| `.nim` | `nim` | [tools.yaml](../languages/nim/tools.yaml) · [card](../languages/nim/OPERATING.md) |
| `.ml` `.mli` | `ocaml` | [tools.yaml](../languages/ocaml/tools.yaml) · [card](../languages/ocaml/OPERATING.md) |
| `.odin` | `odin` | [tools.yaml](../languages/odin/tools.yaml) · [card](../languages/odin/OPERATING.md) |
| `.py` `.pyi` | `python` | [tools.yaml](../languages/python/tools.yaml) · [card](../languages/python/OPERATING.md) |
| `.qs` | `quantum/qsharp` | [tools.yaml](../languages/quantum/qsharp/tools.yaml) · [card](../languages/quantum/qsharp/OPERATING.md) |
| `.slq` | `quantum/silq` | [tools.yaml](../languages/quantum/silq/tools.yaml) · [card](../languages/quantum/silq/OPERATING.md) |
| `.r` | `r` | [tools.yaml](../languages/r/tools.yaml) · [card](../languages/r/OPERATING.md) |
| `.roc` | `roc` | [tools.yaml](../languages/roc/tools.yaml) · [card](../languages/roc/OPERATING.md) |
| `.rs` | `rust` | [tools.yaml](../languages/rust/tools.yaml) · [card](../languages/rust/OPERATING.md) |
| `.sc` `.scala` | `scala` | [tools.yaml](../languages/scala/tools.yaml) · [card](../languages/scala/OPERATING.md) |
| `.sql` | `sql` | [tools.yaml](../languages/sql/tools.yaml) · [card](../languages/sql/OPERATING.md) |
| `.swift` | `swift` | [tools.yaml](../languages/swift/tools.yaml) · [card](../languages/swift/OPERATING.md) |
| `.cjs` `.js` `.jsx` `.mjs` `.ts` `.tsx` | `typescript` | [tools.yaml](../languages/typescript/tools.yaml) · [card](../languages/typescript/OPERATING.md) |
| `.ua` | `uiua` | [tools.yaml](../languages/uiua/tools.yaml) · [card](../languages/uiua/OPERATING.md) |
| `.v` | `v` | [tools.yaml](../languages/v/tools.yaml) · [card](../languages/v/OPERATING.md) |
| `.wasm` `.wat` | `webassembly` | [tools.yaml](../languages/webassembly/tools.yaml) · [card](../languages/webassembly/OPERATING.md) |
| `.zig` | `zig` | [tools.yaml](../languages/zig/tools.yaml) · [card](../languages/zig/OPERATING.md) |
<!-- END generated: route-table -->

**This table was hand-written and had gone wrong in both directions:** it named a tool per
row that disagreed with the pack owning that role, and it omitted six routes entirely, so a
reader routing a `.swift` or `.ml` file was told nothing claimed it. It is generated now.

## Task route

<!-- BEGIN generated: task-profiles (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/task_profiles`, resolved for one artifact by
`python scripts/atlas.py plan <path> --task <name>`.

| task profile | what it activates |
|---|---|
| `default` | `native` · `focused_context` · `focused_verify` |
| `implementation` | `native` · `semantic_context` · `tests` · `diff_review` |
| `debugging` | `native_debugger` · `focused_repro` · `regression_test` · `diff_review` |
| `endpoint` | `native_http` · `schema_contract` · `integration_test` · `browser_if_needed` |
| `database` | `native_db` · `read_only_dbhub` · `migration_test` · `plan_review` |
| `security` | `native_security` · `codeql` · `semgrep` · `secret_scan` · `dependency_review` |
| `reliability` | `timeouts` · `cancellation` · `health_readiness` · `telemetry` · `smoke_test` |
| `mutation` | `existing_tests` · `mutation_tool_if_mature` · `bounded_mutants` · `regression_gate` |
| `performance` | `profiler` · `benchmark` · `representative_workload` · `regression_threshold` |
| `polyglot` | `schema_or_abi` · `native_tools_both_sides` · `boundary_test` · `e2e_if_needed` |
| `research` | `primary_sources` · `isolated_context` · `prototype` · `measurement` |
| `retrieval` | `ast_chunking` · `hybrid_search` · `checksum_invalidation` · `sidecar_metadata` · `citations` |
| `autonomous_agent` | `narrow_tools` · `sandbox` · `budget` · `approval` · `audit` |
| `quantum` | `native_simulator` · `shots_declared` · `noise_model_declared` · `qubit_budget_declared` · `resource_estimate` · `classical_baseline` |
<!-- END generated: task-profiles -->

## Runtime and MCP profiles

<!-- BEGIN generated: tool-profiles (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/tool_profiles`. Use the smallest profile that satisfies the task;
native compiler, LSP, debugger, test and profiler output stays authoritative.

| tool profile | tools |
|---|---|
| `core-code` | `native` · `github` · `serena_when_supported` |
| `docs` | `native_docs` · `context7_when_needed` |
| `browser` | `native_http` · `playwright` |
| `database` | `native_db` · `dbhub_read_only` |
| `security` | `native_security` · `codeql` · `semgrep` · `github_secret_controls` · `dependency_review` |
| `polyglot` | `core-code` · `schema_abi` · `boundary_tests` |
<!-- END generated: tool-profiles -->

## Routing command

```bash
python scripts/atlas.py route path/to/file.py
python scripts/atlas.py route path/to/file.rs
python scripts/atlas.py route path/to/schema.sql
```

Do not route a task to an MCP solely because an MCP exists. Route by capability need.
