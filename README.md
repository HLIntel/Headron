<!-- AGENTS: do not read this page breadth-first. Run `headron port <file>` (in a clone,
     `python scripts/atlas.py port <file>`), or parse .agent/bootstrap.json. -->
<!-- mcp-name: io.github.HLIntel/headron -->
<div align="center">
  <img src="https://raw.githubusercontent.com/HLIntel/Headron/main/docs/media/headron-banner.jpg"
       alt="Headron Software: AI governance and verification"
       width="992">
  <h1>Headron Software</h1>
</div>

<!-- BEGIN generated: badges (python scripts/atlas.py index --write) -->

**Contract 3.62.0** · MIT · verdicts carry receipts: `headron verify --receipt <file>`

<!-- END generated: badges -->

<!-- BEGIN generated: headline (python scripts/atlas.py index --write) -->

- **Is:** a rule contract and CLI mapping changed files to checks. Hooks are optional; `headron verify` runs done gates.
- **Is not:** a coding agent, model, test framework, or proof code is correct. A check that cannot run reports SKIP or NOT RUN, never a pass; the hook lets that commit through.
- **`headron init` writes:** AGENTS.md, CLAUDE.md, .mcp.json, .codex/config.toml, .git/hooks/pre-commit. Use `--no-wiring` to skip hooks and configuration; `headron enforce uninstall` restores a displaced hook.
- **Mind API:** hosted, paid, needs a key; plans a declared change. The command line works without it.

Agents: [llms.txt](llms.txt). Chats: [CHAT.md](CHAT.md). [Evidence](#recorded-results).

<!-- END generated: headline -->

## Why this exists

Headron connects changed files to declared checks and reports whether those checks ran. A skipped
check is not a pass. An optional Git hook can run checks before a commit, whether the change came
from a developer or an agent.

## How it works

`headron port <file>` tells an agent what a file owes before it edits. [`atlas.yaml`](atlas.yaml)
holds those checks; the commit hook and CI report `PASS`, `FAIL`, `SKIP` or `NOT RUN`. The hosted
[Mind API](https://headron.tech/mind-api.html) plans a declared change through `headron mind`.

<!-- BEGIN generated: proof-flow (python scripts/atlas.py index --write) -->

<p align="center">
  <img src="docs/media/headron-proof-flow.svg" width="900"
       alt="Headron Architecture: contract, targeted evidence, integrity audit, unified verdict.">
</p>

<!-- END generated: proof-flow -->

<!-- BEGIN generated: gate-example (python scripts/atlas.py index --write) -->

```console
$ headron gate scripts/doctor.py
1. formatter: ruff format --check scripts/doctor.py
2. compiler_or_typechecker: python3 -c 'import ast,sys; [ast.parse(open(f, encoding="utf-8").read(), f) for f in sys.argv[1:]]' scripts/doctor.py
3. unit_tests: pytest
```

<!-- END generated: gate-example -->

## Quickstart

<!-- BEGIN generated: install (python scripts/atlas.py index --write) -->

```bash
# install
uv tool install headron-software && headron doctor
# editable, to change Headron itself
git clone --depth 1 --branch v3.62.0 https://github.com/HLIntel/Headron ~/headron && uv tool install --editable ~/headron && headron doctor
```

<!-- END generated: install -->

In your repository:

```bash
cd path/to/your-repo && headron init   # finds your checks, wires your agents, installs the commit hook, runs once
headron verify && headron proof <file> --verify   # after a change: verdicts, then a file's proof
```

With an impact map, `headron verify --changed` evaluates checks for modified files.
Target a specific profile with `headron verify --changed --change <class>` (e.g. `source_change`, `api_change`, `security_sensitive`); `headron verify` remains the final full verdict.

**Machines:** [bootstrap](.agent/bootstrap.json), [facts](.agent/facts.json), and [JSON schema](tools/atlas-output.schema.json).
**Agents:** [adapters](models/README.md); the MCP interface is read-only.
**Another repository:** [CONSUMING](docs/CONSUMING.md).

## Recorded results

See the [instrument limits](docs/CERTIFICATION.md#what-the-numbers-do-not-prove) for their scope.

<!-- BEGIN generated: measured-benefits (python scripts/atlas.py index --write) -->

<!-- prettier-ignore -->
| Instrument | Recorded result |
| :--- | :--- |
| Enforcement | 31/31 breaks refused across 20 toolchains; **815** declared planted cases |
| Failure ledger | 128 shapes, 220 sightings; 103 in-tree guarded, 25 host-only |
| Field ledger | 940 verifications (136 clean); 1133 refusals; 394 landings; 711 lessons; 394 sessions |
| Verification outcomes | 17,397 checks: 7,357 PASS, 1,097 REUSED, 1,278 FAIL, 7,665 NOT RUN. 533 runs failed; 271 stopped with an unrun check; 0 reported clean despite a failed or unrun check |
| Routing experiment | 89% fewer prompt tokens than whole-tree; 50% fewer than unassisted, across identified models |
| Language roles | 360 pairs: 110 runnable, 0 undeclared |

Entry context: ~1,593 tokens. The 211 documents (707 KiB) load on demand; install: 10 KiB; hash lock with test tools: 8 packages.
[Field records](benchmarks/field-latest.json). [Routing data](benchmarks/ab-latest.json). Measures can overlap.

<!-- END generated: measured-benefits -->

## Where it fits

- **Agents and runtimes:** [adapters](models/README.md) describe supported integrations.
- **Headron-Harness:** a separate desktop dashboard and runtime; see [product boundaries](docs/PRODUCT-STRATEGY.md).
- **Other repositories:** `headron init` sets up a repository; [CONSUMING](docs/CONSUMING.md) covers CI, the [GitHub Action](docs/CONSUMING.md#as-a-github-action) and the [hosted MCP](docs/CONSUMING.md#hosted-mind-api--mcp).
- **Languages:** routes declare available checks and identify checks without a tool.

## Agent contract

<!-- BEGIN generated: port-example (python scripts/atlas.py index --write) -->

```console
$ headron port scripts/doctor.py --line
◉ scripts/doctor.py │ ⠟backend │ python │ ⌂scripts │ ✓5 │ ⚠2 │ → headron gate scripts/doctor.py
$ headron port scripts --line
◎ scripts │ ⠟186 │ ⌂scripts │ → headron brainstorm
$ headron port . --line
○ . │ ⠟214 ⠿4 ⠁1 │ → headron check
```

<!-- END generated: port-example -->

- **Discover:** `headron find <query>` searches paths, symbols and vocabulary; `headron sweep` maps topology. Search does not guarantee semantic recall.
- **Route:** `headron port <file>`, or parse [.agent/bootstrap.json](.agent/bootstrap.json); load only its names.
- **Processes:** `headron process [<id>] --json` lists workflows; with an id, its steps and gates.
- **Mind:** `headron mind --route <file>` routes; `headron mind --receipts` summarizes the latest local verification record.
- **Beliefs:** `headron revise` names what rests on a refuted claim; `headron propose` drafts each fix outside the tree.
- **Automate:** add `--json`; records follow [the output schema](tools/atlas-output.schema.json).
- **Before shell:** `headron shell --json "<cmd>"`; exit 3 means its verdict would be misread.
- **Land:** `python scripts/branchstate.py --land`; check `headron landed <branch>` before deletion.
- **Judge and report:** use the [judgment rungs](docs/systems/AGENT-HARNESS.md#judgment-rungs); file breaks with the [`headron` skill](skills/headron/SKILL.md).

## Find your way

- **Every document:** [docs index](docs/INDEX.md) · [wiki](docs/wiki/README.md)
- **Languages:** [atlas](languages/ATLAS.md) · [routing](docs/wiki/CODE-ROUTING.md) · [verification](docs/VERIFY.md)
- **Agents:** [harness](docs/systems/AGENT-HARNESS.md) · [`.headron`](docs/HEADRON-LANGUAGE.md) · [runtimes](models/README.md)
- **Why a rule:** `headron why` · `headron failures` · [instruments](docs/INSTRUMENTS.md)
- **Companion products:** [desktop, web, enterprise](docs/CONSUMING.md#optional-hlintel-services)
- **Security:** [policy](SECURITY.md) · [OpenSSF](docs/OPENSSF.md) · [contributing](CONTRIBUTING.md)

## Counts, computed

Generated on every build; `check` refuses drift.

<!-- BEGIN generated: repository-facts (python scripts/atlas.py index --write) -->

- **52** hard invariants — enforced on every change, zero unowned
- **367** agreement edges — each a file tied to the declaration it answers for
- **95** instruments — each stating what it proves, what it does not, and what closes the gap
- **385** tool entries — across 40 manifests and 5 kinds, validated against `tools/tools.schema.json`
- **184** harness Python files — every one held by `lint` · `format` · `typecheck`
- **3.62.0** contract version — `VERSION`, asserted in 10 other files

<!-- END generated: repository-facts -->

## Project

Version tracks the **contract**, not content ([versioning](docs/VERSIONING.md)).
Built by **HLIntel LLC**, public on purpose ([about](ABOUT.md)). Contributions pass `headron verify`. [MIT License](LICENSE).

Updated: contract v3.62.0
