<p align="center">
  <img src="docs/assets/apian-software-code-development-01d337af.webp"
       alt="Apian Software — Code-Development" width="340">
</p>

<h1 align="center">The Engineering Atlas</h1>

<p align="center">
  <em>Route the artifact. Verify the change. Print every count.</em>
</p>

<p align="center">
  <a href="https://github.com/ApianSoftware/Code-Development/actions/workflows/atlas-ci.yml"><img
     src="https://github.com/ApianSoftware/Code-Development/actions/workflows/atlas-ci.yml/badge.svg?branch=main"
     alt="Atlas CI"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/ApianSoftware/Code-Development"><img
     src="https://api.securityscorecards.dev/projects/github.com/ApianSoftware/Code-Development/badge"
     alt="OpenSSF Scorecard"></a>
  <a href="https://github.com/ApianSoftware/Code-Development/actions/workflows/scorecard.yml"><img
     src="https://github.com/ApianSoftware/Code-Development/actions/workflows/scorecard.yml/badge.svg?branch=main"
     alt="OpenSSF Scorecard workflow"></a>
  <a href="LICENSE"><img
     src="https://img.shields.io/github/license/ApianSoftware/Code-Development"
     alt="licence"></a>
  <a href="https://github.com/ApianSoftware/Code-Development/releases/latest"><img
     src="https://img.shields.io/github/v/tag/ApianSoftware/Code-Development?label=contract"
     alt="contract version"></a>
</p>

<p align="center">
  <sub>Every badge is served by whoever measures it — none is a picture or a number typed into
  this repository, and the licence and version badges read the repository itself rather than a
  string in this file. What each one proves, per check, and what would raise it:
  <a href="docs/CERTIFICATION.md">certification</a>.</sub>
</p>

<p align="center">
  <a href="docs/VERSIONING.md">contract v2.3.1</a> ·
  <a href="https://github.com/ApianSoftware/Code-Development/releases">releases</a> ·
  <a href="docs/INDEX.md">index</a> ·
  <a href="llms.txt">llms.txt</a> ·
  <a href="SECURITY.md">security</a> ·
  <a href="docs/CERTIFICATION.md">certification</a> ·
  <a href="LICENSE">MIT</a>
</p>

---

A model-aware engineering atlas for polyglot programming, AI coding agents, Git and GitHub, APIs,
MCP connectors, data and research, storage, backends, performance, security, reliability, routing
and verification. It is a **routing table with a contract**, not a manual: you ask it where to go,
it answers in one call, and a harness fails the build when any answer it gives has drifted from
the tree.

> ### Never a silent break
>
> **The expensive break is the one whose output is identical to success.** A guard that checked
> nothing, a test that ran zero cases, a backup that pushed nowhere and a router that served an
> error as an answer all printed exactly what a working system prints.
>
> So the order is fixed: **make the break unrepresentable → if it can still happen, make it
> impossible to be silent → only then detect it.** A detector added for a fault that could have
> been deleted is maintenance forever. Each mechanism with the sighting that produced it:
> [Anti-break, three tiers](docs/ENGINEERING-CONCEPTS.md).

## If you are an agent, start here

Do not read this repository breadth-first. **Ask it where to go, then read only what it names.**

```bash
python scripts/atlas.py route path/to/file.ext          # language, card, manifest, label, lane, gates
python scripts/atlas.py route path/to/file.ext --json    # the same answer as a record
python scripts/atlas.py plan  path/to/file.ext --task debugging --change source_change --json
python scripts/atlas.py check                            # the exit code IS the verdict
python scripts/atlas.py doctor                           # can this machine run each instrument?
python scripts/atlas_test.py                             # does the contract still catch a planted defect?
python scripts/packprobe.py --mode smoke                 # which declared commands actually run here
python scripts/ghaudit.py                                # do the live GitHub controls match the declaration?
```

`route` is the entry point and answers in one call, naming **which precedence rule resolved it and
the evidence** — an explicit match and a lucky guess must not look alike. `--json` is there so a
consumer never has to re-implement the router with a regex over printed lines.
[llms.txt](llms.txt) is the same entry point in the convention agents already look for, and it is
generated, so it cannot name a document that does not exist.

**What this repository does not know about your machine:** packs declare toolchains; nothing here
declares them installed. `packprobe` is how you find out before you plan around one.

## Start here — by what you are trying to do

| I want to… | Go here |
|---|---|
| **route one file** and get its toolchain | `atlas.py route` · [Code-specific routing](wiki/CODE-ROUTING.md) |
| **pick a language**, or add one | [Languages](languages/ATLAS.md) · [Language packs](languages/README.md) · [Pack contract](languages/PACK-SPEC.md) |
| **know what a pack must contain** | [Manifest contract](languages/PACK-TOOLS-SPEC.md) · [tools.schema.json](tools/tools.schema.json) |
| **run a language in production** | [Language operations](wiki/LANGUAGE-OPERATIONS.md) · [Systems](systems/README.md) |
| **choose or orchestrate tools** | [Tool orchestration](wiki/TOOL-ORCHESTRATION.md) · [MCP language matrix](integrations/MCP-LANGUAGE-MATRIX.md) |
| **choose a model or runtime** | [Models and runtimes](models/README.md) |
| **branch, merge, or clean up a worktree** | [Branch/worktree model](wiki/BRANCH-WORKTREES.md) · [Labels and tags](wiki/LABELS-TAGS.md) |
| **configure GitHub**, or see what is actually enforced | [GitHub backend](docs/GITHUB-BACKEND.md) · [Finalization](docs/GITHUB-FINALIZATION.md) · `ghaudit.py` |
| **understand WHY a rule here exists** | [Engineering concepts, each paired with a mechanism](docs/ENGINEERING-CONCEPTS.md) |
| **report or handle a vulnerability** | [Security policy](SECURITY.md) |
| **read the background research** | [Research](research/ENGINEERING-RESEARCH.md) |
| **browse everything** | [Wiki](wiki/README.md) · [docs/INDEX.md](docs/INDEX.md) |

## Nothing here states a count it did not compute

A number typed into prose is stale the moment the tree moves, and the reader cannot see that it
moved. So the documents state **no** counts: each one is generated from `atlas.yaml` and the file
tree by `python scripts/atlas.py index --write`, and `check` fails when a generated block differs
from what the tree would produce. Machine-specific numbers — which toolchain is installed, what
GitHub currently enforces — are not written down at all; the instrument that answers them is
named instead.

<!-- BEGIN generated: repository-facts (python scripts/atlas.py index --write) -->
| fact | value | derived from |
|---|---|---|
| contract version | **2.3.1** | `VERSION`, asserted identical in 6 other files |
| artifact extensions routed | **53** | `atlas.yaml/artifact_routes` |
| language routes | **35** | distinct targets of those extensions |
| tool manifests | **35** | `languages/<route>/tools.yaml`, validated against `tools/tools.schema.json` |
| declared tool entries | **340** | distinct entries per manifest, summed; `packprobe.py` classifies every one |
| entry kinds | **5** | `tools/tools.schema.json` `$defs.entry.x-kinds` |
| hard invariants | **25** | each CHECKED or DECLARED, never neither |
| instruments | **11** | `atlas.yaml/instruments`, each naming its own limits |
| verification gate classes | **7** | `atlas.yaml/verification_policy/profiles` |
| task profiles | **13** | `atlas.yaml/task_profiles` |
| python files in the harness | **11** | `scripts/*.py`, all linted by ruff |
<!-- END generated: repository-facts -->

## Instruments — what each one proves, and who closes what it does not

**An instrument whose limits are unnamed is read as proving more than it does.** Every limit below
names its closer, and `atlas.yaml` refuses an entry that leaves that field empty — so a blind spot
with no owner cannot be written down here, rather than merely being discouraged. The same rule
fails the contract when a script exists in `scripts/` that this roster does not name.

<!-- BEGIN generated: instruments (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/instruments`. Run them; do not read a number about them from this page.

| instrument | proves | does not prove | closed by |
|---|---|---|---|
| `atlas.py check` | the repository satisfies its own contract — links, routes, guides, cards, manifests, labels, generated blocks and files, hard invariants | that a declared tool exists anywhere, or that a manifest names the right tools | `packprobe.py --mode smoke` answers existence and execution; each pack's provenance.basis states what is unconfirmed against a real toolchain |
| `atlas.py route / plan` | the route for one artifact, the precedence rule that resolved it and the evidence for that rule, as text or as a JSON record | that the thing routed to is correct for the task | the task profile's own gates, run by `atlas.py plan --change <class>` |
| `atlas.py invariants` | every hard invariant in atlas.yaml is CHECKED by a function or DECLARED with its reason, and names which | that a declared invariant is true of a consuming system | the consuming repository runs its own contract; none is declared here, so the roster is empty by construction |
| `atlas_test.py` | the contract still FAILS on a planted defect — one case per rule, its own case count asserted, and this harness cross-checked against the jsonschema library when it is installed | the truth of a manifest's tool names | `packprobe.py --mode smoke` for the ones this machine can run; provenance.basis for the rest |
| `check_contract.py` | the contract runs from the repository root, from scripts/ and from an unrelated directory | anything about the contract's content | `atlas.py check`, which it calls |
| `packprobe.py` | per pack and in total — how many declared entries there are, how many are commands, and (--mode version\|smoke) which of them run here and what version they report | that a pack was ever exercised end to end, or that a tool absent here is absent elsewhere | a codespace with that one toolchain installed (.devcontainer/README.md) plus the pack's provenance.verify list; absence on one machine is a fact about the machine |
| `atlas.py doctor` | which capabilities THIS machine has — interpreter, PyYAML, git, gh, ruff, jsonschema — and, for each one missing, what stops working because of it | that a present tool is new enough, or anything about the language toolchains the packs declare | `packprobe.py --mode smoke`, which runs the language toolchains pack by pack; a version floor is declared per pack in its manifest and in pyproject for the harness |
| `astshape.py` | no two Python functions in this repository share a canonical AST — names, literals and docstrings erased — and none exceeds the declared line or nesting caps | anything about the 34 language packs, whose formatters and linters are their own declared authority, and nothing about whether a unique function is a GOOD one | each pack declares its own formatter and linter in its manifest; `ruff` covers this repository's own Python, and a human reviewer covers whether the shape earns its place |
| `exrun.py` | every example under examples/ RUNS on this machine and its own assertions hold — routed by this repository's own router, with the recipe declared per route | anything about a toolchain that is absent here, or about the rest of a pack's declarations | CI runs it on every pull request with the runner's toolchains, and `packprobe.py --mode smoke` covers the declarations an example does not exercise |
| `ghaudit.py` | the live GitHub controls — visibility, secret scanning, rulesets, required checks, topics, licence — match config/github-controls.json, and REFUSES rather than reporting when it cannot reach the API | that a required check is a good check, or that a bypass actor did not use its bypass | the check's own workflow, and `gh api .../rulesets` history; bypasses are listed in the audit output so the reader sees who can skip |
| `ruff check` | lint over every Python file in this repository, configured in pyproject.toml | formatting, which `ruff format` would rewrite in every file | a deliberate single commit that reformats everything at once, with the reason recorded in pyproject.toml — never a gate switched on quietly |
<!-- END generated: instruments -->

## Hard invariants are owned, not listed

`atlas.yaml` declares the hard invariants. Each maps in `scripts/atlas.py` to either a CHECK that
fails the contract or a DECLARATION naming why this repository cannot check it and what would. An
invariant in neither list fails the contract, so the roster cannot quietly grow promises nobody
owns:

```bash
python scripts/atlas.py invariants
```

A declared blind spot is a promise to come back, not an exemption — and the declared table is
currently empty, which the command prints on every run.

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
quantum_change     -> simulator_run + shot_count_declared + noise_model_declared + resource_estimate + classical_baseline_comparison
```
<!-- END generated: verification-gates -->

Four severity classes: `blocker`/`error` are merge-blocking; `warning` is visible and actionable
but normally non-blocking; `info` is report-only; `baseline` is limited to already-known findings.
New findings must never be hidden by baseline growth.

## Assurance chain

```text
GOAL
 -> route
 -> native compiler/LSP/debugger/tester
 -> language tool manifest
 -> semantic repository context
 -> boundary contract
 -> targeted docs/browser/database capability
 -> security/dependency analysis
 -> independent verification
 -> CI
```

Do not load every tool, MCP or language guide. Activate only the capability the goal or failure
class needs.

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

A codespace boots from [.devcontainer](.devcontainer/README.md): Python plus the harness
dependency, with the contract run on create. Its purpose is confirming a language pack against a
real toolchain — add that one language as a devcontainer feature, run `atlas.py learn <language>`,
confirm the pack with `packprobe.py --mode smoke`, then remove the feature.

## Languages

<!-- BEGIN generated: language-roster (python scripts/atlas.py index --write) -->
35 routes, each with a guide, an operating card and a tool manifest — the full table with links is in [languages/README.md](languages/README.md).

`bash` (.bash .sh) · `bqn` (.bqn) · `c` (.c .h) · `carbon` (.carbon) · `chapel` (.chpl) · `cpp` (.cc .cpp .hpp) · `cuda` (.cu .cuh) · `elixir` (.ex .exs) · `forth` (.4th .fth) · `fsharp` (.fs .fsx) · `futhark` (.fut) · `gleam` (.gleam) · `go` (.go) · `hare` (.ha) · `haskell` (.hs .lhs) · `julia` (.jl) · `lean4` (.lean) · `mojo` (.mojo) · `nim` (.nim) · `ocaml` (.ml .mli) · `odin` (.odin) · `python` (.py .pyi) · `quantum/qsharp` (.qs) · `quantum/silq` (.slq) · `r` (.r) · `roc` (.roc) · `rust` (.rs) · `scala` (.sc .scala) · `sql` (.sql) · `swift` (.swift) · `typescript` (.cjs .js .jsx .mjs .ts .tsx) · `uiua` (.ua) · `v` (.v) · `webassembly` (.wasm .wat) · `zig` (.zig)
<!-- END generated: language-roster -->

## Packages and dependencies

<!-- BEGIN generated: packages (python scripts/atlas.py index --write) -->
The atlas is not a library you install. One Python dependency runs the harness; every
language toolchain is declared by a pack and installed by the machine that needs it.

| package surface | value | where it is declared |
|---|---|---|
| harness package | `code-development-harness` | declared in `pyproject.toml`; nothing is published to an index |
| python required | `>=3.11` | `pyproject.toml` |
| runtime dependency | `pyyaml>=6,<7` | `scripts/requirements.txt`, mirrored in `pyproject.toml` |
| what CI actually installs | `scripts/requirements.lock.txt` | hash-pinned and installed with `--require-hashes`; the contract asserts the pin sits inside the range above |
| quality extra | `ruff` | `pyproject.toml` `[project.optional-dependencies]` |
| language toolchains | declared per pack, installed by nobody here | `languages/<route>/tools.yaml`; run `python scripts/packprobe.py --mode smoke` |
<!-- END generated: packages -->

## Versions and releases

The version tracks the **contract**, not the content: adding a paragraph to a guide is not a
version change; changing what the harness enforces, what a route resolves to or what a gate
requires always is. One line per version is the only changelog, the same commit bumps every place
the string appears, and the release procedure ends in a tag — a version with no tag is a claim with
no artifact. See [docs/VERSIONING.md](docs/VERSIONING.md).

## Topics

<!-- BEGIN generated: topics (python scripts/atlas.py index --write) -->
Declared in `config/github-controls.json` and asserted against the live repository by
`python scripts/ghaudit.py` — this page states the declaration, the instrument states
the fact.

`agent-tooling` · `ai-agents` · `code-quality` · `data-science` · `developer-tools` · `engineering-atlas` · `github-actions` · `llm` · `mcp` · `openssf` · `polyglot` · `quantum-computing` · `software-engineering` · `static-analysis` · `supply-chain-security` · `verification`
<!-- END generated: topics -->

## About

Built by **Apian Software** and public on purpose: an atlas that needs a token to read cannot route
an agent that has none. The cost of that choice is one absolute rule — **no secret, credential,
private-project path or internal hostname enters this repository**, not in a file, not in an
example, not in history. Everything operational lives in a private repository; what lives here is
the method, and it is safe to hand this whole tree to an unknown agent.

Read [ABOUT.md](ABOUT.md) for the division between the two, and
[docs/ENGINEERING-CONCEPTS.md](docs/ENGINEERING-CONCEPTS.md) for why each rule exists.
Contributions follow the same contract as any change: `check` and `atlas_test.py` must pass, and
the pull request template asks what would prove the goal met.

Licensed under the [MIT License](LICENSE).
