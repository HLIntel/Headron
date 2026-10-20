<!-- AGENTS: do not read this page breadth-first. Plug in: `python scripts/atlas.py port <file>`,
     or parse .agent/bootstrap.json — one record back. -->
<!-- mcp-name: io.github.HeartlandIntel/thea -->
<p align="center">
  <img src="docs/media/thea-desktop-engineering-intelligence-banner.png"
       alt="Thea Desktop: engineering intelligence for the agentic era, built on HLIntel/thea-software">
</p>

<p align="center">
  <a href="https://github.com/HLIntel/thea-software/actions/workflows/atlas-ci.yml"><img
     src="https://github.com/HLIntel/thea-software/actions/workflows/atlas-ci.yml/badge.svg?branch=main"
     alt="Atlas CI"></a>
  <a href="https://github.com/HLIntel/thea-software/releases/latest"><img
     src="https://img.shields.io/github/v/tag/HLIntel/thea-software?label=contract"
     alt="contract version"></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/HLIntel/thea-software"><img
     src="https://api.securityscorecards.dev/projects/github.com/HLIntel/thea-software/badge"
     alt="OpenSSF Scorecard"></a>
  <a href="https://pypi.org/project/thea-software/"><img
     src="https://img.shields.io/pypi/v/thea-software?label=PyPI"
     alt="PyPI version"></a>
  <a href="https://pypi.org/project/thea-software/"><img
     src="https://img.shields.io/pypi/pyversions/thea-software"
     alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
</p>

<!-- BEGIN generated: headline (python scripts/atlas.py index --write) -->

**Measured:** the commands that prove a change, build-enforced ([evidence](#what-it-measurably-buys)). Agents: [llms.txt](llms.txt); chats: [CHAT.md](CHAT.md).

<!-- END generated: headline -->

**Start:** [install/use](#quickstart) · [agents](llms.txt) · [chat](CHAT.md) · [adapters](models/README.md)

## What it does

Thea turns repository policy into executable verification. [`atlas.yaml`](atlas.yaml) tells agents
what proves each file's change; CLI, MCP, hooks, CI and adapters enforce it. Gates report `PASS`,
`FAIL` or `NOT RUN` — missing tools never become green.

<!-- BEGIN generated: proof-flow (python scripts/atlas.py index --write) -->

```mermaid
---
config:
  theme: base
  themeVariables:
    primaryColor: "#e6f2e7"
    primaryBorderColor: "#6f9f73"
    primaryTextColor: "#14301a"
    lineColor: "#7f9483"
    fontSize: "15px"
  flowchart:
    padding: 6
    nodeSpacing: 14
    rankSpacing: 18
---
flowchart TB
  accTitle: How Thea is built
  accDescr: the contract says what must be checked and what counts as proof, one core resolves the file, selects its gates, runs the checks and records the verdict, and the CLI, MCP, hooks with CI and the Thea Desktop all reach that one core
  R[contract · atlas.yaml<br>what counts as proof] --> C[one core: resolve, gate,<br>check, record the verdict]
  C --> doors
  subgraph doors [ ]
    direction TB
    L[CLI<br>commands] ~~~ H[hooks · CI<br>commit, merge]
    P[MCP<br>agent tools] ~~~ B[Thea Desktop<br>results, history]
  end
  classDef core fill:#cfe9d2,stroke:#4f9a58,color:#103d17
  class C core
  classDef band fill:none,stroke:#6f9f73,stroke-dasharray:4 3
  class doors band
```

<!-- END generated: proof-flow -->

<!-- BEGIN generated: gate-example (python scripts/atlas.py index --write) -->

```console
$ thea gate scripts/doctor.py
1. formatter: ruff format --check scripts/doctor.py
2. compiler_or_typechecker: python3 -c 'import ast,sys; [ast.parse(open(f, encoding="utf-8").read(), f) for f in sys.argv[1:]]' scripts/doctor.py
3. unit_tests: pytest
```

<!-- END generated: gate-example -->

**Adapters:** Claude Code, Codex, GitHub Copilot, Cursor/Grok Bot, OpenCode, Hermes, VS Code, Thea Desktop,
`llms.txt` and MCP; git hooks and Actions cover builds ([all runtimes](models/README.md)).

Thea verifies development work; it does not replace its framework or toolchain ([limits](docs/CERTIFICATION.md#what-the-numbers-do-not-prove)).

## Quickstart

<!-- BEGIN generated: install (python scripts/atlas.py index --write) -->

```bash
# no checkout
uv tool install thea-software && thea doctor
# or, editable
git clone --depth 1 --branch v3.59.0 https://github.com/HLIntel/thea-software ~/thea && uv tool install --editable ~/thea && thea doctor
```

<!-- END generated: install -->

```bash
cd ~/thea
thea port scripts/doctor.py   # route, gates, lessons
thea gate scripts/doctor.py   # what proves a change
thea verify                   # exit 0 only if all PASS
```

Read-only MCP: `thea-mcp`. No-shell chat: [CHAT.md](CHAT.md). Add Thea to another repository:
[CONSUMING](docs/CONSUMING.md).

## Thea Desktop preview

Thea Desktop is agent engineering on the thea-software foundation. The CLI is
public; [request access](https://github.com/HLIntel/thea-software/issues/new?title=Thea%20Desktop%20preview%20request)
(no secrets or private code). [Limits](docs/CONSUMING.md#optional-hlintel-services).

<!-- BEGIN generated: port-example (python scripts/atlas.py index --write) -->

```console
$ thea port scripts/doctor.py --line
◉ scripts/doctor.py │ ⠟backend │ python │ ⌂scripts │ ✓3 │ ⚠1 │ → thea gate scripts/doctor.py
$ thea port scripts --line
◎ scripts │ ⠟122 │ ⌂scripts │ → thea brainstorm
$ thea port . --line
○ . │ ⠟150 ⠁4 ⠿4 │ → thea check
```

<!-- END generated: port-example -->

## What it measurably buys

Recorded instruments prove routing and refusals, not end-to-end task success
([limits](docs/CERTIFICATION.md#what-the-numbers-do-not-prove)).

<!-- BEGIN generated: measured-benefits (python scripts/atlas.py index --write) -->

_With Thea_ the model sees what `thea gate` prints; _blind_ it sees only the language names.

**Right answers, with Thea vs blind** (`abtest.py` v3.49.0, 76 questions per Claude model)

- **Opus:** 100% vs 41%; 90% fewer tokens.
- **Sonnet:** 100% vs 39%; 90% fewer tokens.
- **Haiku:** 100% vs 39%; 91% fewer tokens.
- **Claude Code start-up:** 221 tokens (`CLAUDE.md` and its imports).

- **All 8 models** (4 providers, 423 trials, v2.28.0 / v3.49.0): 99% vs 53% (95% intervals 98–100, 49–58); weakest 97%; a random guess 2.8%.

**Beyond routing** (blind → with Thea, `taskbench.py` v2.29.0)

- **Name a failure from its symptom:** Opus 93% → 100% · Sonnet 57% → 100% · Haiku 64% → 96%
- **List the checks a change needs:** Opus 12% → 100% · Sonnet 12% → 100% · Haiku 0% → 100%
- **Spot a line the build refuses (coin flip: 50%):** Opus 60% → 100% · Sonnet 60% → 100% · Haiku 40% → 100%
- **Hand off with the right checks** (schema only → with Thea, `workflowbench.py`): Opus 0/6 → 6/6 · Sonnet 0/6 → 6/6 · Haiku 0/6 → 6/6
- _Not measured:_ visual design, open-ended strategy, arithmetic — nothing declares a right answer.

**Failures caught**

- **24/24** planted breaks refused at commit, in 16 of 42 languages; 21 have an example not yet trialled, 5 none (`enforce.py` v3.58.0).
- **548** mistake kinds planted in the tests, each refused.
- **117** failure shapes recorded from real runs: 201 sightings, 45 recurred, 96 now guarded.
- **245** refusals in daily use (26 shapes, 166 re-fired); verify 21 pass / 40 fail; 46/48 lands armed; 139 lessons shown (`agents.py --field` v3.54.0).
- **24/24** solo commits clean with or without the hook; a planted broken commit is refused.
- **6** agent controls block, never warn: narrow_tools, sandbox, budget, approval, effects, audit.

**Cost**

- **1,734** tokens read before routing; 196 more documents (612 KiB) load only when a route names one.
- **89%** fewer tokens than pasting every tool list; 50% fewer than blind.
- **10 KiB** install: 1 module, 1 dependency.

**Coverage**

- **378** language × check pairs (42 × 9), all answered: 146 by a command, 232 by a declared _no tool_, 0 silent.

<!-- END generated: measured-benefits -->

## Agent contract

- **Route:** `thea port <file>`, or parse [.agent/bootstrap.json](.agent/bootstrap.json); load only its names.
- **Automate:** add `--json`; records follow [the output schema](tools/atlas-output.schema.json).
- **Before shell:** `thea shell --json "<cmd>"`; exit 3 means its verdict would be misread.
- **Land:** `python scripts/branchstate.py --land`; check `thea landed <branch>` before deletion.
- **Judge and report:** use the [judgment rungs](docs/systems/AGENT-HARNESS.md#judgment-rungs); file breaks with the [`thea` skill](skills/thea/SKILL.md).

## Counts, computed

Generated on every build; `check` refuses drift. Machine-readable: [.agent/facts.json](.agent/facts.json).

<!-- BEGIN generated: repository-facts (python scripts/atlas.py index --write) -->

- **401** tool entries — across 42 manifests and 5 kinds, validated against `tools/tools.schema.json`
- **335** agreement edges — each a file tied to the declaration it answers for
- **82** instruments — each stating what it proves, what it does not, and what closes the gap
- **8** change classes — and 14 task profiles, in `atlas.yaml`
- **122** harness Python files — every one held by `lint` · `format` · `typecheck`
- **3.59.0** contract version — `VERSION`, asserted in 8 other files

<!-- END generated: repository-facts -->

## Find your way

- **Every document:** [docs index](docs/INDEX.md) · [wiki](docs/wiki/README.md)
- **Languages:** [atlas](languages/ATLAS.md) · [routing](docs/wiki/CODE-ROUTING.md) · [verification](docs/VERIFY.md)
- **Agents:** [harness](docs/systems/AGENT-HARNESS.md) · [`.thea`](docs/THEA-LANGUAGE.md) · [runtimes](models/README.md)
- **Why a rule:** `thea why` · `thea failures` · [instruments](docs/INSTRUMENTS.md)
- **Security:** [policy](SECURITY.md) · [OpenSSF](docs/OPENSSF.md) · [contributing](CONTRIBUTING.md)

## Project

Version tracks the **contract**, not content ([versioning](docs/VERSIONING.md)).
Built by **HLIntel LLC**, public on purpose ([about](ABOUT.md)). Contributions pass `thea verify`. [MIT License](LICENSE).

Updated: contract v3.59.0
