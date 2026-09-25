<p align="center">
  <img src="docs/assets/heartland-technology.webp"
       alt="Heartland Technology — Code-Development" width="340">
</p>

<h1 align="center">The Heartland Engineering Atlas</h1>

<p align="center">
  <em>Route the artifact. Verify the change. Print every count.</em>
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

**The Heartland Engineering Atlas is the shared engineering substrate for [Heartland Technology](https://github.com/HeartlandTechnology):
one repository that decides how every other repository is built, verified and changed — and
answers by command rather than by document.**

Engineering knowledge rots the same way everywhere. A standard is written down, the code moves,
and the document keeps saying what used to be true — confidently, in prose, where nothing can
check it. This repository inverts that: **every rule is a declaration something executes, and the
build fails when an answer it gives has drifted from the tree.**

Three parts that cannot disagree with each other:

| | |
|---|---|
| **One declaration** | `atlas.yaml` — every route, gate, process, control, budget and policy in one file |
| **One harness** | Python that *enforces* it; each instrument declares what it does **not** prove and who closes that gap, and an empty closer fails the build |
| **35 language packs** | each declaring its own compiler, formatter, test runner, debugger, profiler and security tool — none loaded until a route names it |

You do not read it. You ask — `route`, `plan`, `process`, `do`, `pick`, `why` — and it answers as
prose for a person or as a schema-frozen record for a machine.

> ### It refuses its own work, and that is the product
>
> These guards did not catch a hypothetical. **In building this repository they refused a
> duplicate AST structure, two tracked configs that did not parse, a version that had drifted
> across five releases, and a parser whose trailing-comma cleanup silently rewrote data inside
> string literals — found by a fuzz target on its first run.** One guard was itself wrong and
> stripped 76 working links before a printed count exposed it; it was narrowed rather than
> silenced. Every shape is recorded in `atlas.yaml/agent_failure_modes` with **what it looks like
> from outside** — and all of them look like success.

### What it measurably buys you

Every figure below is produced by a named instrument in this repository and stamped with the
contract version it was measured at — re-run it rather than trusting the line.

| | measured | instrument |
|---|---|---|
| **Routing accuracy** | a model answers **98.5%** correctly with a route, against **47–72%** asking blind — replicated on two models, 68 questions each | `abtest.py` (v2.26.0) |
| **Token efficiency** | the same accuracy as handing over *every* pack's declarations, at **29.4%** of the prompt tokens. More context scored *worse* | `abtest.py` (v2.26.0) |
| **Session entry cost** | a runtime is handed a router and a bounded entry path, not a repository — and the budget is a ratchet that only falls | `contextcost.py` |
| **Error prevention** | every rule ships a planted defect that must fail, and the suites assert their own case counts, so a skipped case cannot print a pass | `atlas_test.py`, `agent_test.py` |
| **Agent safety** | five controls that **refuse** rather than warn — path, command, budget, approval, audit — each naming the function that decides it | `agent_policy`, `agentrun.py` |
| **Multi-language reach** | one command runs whatever *that* pack declares, across every route; the unit-test gate resolves for **34 of 35** packs | `atlas do`, `gate_tools` |
| **Install weight** | one runtime dependency, no toolchain installed by default, policy pointed at rather than vendored | `contextcost.py` |

**The error-prevention claim is not theoretical.** The guards in this repository refuse *its own*
work routinely: a duplicate AST structure, two tracked configs that did not parse, a version that
had drifted across five releases, a hand-written parser whose trailing-comma cleanup silently
rewrote data inside string literals — that last one found by a fuzz target on its first run.
What each one looks like from outside is recorded in `atlas.yaml/agent_failure_modes`; **all of
them look like success.**

### Who it is for

- **Engineers on a polyglot codebase** — one answer to *"which toolchain owns this file, and what
  must pass before it merges"*, instead of thirty-five conventions held in somebody's head.
  `atlas do <file> test` runs whatever *that* pack declares: one implementation, every language.
- **AI coding agents** — handed a router and a bounded entry path rather than a repository, and
  run under a task contract whose path, command, budget, approval and audit controls **refuse**
  rather than warn. Each names the function that decides it; a control with no enforcer fails the
  build.
- **CI and consuming repositories** — pin a version, call a reusable workflow, depend on route ids
  and gate ids frozen in a schema. Never on rendered Markdown.

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
- **Mistakes are inventory, not embarrassment.** What went wrong here is written down with its
  recurrence count and what refuses it now, because a shape seen twice is a missing rule.
- **It stays out of your way.** ~160 KiB installed, one runtime dependency, no toolchain installed
  by default, policy pointed at rather than vendored.

Released under MIT. Contract version and changelog: [docs/VERSIONING.md](docs/VERSIONING.md).

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
| **branch, merge, or clean up a worktree** | [Branch/worktree model](wiki/BRANCH-WORKTREES.md) · [Labels and tags](wiki/LABELS-TAGS.md) |
| **configure GitHub**, or see what is enforced | [GitHub backend](docs/GITHUB-BACKEND.md) · [Finalization](docs/GITHUB-FINALIZATION.md) · `ghaudit.py` |
| **understand WHY a rule here exists** | `atlas.py why` · [Engineering concepts](docs/ENGINEERING-CONCEPTS.md) |
| **report or handle a vulnerability** | [Security policy](SECURITY.md) |
| **read the background research** | [Research](research/ENGINEERING-RESEARCH.md) |
| **browse everything** | [Wiki](wiki/README.md) · [docs/INDEX.md](docs/INDEX.md) |

## If you are an agent

Do not read this repository breadth-first — that failure is named in
`atlas.yaml/context_policy/forbidden_default`. Parse
[.agent/bootstrap.json](.agent/bootstrap.json), then route, then load only what the route names.
A runtime is handed **~1,700 tokens** before it asks anything; everything else is behind a route,
and `scripts/contextcost.py` is the ratchet that keeps it that way.

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
YAML keeps the *last* duplicate and reports nothing — so **every YAML read now goes through a
loader that refuses duplicates.** A mechanical re-indent wrote a harness file that no longer
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
| contract version | **2.26.0** | `VERSION`, asserted identical in 7 other files |
| artifact extensions routed | **53** | `atlas.yaml/artifact_routes` |
| language routes | **35** | distinct targets of those extensions |
| tool manifests | **35** | `languages/<route>/tools.yaml`, validated against `tools/tools.schema.json` |
| declared tool entries | **362** | distinct entries per manifest, summed; `packprobe.py` classifies every one |
| entry kinds | **5** | `tools/tools.schema.json` `$defs.entry.x-kinds` |
| hard invariants | **31** | each CHECKED or DECLARED, never neither |
| instruments | **27** | `atlas.yaml/instruments`, each naming its own limits |
| verification gate classes | **8** | `atlas.yaml/verification_policy/profiles` |
| task profiles | **14** | `atlas.yaml/task_profiles` |
| python files in the harness | **27** | `scripts/*.py`, all linted by ruff |
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

`scripts/atlas_test.py` plants a real defect on disk for each rule the contract claims to enforce
— a hand-edited generated block, a version skew, a manifest with a missing key or an entry that is
prose, a route whose label is not in the catalog, an instrument with no closer — and asserts the
check fails on each; that a clean tree passes; that `index --write` repairs the drift it reports
and is idempotent; and that the route edge cases behave. It asserts its own case count, because a
harness that silently skips cases prints a full pass. Where `jsonschema` is installed it also
cross-checks this repository's own validator against that library. CI runs it before the contract.

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

Four severity classes: `blocker`/`error` are merge-blocking; `warning` is visible and actionable
but normally non-blocking; `info` is report-only; `baseline` is limited to already-known findings.
New findings must never be hidden by baseline growth.

## Assurance chain

```text
GOAL -> route -> native toolchain -> tool manifest -> repository context
     -> boundary contract -> targeted capability -> security/dependency analysis
     -> independent verification -> CI
```

Do not load every tool, MCP or language guide. Activate only the capability the goal or the
failure class needs — an enabled MCP server is paid for on every request, not on the one that
uses it.

## Multi-language design

Use a second language only when it contributes a distinct guarantee, runtime property, ecosystem
or performance characteristic. Define the boundary first, then assign ownership.

```text
Python -> Rust/C++/Mojo native core
TypeScript -> Go/Rust service
Python/Julia -> native/accelerator component
local process -> bounded stdio/schema
service -> versioned RPC/message schema
portable component -> WebAssembly/WASI
```

See [systems/POLYGLOT-ENGINEERING.md](systems/POLYGLOT-ENGINEERING.md).

## Learning and mastery

```text
read reference -> trace real code -> reproduce a tiny example -> modify -> break on purpose
 -> verify -> benchmark -> record the lesson
```

`python scripts/atlas.py learn rust` turns a pack's operating card and manifest into that loop, so
one language deepens at a time. Prefer primary documentation to a copied summary; `none` in a
manifest means no established tool is known for that role, and `provenance` says what has not been
confirmed against a running toolchain.

## Branches and worktrees

One checkout is the main worktree and is never a branch lane. Lanes merge into the default branch
only, by rebase then fast-forward; a lane with `ahead=0` against `main` is finished, and the
worktree is removed in the session that merges it. Full rules, including the sweep that prints what
is still on disk: [wiki/BRANCH-WORKTREES.md](wiki/BRANCH-WORKTREES.md).

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
