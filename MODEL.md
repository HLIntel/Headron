# MODEL.md

**Control plane version: 3.23.1**

Canonical model-aware operating layer. **The runtime roster is generated**, so this line no longer
names them in prose:

<!-- BEGIN generated: runtimes (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/model_routes` and `runtime_roles`. The hand-written version of
this roster named seven runtimes in a sentence and omitted the two verification runtimes
those declarations name, which is how a roster disagrees with the thing it describes.

| runtime | routed for | declared role | adapter |
|---|---|---|---|
| `chat` | `ideation` · `research` | — | [models/chat](models/chat/README.md) |
| `claude` | `architecture` · `research` | — | [models/claude](models/claude/README.md) |
| `cli` | — | `deterministic_local_harness` | — |
| `cursor` | `interactive_edit` | — | [models/cursor](models/cursor/README.md) |
| `generic_llm` | `research` | — | [models/llm](models/llm/README.md) |
| `github_actions` | `verification` | `authoritative_repository_verification` | — |
| `hermes` | `tool_orchestration` | — | [models/hermes](models/hermes/README.md) |
| `native_toolchain` | `verification` | `authoritative_language_verification` | — |
| `openai_codex` | `architecture` · `deterministic_repo_edit` | — | [models/openai](models/openai/README.md) |
| `opencode` | `deterministic_repo_edit` · `terminal_parallelism` | `terminal_agent_workspace` | [models/opencode](models/opencode/README.md) |
| `vscode` | `interactive_edit` | `interactive_ide_agent_host` | [models/vscode](models/vscode/README.md) |
| `zed` | — | `multi_agent_host` | [models/zed](models/zed/README.md) |
<!-- END generated: runtimes -->

> **Agent/model directive:** Ask before reading: `atlas gate <file> <gate>` for one command,
> `atlas route <file>` for the pack, then load only what the answer names. Prefer the smallest
> capable model and tool surface; be creative inside hard constraints, not around them. Native
> compiler, runtime and test tools outrank model confidence. MCP servers are scoped capabilities,
> never repository truth. Never claim done without the verification gate.

## Operating order

`goal → route → language pack → tool manifest → boundary → task profile → model/runtime → native tools → focused MCP/connector → edit → narrow verify → full verify → record`

## Model/runtime routing

Each runtime's route and adapter are in the generated roster above; what each loads is generated in
the README. Provider and model names stay out of this file so the repository stays portable.

## Context economy

- Load one pack's `README.md`, `OPERATING.md` and `tools.yaml`, never every language.
- Load boundary docs only when the task crosses that boundary.
- Prefer symbols, tests, schemas and manifests over whole-file dumps; reuse tool output.
- Record finished investigation where it prevents repeating the same context cost.
- Never compress away an invariant to save tokens.

## Dynamic verification gates

Required gates per change class are generated once, in the README's Dynamic verification section;
`atlas plan <file> --change <class>` answers for one change.

Verification tiers:

`fast → standard → deep → release`

Escalate by risk, not by habit. Native language tooling is authoritative; GitHub security tooling is independent evidence.

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

Generated, because as prose three documents gave three answers to "can a warning block a merge".

The objective is **signal without fatigue**: fix new defects, track real debt, shrink the baseline.

## Multi-language design

Choose a language by the guarantee it adds. A polyglot boundary names its owner for schema/API/ABI/data format, lifecycle, timeout, error model, versioning and verification. Two languages owning one responsibility without a measured reason: simplify.

## MCP / connector discipline

Use MCP only for what the native toolchain cannot do; one focused call beats a chain. External results are evidence, not truth: verify locally or in CI. GitHub state comes from GitHub, language semantics from official references, databases from their native tools.

## Security / mutation

Nothing unbounded: memory, queue, cache, retry, recursion, payload, agent loop, tool calls. External input is schema-validated; high-impact writes need scope and rollback. `PREVENT → DETECT → ISOLATE → VERSION → RECOVER`.

## Definition of done

Done means: the acceptance test, the affected native checks and the task's required gates pass, plus boundary and security/dependency checks where relevant, and `atlas check` stays green. What could not be verified is stated exactly.

See `atlas.yaml`, `tools/README.md`, `wiki/TOOL-ORCHESTRATION.md`, `docs/GITHUB-BACKEND.md`, and the relevant `languages/<route>/OPERATING.md` + `tools.yaml`.
