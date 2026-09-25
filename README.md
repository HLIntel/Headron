<!-- AGENTS: do not read this page breadth-first. Start at .agent/bootstrap.json or llms.txt,
     then ask `python scripts/atlas.py gate <file> <gate>` — one command back. -->
<p align="center">
  <img src="docs/assets/thea.webp"
       alt="Thea Software — The Heartland Engineering Atlas · software development · AI agents" width="440">
</p>

<h1 align="center"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/title-dark.svg">
  <img src="docs/assets/title-light.svg" alt="The Heartland Engineering Atlas" width="560">
</picture></h1>

<p align="center">
  <strong>The engineering layer between AI and the software it builds.</strong><br>
  <em>Thea Software — AI proposes. Your toolchain proves. Nothing drifts.</em>
</p>

<p align="center"><sub><b>An AI reading this?</b> Agents start at <a href="llms.txt">llms.txt</a>, chats at
<a href="CHAT.md">CHAT.md</a> — each maps <i>use · install · open · run · pull</i> to one action.</sub></p>

<p align="center">
  <a href="https://github.com/HeartlandIntel/thea-software/actions/workflows/atlas-ci.yml"><img
     src="https://github.com/HeartlandIntel/thea-software/actions/workflows/atlas-ci.yml/badge.svg?branch=main"
     alt="Atlas CI"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/HeartlandIntel/thea-software"><img
     src="https://api.securityscorecards.dev/projects/github.com/HeartlandIntel/thea-software/badge"
     alt="OpenSSF Scorecard"></a>
  <a href="https://github.com/HeartlandIntel/thea-software/actions/workflows/scorecard.yml"><img
     src="https://github.com/HeartlandIntel/thea-software/actions/workflows/scorecard.yml/badge.svg?branch=main"
     alt="OpenSSF Scorecard workflow"></a>
  <a href="LICENSE"><img
     src="https://img.shields.io/github/license/HeartlandIntel/thea-software"
     alt="licence"></a>
  <a href="https://github.com/HeartlandIntel/thea-software/releases/latest"><img
     src="https://img.shields.io/github/v/tag/HeartlandIntel/thea-software?label=contract"
     alt="contract version"></a>
</p>

<p align="center">
  <sub>Every badge is served by whoever measures it — none is typed here.
  <a href="docs/CERTIFICATION.md">What each one proves</a>.</sub>
</p>

<p align="center">
  <a href="docs/VERSIONING.md">versioning</a> ·
  <a href="docs/INDEX.md">index</a> ·
  <a href="docs/CONSUMING.md">use it elsewhere</a> ·
  <a href="llms.txt">llms.txt</a> ·
  <a href="SECURITY.md">security</a> ·
  <a href="docs/CERTIFICATION.md">certification</a> ·
  <a href="https://github.com/HeartlandIntel/thea-software/releases">releases</a> ·
  <a href="LICENSE">MIT</a>
</p>

---

## What this is

**Thea Software is a rulebook any AI can follow, and a build that checks it did.** Hand it to a chat, an
agent or a bare model: it answers in one line which command proves a change, which checks a change
needs and what an agent may not do, then refuses work that skipped them. It is the engineering
control plane for [Heartland Intel](https://github.com/HeartlandIntel), and it behaves the
same under Claude, Codex, Cursor, opencode, Zed or any model handed a link.

**What it does better**

- **Right answers for fewer tokens.** Given Thea's one-line answer, models pick the right command
  far more often than asking blind, at a fraction of the tokens of reading everything — measured per
  model below, including on reasoning and rule-following tasks.
- **Nothing rests on memory.** Every rule is a declaration a program executes. A document, count or
  version that drifts from the tree fails the build; "looks correct" is never a verdict.
- **Mistakes stay fixed.** Any AI files a break with the portable [`thea` skill](skills/thea/SKILL.md);
  each becomes a guard with a planted test, or an intake that must graduate.
- **Safe to hand to anything.** Public, secret-free, its dependency closure pinned by hash, and its
  agent controls refuse rather than warn.
- **Meets you where you are.** A chat pastes one block (`CHAT.md`); an agent loads one generated
  file; a model given a link reads `llms.txt`; each maps *use, install, open, run, pull* to one action.

Six capabilities, one declaration, none able to disagree with the others:

- **Routing** — `atlas.yaml` holds every route, gate, process, control, budget and policy; `atlas route` returns the answer *and which precedence rule resolved it*
- **Verification** — the change class picks the gates, and each gate resolves to a command the pack itself declares — every (pack, gate) pair resolves, none to silence
- **Language packs** — compiler, formatter, test runner, debugger, profiler and security tool per language — none loaded until a route names it
- **Runtime adapters** — one generated body served as `CLAUDE.md`, `AGENTS.md` and `llms.txt`, plus an adapter each for Claude, Codex, Cursor, opencode, Zed, VS Code and Hermes: how the atlas loads there, and *the mistake that runtime makes*
- **An agent harness** — a task contract with a schema, five controls that refuse rather than warn, a runner that writes the outcome into the record that planned it, and a hash-chained audit
- **Error prevention** — defect tests: each plants a real defect, asserts the contract refuses it, and restores the file — and each suite asserts its own case count

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

Model results come from recorded test runs, stamped with the version they ran on.

<!-- BEGIN generated: measured-benefits (python scripts/atlas.py index --write) -->
*With Thea* = the model is given the one line `atlas gate` returns. *Blind* = it gets only the list
of language names. Token savings are against the usual alternative: pasting in every language's tool list.

**On Claude** (39 questions per model, `abtest.py` v2.28.0)
- **Opus:** 100% right with Thea, 41% blind; reads 91% fewer tokens.
- **Sonnet:** 95% right with Thea, 41% blind; reads 91% fewer tokens.
- **Haiku:** 97% right with Thea, 41% blind; reads 91% fewer tokens.
- **Claude Code start-up:** reads only `CLAUDE.md`, 1,085 tokens.

**Beyond routing** (blind → with Thea, `taskbench.py` v2.29.0)
- **Name a failure from its symptom:** Opus 93% → 100%; Sonnet 57% → 100%; Haiku 64% → 96%.
- **List the checks a change needs:** Opus 12% → 100%; Sonnet 12% → 100%; Haiku 0% → 100%.
- **Spot a line the build refuses (yes/no, so a coin flip scores 50%):** Opus 60% → 100%; Sonnet 60% → 100%; Haiku 40% → 100%.
- *Not measured:* visual design, open-ended strategy, arithmetic — nothing declares a right answer.

**Across all 11 models tested** (5 providers, 2,076 questions, `abtest.py` v2.27.0 / v2.28.0)
- **Right answers:** 98% with Thea, 63% blind; every model 95–100% with Thea. A random guess scores 2.8%.
- **Tokens:** reads 89% fewer than pasting every tool list, and 51% fewer than asking blind.

**The repository itself** (recomputed on every build)
- **Before routing:** an agent reads 1,744 tokens. The other 156 documents (450 KiB) load only when a route names one.
- **Coverage:** all 324 language × check pairs answer — 142 with a command, 182 with a declared *no tool*, 0 silently.
- **Mistakes caught:** 163 kinds are planted in the tests, and each must be refused.
- **Agent controls that block, not warn:** narrow_tools, sandbox, budget, approval, audit.
- **Install:** 190 KiB, 11 modules, 1 dependency — 1 package in total once its own dependencies are counted.
<!-- END generated: measured-benefits -->

### What each runtime pays to start

<!-- BEGIN generated: runtime-entry (python scripts/atlas.py index --write) -->
| runtime | loads by itself | ~tokens |
|---|---|---|
| **Claude Code** | `CLAUDE.md` | 1,085 |
| Codex | `AGENTS.md` | 1,099 |
| Cursor | `AGENTS.md` | 1,099 |
| opencode | `AGENTS.md` | 1,099 |
| Zed | `AGENTS.md` | 1,099 |
| Hermes | `.agent/bootstrap.json` | 628 |
| any model given a link | `llms.txt` | 1,116 |
| any chat assistant | `CHAT.md` | 1,540 |

Measured from each file on every build.
<!-- END generated: runtime-entry -->

### Who it is for

- **Claude Code developers:** a generated `CLAUDE.md`, hooks over instructions, landing that cannot strand.
- **Polyglot repositories:** which toolchain owns this file, and what must pass.
- **Teams running several agents:** one contract, one audit chain, one landing path.
- **Security and supply-chain owners:** pinned, attested, audited against the live platform.
- **CI and consuming repos:** ids frozen in a schema; a document that drifts fails the build.

### What makes it different

- **One question, one call — with its evidence.** `atlas route <file>` returns the pack, card,
  manifest, label, lane and gates, and names *which precedence rule resolved it*, so an explicit
  match and a lucky guess never look alike. It also reports the rules it did **not** resolve.
- **Rules that may bend, and rules that may not — declared.** `governance_tiers` separates what
  refuses outright from what may move *if the move names what earned it*, because a bound that
  cannot move gets worked around instead of respected.
- **Mistakes are inventory.** What went wrong here is written down with its recurrence count and
  what refuses it now, because a shape seen twice is a missing rule.
- **Ratchets that only fall.** Entry cost, install footprint, function shape and example coverage.
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

- **route one file** and get its toolchain → `atlas.py route` · [Code-specific routing](wiki/CODE-ROUTING.md)
- **run a pack's own tool** on a file → `atlas.py do` · [Manifest contract](languages/PACK-TOOLS-SPEC.md)
- **follow a named process** end to end → `atlas.py process` · [Verification](docs/VERIFY.md)
- **pick a language**, or add one → [Languages](languages/ATLAS.md) · [Language packs](languages/README.md) · [Pack contract](languages/PACK-SPEC.md)
- **know what a pack must contain** → [tools.schema.json](tools/tools.schema.json) · [Pack tools spec](languages/PACK-TOOLS-SPEC.md)
- **run an agent under real controls** → [agent-task.schema.json](tools/agent-task.schema.json) · [Agent harness](systems/AGENT-HARNESS.md)
- **run a language in production** → [Language operations](wiki/LANGUAGE-OPERATIONS.md) · [Systems](systems/README.md)
- **choose or orchestrate tools** → [Tool orchestration](wiki/TOOL-ORCHESTRATION.md) · [MCP language matrix](integrations/MCP-LANGUAGE-MATRIX.md)
- **choose a model or runtime** → [Models and runtimes](models/README.md)
- **land a change**, or clean up a worktree → `branchstate.py --land` / `--sync` · [Branch/worktree model](wiki/BRANCH-WORKTREES.md)
- **configure GitHub**, or see what is enforced → [GitHub backend](docs/GITHUB-BACKEND.md) · [Finalization](docs/GITHUB-FINALIZATION.md) · `ghaudit.py`
- **understand WHY a rule here exists** → `atlas.py why` · [Engineering concepts](docs/ENGINEERING-CONCEPTS.md)
- **report or handle a vulnerability** → [Security policy](SECURITY.md)
- **read the background research** → [Research](research/ENGINEERING-RESEARCH.md)
- **browse everything** → [Wiki](wiki/README.md) · [docs/INDEX.md](docs/INDEX.md)

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

**When something goes wrong, run `thea` — people, agents and models alike.** A failed gate, a wrong
answer, drift, a guard firing on correct work: file it the same turn with
[skills/thea/SKILL.md](skills/thea/SKILL.md) (`/thea` in Claude, the `report` verb in any chat).

## The failure it exists to prevent

**The expensive break is the one whose output looks like success.** A guard that checked nothing,
a test that ran zero cases and a router that served an error as an answer all print what a working
system prints. So the order is fixed: **make the break unrepresentable; if it can still happen,
make it loud; only then detect it.**

Two were found here by causing them. A second `'.fs'` key silently moved every F# file to the
Forth pack, because YAML keeps the *last* duplicate, so **every YAML read goes through a loader
that refuses duplicates, and a direct PyYAML call fails the contract.** A re-indent twice wrote a
harness file that no longer compiled while the contract printed all its counts, so **every
tracked source and JSON file must parse, and that check runs first.**

Care could have prevented neither. **A tool that picks a winner where input is ambiguous, or
reports success where it never looked, is worse than one that refuses.** Sightings:
[Engineering concepts](docs/ENGINEERING-CONCEPTS.md) · `atlas.py why`.

## Nothing here states a count it did not compute

A number typed into prose goes stale, unseen, the moment the tree moves. Every count below is
generated from `atlas.yaml` and the tree, and `check` fails when a block drifts. Machine-specific
numbers are never written down; the instrument that answers them is named instead.

<!-- BEGIN generated: repository-facts (python scripts/atlas.py index --write) -->
- **contract version:** 3.2.0 — `VERSION`, asserted at a declared line in 6 other files
- **artifact extensions routed:** 53 — `atlas.yaml/artifact_routes`
- **language routes:** 36 — distinct targets of those extensions
- **tool manifests:** 36 — `languages/<route>/tools.yaml`, validated against `tools/tools.schema.json`
- **declared tool entries:** 372 — distinct entries per manifest, summed; `packprobe.py` classifies every one
- **entry kinds:** 5 — `tools/tools.schema.json` `$defs.entry.x-kinds`
- **hard invariants:** 33 — each CHECKED or DECLARED, never neither
- **instruments:** 33 — `atlas.yaml/instruments`, each naming its own limits
- **verification gate classes:** 8 — `atlas.yaml/verification_policy/profiles`
- **task profiles:** 14 — `atlas.yaml/task_profiles`
- **python files in the harness:** 33 — `scripts/*.py`, all linted by ruff
<!-- END generated: repository-facts -->

## Instruments — what each one proves, and who closes what it does not

Every claim is settled by a command, not a badge. Each instrument declares `proves`,
`does_not_prove` and **`closed_by`** (what covers its limit), and `check` refuses an empty closer,
so an unowned blind spot cannot exist. The roster is generated into
[docs/CERTIFICATION.md](docs/CERTIFICATION.md); its count is in the facts block.

## Hard invariants are owned, not listed

Each hard invariant in `atlas.yaml` maps to a CHECK that fails the contract or a DECLARATION
saying why it cannot be checked here and what would. One in neither fails the contract, so no
promise goes unowned:

```bash
python scripts/atlas.py invariants
```

A declared blind spot is a promise to come back, not an exemption. Every run prints the
enforced/declared split, so the table's size is read from the run, never from this page.

## The harness is tested

`scripts/atlas_test.py` plants a real defect for every rule the contract enforces (a hand-edited
generated block, a version skew, a prose manifest entry, a bypassed YAML loader, a re-parse per
lookup), asserts the check fails on each, and **restores the file before the next case**. It
asserts its own case count, because a harness that skips cases prints a full pass.

## Dynamic verification

The task and its risk pick the smallest sufficient verification surface. Required gates:

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

Severity: `blocker`/`error` block the merge; `warning` is visible, normally non-blocking; `info`
is report-only; `baseline` holds known findings only, and its growth may never hide a new one.

## Multi-language design, and learning one

Add a second language only for a distinct guarantee, runtime property, ecosystem or performance
trait. **Define the boundary first**, then assign ownership. Pairings and boundary shapes:
[systems/POLYGLOT-ENGINEERING.md](systems/POLYGLOT-ENGINEERING.md); `atlas pick` selects by need.

`atlas.py learn <language>` turns a pack's card and manifest into a mastery loop (read, trace,
reproduce, modify, break on purpose, verify, benchmark, record), one language at a time. Prefer
primary docs to summaries: `none` in a manifest means no established tool exists for that role,
and `provenance` says what is unconfirmed against a real toolchain.

## Codespaces

A codespace boots from [.devcontainer](.devcontainer/README.md) to confirm ONE pack against a real
toolchain: add the feature, probe it, remove it. Absence on a machine is a fact about the machine.

## Languages

Every route has a guide, an operating card and a tool manifest, none loaded until a route names
it. Choose by problem shape, not popularity: [languages/ATLAS.md](languages/ATLAS.md), `atlas pick`
for the selection axes, `atlas route <file>` for one file.

## Packages and dependencies

What this repo installs and refuses: [docs/PACKAGE-CATALOG.md](docs/PACKAGE-CATALOG.md). What a
dependency really pulls in — transitive, micro, wiring — and how to add one well:
[docs/DEPENDENCIES.md](docs/DEPENDENCIES.md).

## Versions and releases

The version tracks the **contract**, not the content: a new guide paragraph is not a version
change; changing what the harness enforces, what a route resolves to or what a gate requires
always is. One line per version is the only changelog, one commit bumps every copy of the string,
and every release ends in a tag, since a version with no tag is a claim with no artifact. See
[docs/VERSIONING.md](docs/VERSIONING.md).

## About

Built by **Heartland Intel** and public on purpose: an atlas that needs a token to read cannot route
an agent that has none. The cost of that choice is one absolute rule — **no secret, credential,
private-project path or internal hostname enters this repository**, not in a file, not in an
example, not in history. Everything operational lives in a private repository; what lives here is
the method, and it is safe to hand this whole tree to an unknown agent.

Read [ABOUT.md](ABOUT.md) for the division between the two, and
[docs/ENGINEERING-CONCEPTS.md](docs/ENGINEERING-CONCEPTS.md) for why each rule exists.
Contributions follow the same contract as any change: `check` and `atlas_test.py` must pass, and
the pull request template asks what would prove the goal met.

Licensed under the [MIT License](LICENSE).
