<!-- AGENTS: do not read this page breadth-first. Start at .agent/bootstrap.json or llms.txt,
     then ask `python scripts/atlas.py gate <file> <gate>` — one command back. -->
<p align="center">
  <img src="docs/assets/thea.webp"
       alt="Thea — The Heartland Engineering Atlas · software development · AI agents" width="440">
</p>

<h1 align="center">Thea · The Heartland Engineering Atlas</h1>

<p align="center">
  <em>Route the change. Run the gate. Refuse what drifted.</em>
</p>

<p align="center">
  <a href="https://github.com/HeartlandTechnology/Code-Development/actions/workflows/atlas-ci.yml"><img
     src="https://github.com/HeartlandTechnology/Code-Development/actions/workflows/atlas-ci.yml/badge.svg?branch=main"
     alt="Atlas CI"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/HeartlandTechnology/Code-Development"><img
     src="https://api.securityscorecards.dev/projects/github.com/HeartlandTechnology/Code-Development/badge"
     alt="OpenSSF Scorecard"></a>
  <a href="https://github.com/HeartlandTechnology/Code-Development/actions/workflows/scorecard.yml"><img
     src="https://github.com/HeartlandTechnology/Code-Development/actions/workflows/scorecard.yml/badge.svg?branch=main"
     alt="OpenSSF Scorecard workflow"></a>
  <a href="LICENSE"><img
     src="https://img.shields.io/github/license/HeartlandTechnology/Code-Development"
     alt="licence"></a>
  <a href="https://github.com/HeartlandTechnology/Code-Development/releases/latest"><img
     src="https://img.shields.io/github/v/tag/HeartlandTechnology/Code-Development?label=contract"
     alt="contract version"></a>
</p>

<p align="center">
  <sub>Every badge is served by whoever measures it — none is typed here.
  <a href="docs/CERTIFICATION.md">What each one proves</a>.</sub>
</p>

<p align="center">
  <a href="docs/VERSIONING.md">contract v2.26.0</a> ·
  <a href="docs/INDEX.md">index</a> ·
  <a href="docs/CONSUMING.md">use it elsewhere</a> ·
  <a href="llms.txt">llms.txt</a> ·
  <a href="SECURITY.md">security</a> ·
  <a href="docs/CERTIFICATION.md">certification</a> ·
  <a href="https://github.com/HeartlandTechnology/Code-Development/releases">releases</a> ·
  <a href="LICENSE">MIT</a>
</p>

---

## What this is

**Thea, the Heartland Engineering Atlas, is the engineering control plane for [Heartland Technology](https://github.com/HeartlandTechnology):
one contract that Claude, Codex, Cursor, opencode and Zed all work under.** It decides where a
change goes, what must prove it and what an agent may do while making it — then enforces all
three, lands the result, and turns every defect it catches into a guard that refuses the next one.
Thirty-five language packs are one layer of it; the rest is routing, verification, an agent
harness, a landing pipeline and a failure ledger the build learns from.

**The objective:** software work that depends less on memory, convention and model judgment. Every
rule is a declaration something executes, and the build fails the moment an answer drifts from the
tree. **AI picks and runs the tools; the native tools decide whether code is valid** — "looks
correct" is never a verdict.

Six capabilities, one declaration, none able to disagree with the others:

| | |
|---|---|
| **Routing** | `atlas.yaml` holds every route, gate, process, control, budget and policy; `atlas route` returns the answer *and which precedence rule resolved it* |
| **Verification** | the change class picks the gates, and each gate resolves to a command the pack itself declares — **315 of 315 (pack, gate) pairs resolve**, none of them to silence |
| **35 language packs** | compiler, formatter, test runner, debugger, profiler and security tool per language — none loaded until a route names it |
| **Runtime adapters** | one generated body served as `CLAUDE.md`, `AGENTS.md` and `llms.txt`, plus an adapter each for Claude, Codex, Cursor, opencode, Zed, VS Code and Hermes: how the atlas loads there, and *the mistake that runtime makes* |
| **An agent harness** | a task contract with a schema, five controls that refuse rather than warn, a runner that writes the outcome into the record that planned it, and a hash-chained audit |
| **Error prevention** | 137 defect tests: each plants a real defect, asserts the contract refuses it, and restores the file — and each suite asserts its own case count |

You do not read it. You ask — `route`, `plan`, `process`, `do`, `pick`, `why` — and it answers as
prose for a person or as a schema-frozen record for a machine.

> ### Laws the build enforces, so nobody has to remember them
>
> **Route before reading. Every gate resolves to a command its pack declares. Every file is parsed
> once. Ambiguity is refused, never guessed. Every write is read back, and every step is judged by
> its result, not its exit code.** An agent spends its tokens on the change instead of hunting for
> the toolchain, and a defect that looks like success stops at the gate. Each law names the defect
> it was measured against: `atlas.yaml/parser_discipline` · `agent_failure_modes`.

### What it measurably buys you

Every figure below is produced by a named instrument in this repository and stamped with the
contract version it was measured at — re-run it rather than trusting the line.

| | measured | instrument |
|---|---|---|
| **Routing accuracy** | given the one gate `atlas gate` returns, a model answers **98.2%** correctly against **67.4%** asking blind — three models, K=1,140, chance baseline 0.0286 | `abtest.py` (v2.27.0) |
| **Token efficiency** | the one-gate answer uses **90% fewer** prompt tokens than reading every pack at the same 98.2%, **67% fewer** than handing over the whole manifest, and **52% fewer** than asking blind | `abtest.py` (v2.27.0) |
| **What a session pays** | a runtime loads **1,855 tokens** and nothing more until it routes; **98.3%** of the tree — 149 documents — loads only when a route names it | `contextcost.py` |
| **Gate coverage** | **315 of 315** (pack, gate) pairs resolve — 213 to a runnable command, 102 to a declared absence naming its closer, **0 to silence** | `atlas.py check` |
| **Error prevention** | **137 of 137** defect kinds caught — each planted, refused, then removed; nothing is left in the tree, and a skipped case cannot print a pass | `atlas_test.py`, `agent_test.py` |
| **Verify speed** | one check parses each YAML file **once** — it was **671** parses at v2.26.0 — and a budget derived from the tree fails any re-parse per lookup. Seconds are the instrument's to print | `atlas_test.py` |
| **Agent safety** | five controls that **refuse** rather than warn — path, command, budget, approval, audit — each naming the function that decides it | `agent_policy`, `agentrun.py` |
| **Install weight** | **184 KiB**, 11 modules, **one** runtime dependency; 16 instruments stay out of the wheel and no toolchain is installed by default | `contextcost.py` |

### Who it is for

- **Polyglot repositories** — one answer to *which toolchain owns this file and what must pass*.
- **Teams running several AI agents** — one contract, refusing controls, a bounded entry.
- **Strict security or supply-chain needs** — pinned, attested, audited against the live platform.
- **Codebases where stale docs cost money** — a document that drifts fails the build.
- **CI and consuming repos** — depend on ids frozen in a schema, never on rendered Markdown.

### What makes it different

- **One question, one call — with its evidence.** `atlas route <file>` returns the pack, card,
  manifest, label, lane and gates, and names *which precedence rule resolved it*, so an explicit
  match and a lucky guess never look alike. It also reports the rules it did **not** resolve.
- **Rules that may bend, and rules that may not — declared.** `governance_tiers` separates what
  refuses outright from what may move *if the move names what earned it*, because a bound that
  cannot move gets worked around instead of respected.
- **Nothing claimed that was not measured.** No count typed into prose, no claim carrying a date —
  it carries the contract version it was measured at. The entry cost, install footprint, function
  shape and example coverage are **ratchets that only fall**.
- **Mistakes are inventory.** What went wrong here is written down with its recurrence count and
  what refuses it now, because a shape seen twice is a missing rule.
- **It stays out of your way.** 184 KiB installed, one runtime dependency, no toolchain by
  default, policy pointed at rather than vendored.
- **What it is not:** an app framework or a runtime optimizer — it measures performance, it does
  not speed your app — and agent sandboxing still needs host isolation.

## Quickstart

```bash
python scripts/atlas.py route scripts/doctor.py           # which pack, card, manifest, lane, label
python scripts/atlas.py plan  scripts/doctor.py --task implementation --change source_change
python scripts/atlas.py process implementation            # a named process, end to end
python scripts/atlas.py do    scripts/doctor.py           # every action this file's pack can run
python scripts/atlas.py check                             # the exit code IS the verdict
python scripts/atlas.py doctor                            # can THIS machine run the instruments?
```

Add `--json` for a record instead of prose. Those records are frozen in
[tools/atlas-output.schema.json](tools/atlas-output.schema.json) and are the external API:
**depend on route ids, gate ids and manifest paths — never on rendered Markdown.** Using the atlas
elsewhere without vendoring it: [docs/CONSUMING.md](docs/CONSUMING.md).

## Start here — by what you are trying to do

| I want to… | Go here |
|---|---|
| **route one file** and get its toolchain | `atlas.py route` · [Code-specific routing](wiki/CODE-ROUTING.md) |
| **run a pack's own tool** on a file | `atlas.py do` · [Manifest contract](languages/PACK-TOOLS-SPEC.md) |
| **follow a named process** end to end | `atlas.py process` · [Verification](docs/VERIFY.md) |
| **pick a language**, or add one | [Languages](languages/ATLAS.md) · [Language packs](languages/README.md) · [Pack contract](languages/PACK-SPEC.md) |
| **know what a pack must contain** | [tools.schema.json](tools/tools.schema.json) · [Pack tools spec](languages/PACK-TOOLS-SPEC.md) |
| **run an agent under real controls** | [agent-task.schema.json](tools/agent-task.schema.json) · [Agent harness](systems/AGENT-HARNESS.md) |
| **run a language in production** | [Language operations](wiki/LANGUAGE-OPERATIONS.md) · [Systems](systems/README.md) |
| **choose or orchestrate tools** | [Tool orchestration](wiki/TOOL-ORCHESTRATION.md) · [MCP language matrix](integrations/MCP-LANGUAGE-MATRIX.md) |
| **choose a model or runtime** | [Models and runtimes](models/README.md) |
| **land a change**, or clean up a worktree | `branchstate.py --land` / `--sync` · [Branch/worktree model](wiki/BRANCH-WORKTREES.md) |
| **configure GitHub**, or see what is enforced | [GitHub backend](docs/GITHUB-BACKEND.md) · [Finalization](docs/GITHUB-FINALIZATION.md) · `ghaudit.py` |
| **understand WHY a rule here exists** | `atlas.py why` · [Engineering concepts](docs/ENGINEERING-CONCEPTS.md) |
| **report or handle a vulnerability** | [Security policy](SECURITY.md) |
| **read the background research** | [Research](research/ENGINEERING-RESEARCH.md) |
| **browse everything** | [Wiki](wiki/README.md) · [docs/INDEX.md](docs/INDEX.md) |

## If you are an agent

Do not read this repository breadth-first — that failure is named in
`atlas.yaml/context_policy/forbidden_default`. Parse
[.agent/bootstrap.json](.agent/bootstrap.json), then route, then load only what the route names.
**Ask `atlas gate <file> <gate>` first** — one command back, the cheapest answer and measured as
the most accurate. The entry a runtime loads before asking anything is in the table above, and
`scripts/contextcost.py` is the ratchet that keeps it there.

**Claude Code specifically:** `CLAUDE.md` loads by itself and is generated, so it cannot drift. Land
work with `python scripts/branchstate.py --land` — a bare `git push` of a lane is refused by
`.githooks/pre-push`, because a pushed branch nothing will merge looks finished and is not. Enable
an MCP server per task, never by default: it is paid for on every request, not the one using it.

**Three instruction conventions, one generated body:** [CLAUDE.md](CLAUDE.md),
[AGENTS.md](AGENTS.md) and [llms.txt](llms.txt). None can name a document that does not exist, and
`check` fails on drift. Packs declare toolchains; nothing here declares them *installed* —
`packprobe.py --mode smoke` is how you find out before planning around one.

## The failure it exists to prevent

**The expensive break is the one whose output is identical to success.** A guard that checked
nothing, a test that ran zero cases and a router that served an error as an answer all print
exactly what a working system prints. So the order is fixed: **make the break unrepresentable →
if it can still happen, make it impossible to be silent → only then detect it.**

Two were found here by causing them. A second `'.fs'` key moved every F# file to the Forth pack —
YAML keeps the *last* duplicate and reports nothing — so **every YAML read goes through a loader
that refuses duplicates, and a direct PyYAML call anywhere else fails the contract.** A mechanical re-indent wrote a harness file that no longer
compiled, twice, while the contract printed all of its counts — so **every tracked source and JSON
file must parse, and that check runs first.**

Neither was preventable by care. One sentence: **a tool that picks a winner where the input is
ambiguous, or reports success where it never looked, is worse than one that refuses.** Each with its sighting: [Engineering concepts](docs/ENGINEERING-CONCEPTS.md) · `atlas.py why`.

## Nothing here states a count it did not compute

A number typed into prose is stale the moment the tree moves, and the reader cannot see that it
moved. Every count below is generated from `atlas.yaml` and the tree, and `check` fails when a
block differs from what the tree would produce. Machine-specific numbers are not written down at
all — the instrument that answers them is named instead.

<!-- BEGIN generated: repository-facts (python scripts/atlas.py index --write) -->
| fact | value | derived from |
|---|---|---|
| contract version | **2.28.0** | `VERSION`, asserted identical in 7 other files |
| artifact extensions routed | **53** | `atlas.yaml/artifact_routes` |
| language routes | **35** | distinct targets of those extensions |
| tool manifests | **35** | `languages/<route>/tools.yaml`, validated against `tools/tools.schema.json` |
| declared tool entries | **362** | distinct entries per manifest, summed; `packprobe.py` classifies every one |
| entry kinds | **5** | `tools/tools.schema.json` `$defs.entry.x-kinds` |
| hard invariants | **31** | each CHECKED or DECLARED, never neither |
| instruments | **30** | `atlas.yaml/instruments`, each naming its own limits |
| verification gate classes | **8** | `atlas.yaml/verification_policy/profiles` |
| task profiles | **14** | `atlas.yaml/task_profiles` |
| python files in the harness | **30** | `scripts/*.py`, all linted by ruff |
<!-- END generated: repository-facts -->

## Instruments — what each one proves, and who closes what it does not

Every claim here is settled by a command, not by a badge. Each instrument declares `proves`,
`does_not_prove` and **`closed_by`** — what covers the limit it cannot — and `check` refuses one
that leaves the closer empty, so a blind spot with no owner is unrepresentable rather than
discouraged. The roster is generated from `atlas.yaml/instruments` into
[docs/CERTIFICATION.md](docs/CERTIFICATION.md); the count is in the facts block above.

## Hard invariants are owned, not listed

`atlas.yaml` declares the hard invariants. Each maps in `scripts/atlas.py` to either a CHECK that
fails the contract or a DECLARATION naming why this repository cannot check it and what would. An
invariant in neither list fails the contract, so the roster cannot quietly grow promises nobody
owns:

```bash
python scripts/atlas.py invariants
```

A declared blind spot is a promise to come back, not an exemption. The command prints the split
between enforced and declared on every run, so the size of that table is read from the run and
never from this page.

## The harness is tested

`scripts/atlas_test.py` plants a real defect on disk for every rule the contract claims to
enforce — a hand-edited generated block, a version skew, a manifest entry that is prose, a
bypassed YAML loader, a re-parse per lookup — asserts the check fails on each, and **restores the
file before the next case**, so no defect outlives its own test. It asserts its own case count,
because a harness that silently skips cases prints a full pass.

## Dynamic verification

The repository selects the smallest sufficient verification surface from the task and the risk.
Required gates are explicit:

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

Four severity classes: `blocker`/`error` block the merge; `warning` is visible and actionable but
normally non-blocking; `info` is report-only; `baseline` is limited to already-known findings, and
a new finding must never be hidden by baseline growth.

## Multi-language design, and learning one

Use a second language only when it contributes a distinct guarantee, runtime property, ecosystem
or performance characteristic — **define the boundary first**, then assign ownership. The pairings
and the boundary shapes are in
[systems/POLYGLOT-ENGINEERING.md](systems/POLYGLOT-ENGINEERING.md); `atlas pick` selects by need.

`atlas.py learn <language>` turns a pack's card and manifest into a mastery loop — read, trace,
reproduce, modify, break on purpose, verify, benchmark, record — so one language deepens at a
time. Prefer primary documentation to a copied summary: `none` in a manifest means no established
tool is known for that role, and `provenance` says what has not been confirmed against a running
toolchain.

## Codespaces

A codespace boots from [.devcontainer](.devcontainer/README.md) and exists to confirm ONE language
pack against a real toolchain — add that feature, probe it, remove it. Absence on a machine is a
fact about the machine.

## Languages

**35 routes**, each with a guide, an operating card and a tool manifest, and none of them loaded
until a route names one. Choose by problem shape rather than by popularity —
[languages/ATLAS.md](languages/ATLAS.md) — or ask: `atlas pick` lists the selection axes and
`atlas route <file>` resolves one file.

## Packages and dependencies

What this repository installs, what it refuses to install, and the one runtime dependency the
harness carries — generated into [docs/PACKAGE-CATALOG.md](docs/PACKAGE-CATALOG.md) from the
declaration, with the install footprint bounded as a ratchet by `scripts/contextcost.py`.

## Versions and releases

The version tracks the **contract**, not the content: adding a paragraph to a guide is not a
version change; changing what the harness enforces, what a route resolves to or what a gate
requires always is. One line per version is the only changelog, the same commit bumps every place
the string appears, and the release procedure ends in a tag — a version with no tag is a claim with
no artifact. See [docs/VERSIONING.md](docs/VERSIONING.md).

## About

Built by **Heartland Technology** and public on purpose: an atlas that needs a token to read cannot route
an agent that has none. The cost of that choice is one absolute rule — **no secret, credential,
private-project path or internal hostname enters this repository**, not in a file, not in an
example, not in history. Everything operational lives in a private repository; what lives here is
the method, and it is safe to hand this whole tree to an unknown agent.

Read [ABOUT.md](ABOUT.md) for the division between the two, and
[docs/ENGINEERING-CONCEPTS.md](docs/ENGINEERING-CONCEPTS.md) for why each rule exists.
Contributions follow the same contract as any change: `check` and `atlas_test.py` must pass, and
the pull request template asks what would prove the goal met.

Licensed under the [MIT License](LICENSE).
