# MODEL.md

**Control plane version: 2.13.0**

Canonical model-aware operating layer. **The runtime roster is generated**, so this line no longer
names them in prose:

<!-- BEGIN generated: runtimes (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/model_routes` and `runtime_roles`. The hand-written version of
this roster named seven runtimes in a sentence and omitted the two verification runtimes
those declarations name, which is how a roster disagrees with the thing it describes.

| runtime | routed for | declared role | adapter |
|---|---|---|---|
| `claude` | `architecture` · `research` | — | [models/claude](models/claude/README.md) |
| `cli` | — | `deterministic_local_harness` | — |
| `cursor` | `interactive_edit` | — | [models/cursor](models/cursor/README.md) |
| `generic_llm` | `research` | — | — |
| `github_actions` | `verification` | `authoritative_repository_verification` | — |
| `hermes` | `tool_orchestration` | — | [models/hermes](models/hermes/README.md) |
| `native_toolchain` | `verification` | — | — |
| `openai_codex` | `architecture` · `deterministic_repo_edit` | — | — |
| `opencode` | `deterministic_repo_edit` · `terminal_parallelism` | `terminal_agent_workspace` | [models/opencode](models/opencode/README.md) |
| `vscode` | `interactive_edit` | `interactive_ide_agent_host` | [models/vscode](models/vscode/README.md) |
<!-- END generated: runtimes -->

> **Agent/model directive:** Read `MODEL.md` → `docs/INDEX.md` → `atlas.yaml` before acting. Identify the goal, artifact language, boundary, task profile, required tools, and verification gate. Load only the context needed for that route. Prefer the smallest capable model and tool surface. Be creative inside hard constraints, not around them. Preserve invariants, minimize unnecessary code, and maximize durable capability per line changed. Native compiler/runtime/test tooling outranks model confidence. MCP/connectors are scoped capabilities, never substitutes for repository truth. Never claim completion without the repository verification gate.

## Operating order

`goal → route → language pack → tool manifest → boundary → task profile → model/runtime → native tools → focused MCP/connector → edit → narrow verify → full verify → record`

## Model/runtime routing

| Runtime | Best use | Route rule |
|---|---|---|
| Claude | large-context architecture, code archaeology, cross-file reasoning | load architecture + affected language/boundary cards; avoid whole-repo context by default |
| Cursor | interactive IDE edits, fast local iteration | use path-scoped instructions and native diagnostics; keep edits narrow |
| OpenAI/Codex | deterministic repository tasks, refactors, tests, tool-driven implementation | follow Atlas route and verification commands; prefer exact file/symbol operations |
| OpenCode | terminal-centric workflows, local CLI harnesses, parallel worktrees | pair with deterministic scripts and explicit worktree ownership |
| Hermes | agent/tool orchestration experiments | narrow tools, explicit budgets, sandbox, audit, approval for high-impact actions |
| VS Code | debugger/LSP/test/profile cockpit | use language-native debugger and diagnostics; IDE state is not enforcement |
| Generic LLM | research, drafting, low-risk analysis | no write authority unless a task route and verifier exist |

Model names/providers are intentionally not hard-coded here. Provider selection belongs in the task/runtime configuration so the repository stays portable.

## Context economy

- Load the relevant language `README.md`, `OPERATING.md`, and `tools.yaml`, not every language.
- Load boundary docs only when the task crosses that boundary.
- Prefer symbols, tests, schemas, and manifests over whole-file dumps.
- Reuse existing tool output instead of re-querying the same source.
- Summarize completed investigation into a durable artifact when it will prevent repeated context cost.
- Do not compress away invariants merely to reduce tokens.

## Dynamic verification gates

Atlas selects the smallest sufficient verification surface from the task. These are required gates, not suggestions:

<!-- BEGIN generated: verification-gates (python scripts/atlas.py index --write) -->
```text
source_change      -> formatter + compiler_or_typechecker + unit_tests
api_change         -> schema_validation + contract_tests + endpoint_tests + compatibility_check
dependency_change  -> dependency_graph + dependency_review + vulnerability_scan + tests
security_sensitive -> codeql + secret_scan + static_analysis + tests
concurrency_change -> race_detection + cancellation_tests + timeout_tests + stress_test
performance_change -> benchmark + profiler + representative_workload + regression_threshold
retrieval_change   -> chunk_boundary_test + freshness_stamp + hybrid_recall_check + citation_check
quantum_change     -> simulator_run + shot_count_declared + noise_model_declared + resource_estimate + classical_baseline_comparison
```
<!-- END generated: verification-gates -->

Verification tiers:

`fast → standard → deep → release`

Escalate by risk; do not run every expensive tool for every edit. Native language tooling is authoritative. GitHub security tooling provides independent evidence.

## Findings policy

<!-- BEGIN generated: severity (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/verification_policy`.

| class | effect on a merge |
|---|---|
| `blocker` | `merge_blocking` |
| `error` | `merge_blocking` |
| `warning` | `non_blocking_but_actionable` |
| `info` | `report_only` |
| `baseline` | `tracked_only_existing_findings` |

**Baseline rule:** `new_findings_must_not_be_absorbed_into_baseline`. A pack may declare `policy.warnings: blocking` in its own
manifest, which is the one thing that changes the answer for that route.
<!-- END generated: severity -->

**This list drifted while it was prose:** it said warnings are "normally" non-blocking while
`atlas.yaml` says `non_blocking_but_actionable` and the manifest schema lets a pack declare
`blocking` — three documents, three answers to "can a warning block a merge".

The objective is **signal without warning fatigue**: fix newly introduced defects, track legitimate debt, and keep the baseline shrinking.

## Multi-language design

Choose a language by the guarantee it contributes. A polyglot system must have an explicit ownership boundary: schema/API/ABI/data format, lifecycle, timeout, error model, version policy, and verification. If two languages duplicate the same responsibility without a measured reason, simplify.

## MCP / connector discipline

Use MCP/connectors only for capabilities the native repository toolchain does not already provide. Prefer one focused call over a chain of generic calls. Treat external tool results as evidence, not truth, and verify the resulting code locally/CI. For GitHub state, use the GitHub integration; for language semantics, use official language references; for databases, use the database's native tooling.

## Security / mutation

No unbounded memory, queue, cache, retry, recursion, payload, agent loop, or tool-call surface. External inputs are schema-validated. High-impact writes require explicit scope and rollback. Follow `PREVENT → DETECT → ISOLATE → VERSION → RECOVER`.

## Definition of done

A change is done only when its acceptance test passes, the affected language-native checks pass, the applicable task-required gates pass, boundary tests pass when relevant, security/dependency checks pass when relevant, and Atlas remains consistent. If verification cannot be run, state exactly what remains unverified.

See `atlas.yaml`, `tools/README.md`, `wiki/TOOL-ORCHESTRATION.md`, `docs/GITHUB-BACKEND.md`, and the relevant `languages/<route>/OPERATING.md` + `tools.yaml`.
