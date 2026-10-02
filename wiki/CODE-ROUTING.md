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
Derived from `atlas.yaml/artifact_routes`. The authority is each route's `tools.yaml`, linked
with its card in the [language index](../languages/README.md#language-index).

| artifact | route |
|---|---|
| `.bash` `.sh` | `bash` |
| `.bqn` | `bqn` |
| `.c` `.h` | `c` |
| `.carbon` | `carbon` |
| `.chpl` | `chapel` |
|  | `cloudflare` |
| `.cc` `.cpp` `.hpp` | `cpp` |
| `.cu` `.cuh` | `cuda` |
| `.ex` `.exs` | `elixir` |
| `.4th` `.fth` | `forth` |
| `.fs` `.fsx` | `fsharp` |
| `.fut` | `futhark` |
| `.gleam` | `gleam` |
| `.go` | `go` |
| `.ha` | `hare` |
| `.hs` `.lhs` | `haskell` |
| `.jl` | `julia` |
| `.lean` | `lean4` |
| `.mojo` | `mojo` |
| `.nim` | `nim` |
| `.ml` `.mli` | `ocaml` |
| `.odin` | `odin` |
| `.py` `.pyi` | `python` |
| `.qs` | `quantum/qsharp` |
| `.slq` | `quantum/silq` |
| `.r` | `r` |
| `.roc` | `roc` |
| `.rs` | `rust` |
| `.sc` `.scala` | `scala` |
| `.sql` | `sql` |
| `.swift` | `swift` |
| `.cjs` `.js` `.jsx` `.mjs` `.ts` `.tsx` | `typescript` |
| `.ua` | `uiua` |
| `.v` | `v` |
| `.wasm` `.wat` | `webassembly` |
| `.zig` | `zig` |
<!-- END generated: route-table -->

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
| `autonomous_agent` | `narrow_tools` · `sandbox` · `budget` · `approval` · `effects` · `audit` |
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

## What enforces this now

- `atlas.py route <path> --json` returns the answer AND the precedence rule that resolved it, with
  its evidence — an explicit match and a lucky guess must not look alike. The record also lists
  every declared precedence rule with whether THIS router resolved it, because four of six belong
  to the caller and a consumer reading only `resolved_by` could not tell.
- `atlas.py pick` selects a pack by NEED rather than by name: `language_selection` gives each axis
  what it is for, the packs that answer it, their maturity, and — the half that does the work —
  when NOT to reach for it. `check` refuses a pack in no axis, because one reachable only by
  already knowing its name is recall rather than selection.
- `atlas.py do <file> <action>` runs whatever that pack declares, through `pack_actions`. One
  implementation, every language.
- The route ambiguity matrix in `atlas_test.py` asserts the tricky cases as BEHAVIOUR: extension
  over pack directory, a symlink, a traversal that lands back inside, the pack index, and the
  historical `.fs` collision.
