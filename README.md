<!-- AGENTS: do not read this page breadth-first. Start at .agent/bootstrap.json or llms.txt,
     then ask `python scripts/atlas.py gate <file>` — one command back. -->
<p align="center">
  <img src="docs/assets/thea.webp"
       alt="Thea Software by Heartland Intel — rules and build checks for AI coding agents" width="440">
</p>

<h1 align="center"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/title-dark.svg">
  <img src="docs/assets/title-light.svg" alt="Thea — The Heartland Engineering Atlas" width="560">
</picture></h1>

<p align="center">
  <strong>Thea Software, by Heartland Intel.</strong><br>
  A machine-readable rulebook for AI coding agents, and the build checks that enforce it.<br>
  <em>AI proposes a change. The file's own toolchain proves it. The build refuses what skipped a check.</em>
</p>

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
  <a href="#quickstart">quickstart</a> ·
  <a href="#what-it-measurably-buys">results</a> ·
  <a href="#find-your-way">docs</a> ·
  <a href="SECURITY.md">security</a> ·
  <a href="docs/CERTIFICATION.md">what each badge proves</a> ·
  <a href="docs/VERSIONING.md">changelog</a> ·
  <a href="LICENSE">MIT</a>
  <br><sub>An AI reading this: agents start at <a href="llms.txt">llms.txt</a>, chats at <a href="CHAT.md">CHAT.md</a>.</sub>
</p>

---

## What it does

AI coding agents fail in a predictable way: they finish a change, run *something*, and report success.
Thea closes that gap. It is a contract, one declaration file ([`atlas.yaml`](atlas.yaml)) enforced by
programs, that sits between any AI and any repository and answers one question exactly:
**what proves this change is correct?**

<!-- BEGIN generated: glance (python scripts/atlas.py index --write) -->
**36** languages · **53** extensions · **64** gates · **8** runtimes · **44** failure shapes · **38** invariants · **51** instruments · **1** dependency
<!-- END generated: glance -->

That question reaches far past code review. The same contract makes any agent, chat or model more
accurate and cheaper: it routes work to the right toolchain, bounds agents with controls that refuse,
prevents whole classes of mistakes, names a fallback for every gap, and covers endpoints, databases,
security, supply chain, retrieval and quantum code alike.

Point it at a file. Thea resolves the file to its language pack, the change to the gates it must pass,
and each gate to the precise check-only command that language's own toolchain provides: the
formatter in check mode, the type checker, the test runner. Where a toolchain has no such tool it
says so and names who covers the gap. It never guesses, and it refuses ambiguous input.

<!-- BEGIN generated: gate-example (python scripts/atlas.py index --write) -->
```console
$ thea gate scripts/doctor.py
1. formatter: ruff format --check scripts/doctor.py
2. compiler_or_typechecker: python3 -c 'import ast,sys; [ast.parse(open(f, encoding="utf-8").read(), f) for f in sys.argv[1:]]' scripts/doctor.py
3. unit_tests: pytest
```
<!-- END generated: gate-example -->

Then it holds that line at every point a change passes:

- **At commit.** A git hook that every agent commits through refuses a file its own toolchain rejects.
- **On the pull request.** CI runs the same declared gate set, and a document, count or version that
  has drifted from the code fails the build.
- **In the agent's report.** `thea verify` returns PASS, FAIL or NOT RUN per gate from its exit code,
  so "done" means every gate ran and passed, not that the output looked green.

Why that matters to whoever runs the agent:

- **One answer, not a manual.** An agent asks `thea gate <file>` instead of reading the repository,
  and [measurably](#what-it-measurably-buys) picks the right command far more often, for far fewer tokens.
- **Your agent keeps its own tools.** Thea adds a CLI, a git hook and a read-only MCP server to
  [each supported runtime](models/README.md) and never removes a tool it ships with.
- **Mistakes stay fixed.** A break is filed with the [`thea` skill](skills/thea/SKILL.md) and becomes a
  test that fails if it returns.

### It adapts to wherever the AI is

Not only for agents that write code all day — each setting gets the part it can use:

<!-- BEGIN generated: settings (python scripts/atlas.py index --write) -->
| where you use it | what Thea does there |
|---|---|
| A chat with no tools | name the format, typecheck and test commands for any file they name (the route table below, then that pack's tools.yaml), review a pasted diff against the gates, and turn a goal into the checklist of gates its change class requires |
| A chat that keeps instructions | paste the Install block once, and every later chat starts routed, labels its claims and files breaks with the report verb |
| An agent with a shell | clone a release tag and run `python scripts/atlas.py gate <file>` — the numbered commands that prove a change to that file — then `python scripts/enforce.py install` in the repository being changed, so a commit that fails its own toolchain's check is refused |
| A repository's CI | call the reusable workflow, and drift fails the pull request |
| A retrieval or RAG pipeline | run the retrieval_change gates — chunk boundaries, a freshness stamp, hybrid recall and citation checks — so an answer is grounded in what was actually retrieved |
| An autonomous agent run | write a task contract, and `python scripts/sandboxgen.py docker <contract>` prints the host sandbox it needs — no network, read-only root, only the worktree writable |
| A chat or agent with memory | save verdicts by id (a gate, a change class, a ledger entry) with their contract version, never a paraphrase: an id re-checks against the tree, a summary drifts |
<!-- END generated: settings -->

The cheapest start is one command, `enforce.py install`: it adds the hook and keeps any hook you have. The full contract is there when you want it.

**Not** an app framework or a runtime optimizer. It is not a sandbox either, but it generates one
from the task contract (`sandboxgen.py`); running it is still the host's job.

## Quickstart

```bash
python scripts/atlas.py gate   scripts/doctor.py    # the commands that prove a change to this file
python scripts/atlas.py route  scripts/doctor.py    # its language pack, card, manifest and lane
python scripts/atlas.py plan   scripts/doctor.py --task implementation --change source_change
python scripts/verify.py                            # every gate, one verdict each; exit 0 only if all PASS
```

Installed, the same commands answer as **`thea <command>`** (`thea commands` lists them) and
**`thea-mcp`** serves them as read-only MCP tools. Add `--json` for a record frozen in
[tools/atlas-output.schema.json](tools/atlas-output.schema.json): depend on route ids, gate ids and
manifest paths, never on rendered Markdown. From another repository: [docs/CONSUMING.md](docs/CONSUMING.md).

## What it measurably buys

Recorded runs on Thea's own suites, each naming its instrument and version: evidence for routing, checks and refusals, not independent proof of end-to-end task success ([limits](docs/CERTIFICATION.md#what-the-numbers-do-not-prove)).

<!-- BEGIN generated: measured-benefits (python scripts/atlas.py index --write) -->
*With Thea*: the model is shown what `thea gate` prints for the file. *Blind*: it gets only the list
of language names. Token savings are against the usual alternative: pasting in every language's tool list.

**On Claude** (39 questions per model, `abtest.py` v2.28.0)
- **Opus:** 100% right with Thea, 41% blind; reads 91% fewer tokens.
- **Sonnet:** 95% right with Thea, 41% blind; reads 91% fewer tokens.
- **Haiku:** 97% right with Thea, 41% blind; reads 91% fewer tokens.
- **Claude Code start-up:** reads only `CLAUDE.md`, 67 tokens.

**Beyond routing** (blind → with Thea, `taskbench.py` v2.29.0)
- **Name a failure from its symptom:** Opus 93% → 100%; Sonnet 57% → 100%; Haiku 64% → 96%.
- **List the checks a change needs:** Opus 12% → 100%; Sonnet 12% → 100%; Haiku 0% → 100%.
- **Spot a line the build refuses (yes/no, so a coin flip scores 50%):** Opus 60% → 100%; Sonnet 60% → 100%; Haiku 40% → 100%.
- *Not measured:* visual design, open-ended strategy, arithmetic — nothing declares a right answer.

**Across all 11 models tested** (5 providers, 2,076 questions, `abtest.py` v2.27.0 / v2.28.0)
- **Right answers:** 98% with Thea, 63% blind; every model 95–100% with Thea. A random guess scores 2.8%.
- **Tokens:** reads 89% fewer than pasting every tool list, and 51% fewer than asking blind.

**The repository itself** (recomputed on every build)
- **Before routing:** an agent reads 1,739 tokens. The other 156 documents (487 KiB) load only when a route names one.
- **Coverage:** all 324 language × check pairs answer — 133 with a command, 191 with a declared *no tool*, 0 silently.
- **Mistakes caught:** 218 kinds are planted in the tests, and each must be refused.
- **Enforced at commit:** refused 17 of 17 planted breaks in 12 languages; 11 files untested here (`enforce.py`, v3.6.0).
- **Agent-to-agent handoffs with the right checks** (schema alone → with Thea): Opus 0/6 → 6/6; Sonnet 0/6 → 6/6; Haiku 0/6 → 6/6 (`workflowbench.py`).
- **Solo commits:** 24/24 clean with or without the hook on these tasks; a planted broken commit is refused.
- **Agent controls that block, not warn:** narrow_tools, sandbox, budget, approval, audit.
- **Install:** 5 KiB, 1 modules, 1 dependency — 1 in total with its own dependencies.
<!-- END generated: measured-benefits -->

## How it works

| part | what it gives you | where |
|---|---|---|
| **Routing** | the language pack for any file, and *which precedence rule* chose it | `atlas route` · [routing](wiki/CODE-ROUTING.md) |
| **Gates** | the change class picks the checks; each resolves to a command the pack declares, or to a declared *no tool* | `atlas gate` · [verification](docs/VERIFY.md) |
| **Language packs** | compiler, formatter, tests, debugger, profiler, security tool per language, loaded only when routed | [languages](languages/ATLAS.md) · [pack contract](languages/PACK-SPEC.md) |
| **Runtime adapters** | how Thea loads in each agent, and the mistake that agent makes | [models](models/README.md) |
| **Agent harness** | a task contract whose controls refuse rather than warn, and a hash-chained audit | [agent harness](systems/AGENT-HARNESS.md) |
| **Enforcement** | a pre-commit hook for any agent, CI on every pull request, a landing that cannot strand a branch | `enforce.py` · `branchstate.py --land` |

**The rules it will not bend**, each with the defect it was measured against: `thea why` · [AGENTS.md](AGENTS.md).

The gates each change class requires, and what blocks a merge: [docs/VERIFY.md](docs/VERIFY.md).

## For agents

Parse [.agent/bootstrap.json](.agent/bootstrap.json), ask `thea gate <file>`, load only what the
answer names. Reading this tree breadth-first is the failure named in
`atlas.yaml/context_policy/forbidden_default`.

- **Land** with `python scripts/branchstate.py --land`. A bare push of a lane is refused, because a
  pushed branch nothing will merge looks finished and is not.
- **Audit read-only** with `THEA_READ_ONLY=1`: the planted suite refuses to run beside a live editor.
- **Enable an MCP server per task**, never by default: its tool list is paid on every request.
- **When something goes wrong**, file it the same turn with the [`thea` skill](skills/thea/SKILL.md).

## Why it exists

**The expensive break is the one whose output looks like success:** a guard that checked nothing, a
test that ran zero cases, a gate that passed on zero files. So a break is made impossible to represent
first, loud second, detected last. Worked cases: [Engineering concepts](docs/ENGINEERING-CONCEPTS.md).

## Counts, computed

Every number here is generated from the tree on each build, and `check` fails when one drifts.

<!-- BEGIN generated: repository-facts (python scripts/atlas.py index --write) -->
- **contract version:** 3.23.1 — `VERSION`, asserted at a declared line in 6 other files
- **artifact extensions routed:** 53 — `atlas.yaml/artifact_routes`
- **language routes:** 36 — distinct targets of those extensions
- **tool manifests:** 36 — `languages/<route>/tools.yaml`, validated against `tools/tools.schema.json`
- **declared tool entries:** 372 — distinct entries per manifest, summed; `packprobe.py` classifies every one
- **entry kinds:** 5 — `tools/tools.schema.json` `$defs.entry.x-kinds`
- **hard invariants:** 38 — each CHECKED or DECLARED, never neither
- **instruments:** 51 — `atlas.yaml/instruments`, each naming its own limits
- **verification gate classes:** 8 — `atlas.yaml/verification_policy/profiles`
- **task profiles:** 14 — `atlas.yaml/task_profiles`
- **python files in the harness:** 51 — `scripts/*.py`, all linted by ruff
<!-- END generated: repository-facts -->

What each instrument proves and does not: [docs/CERTIFICATION.md](docs/CERTIFICATION.md) · invariants: `thea invariants`.

## Find your way

| to… | go to |
|---|---|
| route a file or run a pack's tool | `atlas route` · `atlas do` · [manifest contract](languages/PACK-TOOLS-SPEC.md) · [tools.schema.json](tools/tools.schema.json) |
| follow a named process end to end | `atlas process` · [verification](docs/VERIFY.md) |
| pick or add a language | [languages](languages/ATLAS.md) · [packs](languages/README.md) · `atlas pick` · `atlas learn` |
| combine languages | [polyglot engineering](systems/POLYGLOT-ENGINEERING.md) |
| run an agent under real controls | [agent-task.schema.json](tools/agent-task.schema.json) · [agent harness](systems/AGENT-HARNESS.md) |
| run a language in production | [language operations](wiki/LANGUAGE-OPERATIONS.md) · [systems](systems/README.md) |
| choose tools, a model or a runtime | [tool orchestration](wiki/TOOL-ORCHESTRATION.md) · [MCP matrix](integrations/MCP-LANGUAGE-MATRIX.md) · [models](models/README.md) |
| land work or clean a worktree | [branch and worktree model](wiki/BRANCH-WORKTREES.md) |
| configure or audit GitHub | [GitHub backend](docs/GITHUB-BACKEND.md) · [finalization](docs/GITHUB-FINALIZATION.md) · `ghaudit.py` |
| add a dependency well | [package catalog](docs/PACKAGE-CATALOG.md) · [dependencies](docs/DEPENDENCIES.md) |
| report a vulnerability | [security policy](SECURITY.md) |
| everything else | [docs index](docs/INDEX.md) · [wiki](wiki/README.md) · [research](research/ENGINEERING-RESEARCH.md) · [codespace](.devcontainer/README.md) |

## Project

The version tracks the **contract** (what is enforced, routed or required), not the content; one line
per version is the changelog, and every release is tagged: [docs/VERSIONING.md](docs/VERSIONING.md).

Built by **Heartland Intel** and public on purpose (formerly *Code-Development*): an atlas that needs
a token to read cannot route an agent that has none. The price is one absolute rule: **no secret,
credential, private-project path or internal hostname enters this repository**, in any file or in
history. [ABOUT.md](ABOUT.md) covers what lives here and what stays private.

Contributions follow the same contract as any change: `thea verify` must pass, and the pull request
template asks what would prove the goal met. Licensed under the [MIT License](LICENSE).
