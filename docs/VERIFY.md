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
| `python scripts/verify.py --changed [--change <class>]` | fast loop: runs only the gates mapped to the changed files and change class in seconds |
| `python scripts/atlas.py check` | does the tree still satisfy its own contract? |
| `python scripts/atlas_test.py` | does the contract still fail on a seeded defect? |
| `python scripts/astshape.py` | any duplicate AST structures, blobs or over-nesting? |
| `python scripts/exrun.py` | does every example still run and hold its own assertions? |
| `python scripts/packprobe.py --mode smoke` | which declared commands exist and run here? |
| `python scripts/ghaudit.py` | do the live GitHub controls match the declaration? |
| `python scripts/atlas.py doctor` | can this machine run the instruments at all? |

Each one names, in `atlas.yaml/instruments`, what it does **not** prove and who closes that.

## Running CI locally, and what CI skips

`headron ci` (the same as `.github/ci-local.sh`) runs the jobs `scripts/cipipeline.py` declares:
Python steps, each a bounded microprogram, run as one graph in a throwaway virtualenv. No YAML
is translated and no hosted runner starts them; a landing posts the `local-ci` status from this run.

```bash
.github/ci-local.sh                  # fast, exercises, mutation: everything `Contract` waits on
.github/ci-local.sh fast             # lint, format, type check, workflow lint and audit, `atlas.py check`
.github/ci-local.sh --pipeline polyglot   # the example packs; `--pipeline fuzz` runs the atheris campaign
.github/ci-local.sh --plan           # the units a run would start, in order; runs nothing
.github/ci-local.sh --install-hook   # opt-in pre-push hook running `fast`; --uninstall-hook removes it
```

The hook is never installed for you. A step whose tool is not on PATH answers unknown with what to do, never PASS.

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

## Glossary

House words, each with its plain meaning. A name in code font is a wire name (a CLI verb, flag,
file or JSON key) and keeps its spelling; the prose around it uses the plain term.

| Term | Plain meaning |
|---|---|
| atlas (`atlas.yaml`) | the single machine-readable contract every check reads |
| route | the language or area a file belongs to, resolved from its path |
| pack | one language's guide, operating card and `tools.yaml` |
| operating card (`operating_card`) | the short checklist section of a language guide |
| gate | a required check; a change is not done until its gates pass |
| instrument | a check or measurement declared in the atlas, with what it proves and does not prove |
| receipt | the proof record of one run: every gate's verdict, with the contract version |
| ledger | an append-only log of failures or successes, keyed by id |
| failure shape / success move | a recorded failure mode / a proven fix pattern |
| seeded defect (`planted`) | a fault injected on purpose to prove a check fails when it should (mutation testing) |
| topic branch (`lane`) | a one-task branch in its own worktree |
| land (`branchstate.py --land`) | merge: rebase, run the suite, push, open the pull request, arm auto-merge |
| ratchet | a limit that may only tighten |
| ladder / rung | an ordered list of fallbacks / one step on it |
| guard | a test that enforces one rule |
| mind (`headron mind`) | the orchestration API: classify a change, plan its gates, diagnose and recover a failure |
