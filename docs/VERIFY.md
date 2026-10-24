# Verification

**The gate names a requirement; the manifest names the tool.** This page used to list commands —
`pyright`, `staticcheck`, `npm test` — and every one of them disagreed with the pack that owns the
role. It was also the canonical verification document for every route while covering four of them.
Both defects have the same cause: a tool name written into prose, where nothing can check it.

So the rule here is narrow and absolute: **this page carries gates and order. Tool names live in
`languages/<route>/tools.yaml`, and nowhere else.**

```bash
python scripts/atlas.py plan path/to/file.ext --task debugging --change source_change --json
```

That answers, for one artifact: the route, the task profile, the tools the pack declares, and the
gates the change class requires. Run it instead of reading a list.

## The gates, the tiers and the severity classes

<!-- BEGIN generated: gate-detail (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/verification_policy`. The gate names a REQUIREMENT; the tool that
satisfies it is declared per route in `languages/<route>/tools.yaml`, which is the only
place a tool name lives.

| change class | what it requires |
|---|---|
| `source_change` | `formatter` · `compiler_or_typechecker` · `unit_tests` |
| `api_change` | `schema_validation` · `contract_tests` · `endpoint_tests` · `compatibility_check` |
| `dependency_change` | `dependency_graph` · `dependency_review` · `vulnerability_scan` · `tests` |
| `security_sensitive` | `codeql` · `secret_scan` · `static_analysis` · `tests` |
| `concurrency_change` | `race_detection` · `cancellation_tests` · `timeout_tests` · `stress_test` |
| `performance_change` | `benchmark` · `profiler` · `representative_workload` · `regression_threshold` |
| `retrieval_change` | `chunk_boundary_test` · `freshness_stamp` · `hybrid_recall_check` · `citation_check` |

Tiers, cheapest sufficient first — each includes the one before it:

| tier | adds |
|---|---|
| `fast` | `formatter` · `compiler_or_typechecker` · `focused_tests` |
| `standard` | `fast` · `static_analysis` · `applicable_security_and_dependency_checks` |
| `deep` | `standard` · `property_or_fuzz` · `mutation_if_mature` · `performance_if_relevant` |
| `release` | `deep` · `integration_tests` · `artifact_verification` · `supply_chain_verification` |

Severity, and what each one does to a merge:

| class | effect |
|---|---|
| `blocker` | `merge_blocking` |
| `error` | `merge_blocking` |
| `warning` | `non_blocking_but_actionable` |
| `info` | `report_only` |
| `baseline` | `tracked_only_existing_findings` |
<!-- END generated: gate-detail -->

## How to satisfy a gate without knowing the language

Every gate above is a requirement on evidence, not on a command. The pack supplies the command:

1. **Route the artifact.** `atlas.py route <path>` gives the pack, its operating card and its
   manifest, and says which precedence rule resolved it.
2. **Read the manifest's `authority` block** for the role the gate names — `formatter`,
   `compiler_or_runtime`, `test`, `security`, `profiler`. A role reading `none` means no
   established tool exists; that is an answer, not a gap to fill with a guess.
3. **Run it, and judge on the exit code.** Never on a line of output: one harness printed
   "54/54 pass" over seven real failures.
4. **Print the count.** A clean pass and an empty pass must not look identical — a suite that ran
   zero tests exits 0.

## What the repository verifies about itself

| instrument | answers |
|---|---|
| `python scripts/verify.py` | does every gate in `verification_policy/done_set` pass — PASS, FAIL or NOT RUN per gate, exit 0 only when all pass? |
| `python scripts/atlas.py check` | does the tree still satisfy its own contract? |
| `python scripts/atlas_test.py` | does the contract still fail on a planted defect? |
| `python scripts/astshape.py` | any duplicate AST structures, blobs or over-nesting? |
| `python scripts/exrun.py` | does every example still run and hold its own assertions? |
| `python scripts/packprobe.py --mode smoke` | which declared commands exist and run here? |
| `python scripts/ghaudit.py` | do the live GitHub controls match the declaration? |
| `python scripts/atlas.py doctor` | can this machine run the instruments at all? |

Each one names, in `atlas.yaml/instruments`, what it does **not** prove and who closes that.

## Running CI locally, and what CI skips

`.github/ci-local.sh` replays the `run:` steps of the jobs in `.github/workflows/atlas-ci.yml`, in
order, in a throwaway virtualenv. It reads the workflow, so it cannot drift from it.

```bash
.github/ci-local.sh                  # fast, exercises, mutation: everything `Contract` waits on
.github/ci-local.sh fast             # lint, format, type check, workflow lint and audit, `atlas.py check`
.github/ci-local.sh --install-hook   # opt-in pre-push hook running `fast`; --uninstall-hook removes it
```

The hook is never installed for you. A step whose tool is not on PATH prints SKIP, never PASS.

In CI, `Contract` is the required check. It runs no gate itself: it passes only when `Fast checks`,
`Mutation suite`, `Exercises` and `Edge coverage` all passed. `Fast checks` and `Exercises` start
together, and `Mutation suite` starts only once `Fast checks` passes, so a lint or type error shows
up in about a minute instead of after the mutation suite. Nothing in Atlas CI is
skipped by path. ClusterFuzzLite, which is not required, runs only when a pull request touches
`fuzz/`, `scripts/`, `languages/`, `config/`, `atlas.yaml` or `.clusterfuzzlite/`. Polyglot
examples run on a weekly schedule only.

## The order that makes a failure legible

```text
reproduce -> isolate -> root cause -> fix -> targeted verify -> broader verify -> inspect the diff
```

**Never repair forward through a failing gate.** A fix that makes a symptom move downstream is a
defect with a new address, and the gate that would have caught it is now the one you disabled.
