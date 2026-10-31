# GitHub Finalization and Security/AI Stack

Headron Software: rules and build checks for AI coding agents, with a Python harness. Finalization should add controls without forcing every possible tool onto every change.

## What is enforced, and how you check it

**Nothing on this page states the current platform state.** An audit typed into prose is honest on
the day it is written and unfalsifiable afterwards; three lines of an earlier audit here had gone
stale and read as current. The state is declared as data in
[config/github-controls.json](../config/github-controls.json) and compared to the live API by
`python scripts/ghaudit.py`, which exits non-zero on any difference and refuses when it cannot
reach GitHub.

### Ruleset and required checks

The control declaration names the intended rules, required status contexts, review parameters and
bypass actors. The audit compares them with the platform; it does not prove that a merge is
actually refused. A required context must report on every relevant pull request and must identify
the complete verification result. Before changing a ruleset, inspect its full current parameters:
an incomplete replacement can silently remove controls.

### Declared, configured, enforced — keep the three separate

| layer      | where it lives               | how it is verified                                   |
| ---------- | ---------------------------- | ---------------------------------------------------- |
| declared   | this repository, in Git      | `atlas.py check`                                     |
| configured | GitHub settings and rulesets | `ghaudit.py`                                         |
| enforced   | merge is refused without it  | a pull request failing a required check cannot merge |

A control present in the first two columns and absent from the third is an unshipped arm: it reads
as covered and stops nothing.

**Workflow files are not the workflow roster.** CodeQL, Dependabot Updates, Dependency Graph and
GitHub Advanced Security are GitHub-managed with no file in `.github/workflows/`;
`gh api .../actions/workflows` is the roster.

## Enable in GitHub settings

### CodeQL

Use **Code Security -> CodeQL analysis -> Default setup**.

Default setup is the low-maintenance choice for this atlas. It automatically selects supported languages and scans pushes, pull requests, and weekly. If no CodeQL-supported source exists, no scan is run; supported languages added later are automatically included.

Current CodeQL-supported languages: C/C++, C#, Go, Java/Kotlin, JavaScript/TypeScript, Python, Ruby, Rust, Swift, and GitHub Actions workflows.

Do not run a second full CodeQL workflow for the same repository unless a documented advanced configuration requires it.

### Copilot security and coding assistance

CodeQL enables Copilot Autofix for supported public repositories. Autofix generates a proposed remediation from a CodeQL alert; the patch still requires review and normal verification.

Copilot cloud agent can work from code-scanning alerts where available, explore related code, re-run verification, and open a PR.

Copilot code review is a secondary review layer. Repository custom instructions can steer Copilot's repository-aware work; deterministic checks remain the authority.

### Secret scanning / push protection

The controls declaration records the intended secret-scanning and push-protection settings; use
the audit to check their live state. Scanner output is not a substitute for credential rotation
when a secret is exposed.

### Dependabot / dependency graph / dependency review

Keep the dependency graph and Dependabot security updates enabled; both are repository settings
(`config/github-controls.json`) and need no file in the tree. There is no version-update config and
no dependency-review job: a dependency changes only through a reviewed lock bump that passes the
local gate (`.github/ci-local.sh`).

Do not create fake language manifests just to produce scanner coverage.

### OpenSSF Scorecard

No Scorecard workflow runs in this repository. `scripts/ghaudit.py` reads the public Scorecard API
result where one exists and reports it as unknown, never as passing, when it cannot.

### CODEOWNERS / review policy

[CODEOWNERS](../.github/CODEOWNERS) routes ownership only: code-owner review is not required, and [CERTIFICATION.md](CERTIFICATION.md) records why (no second reviewer).

### GitHub Code Quality

GitHub Code Quality is a separate paid feature tier. Keep it optional. CodeQL + native quality tools + tests are sufficient as a baseline for this atlas.

## Tool-selection matrix

| Failure class            | First                            | Second                       | Third                                       |
| ------------------------ | -------------------------------- | ---------------------------- | ------------------------------------------- |
| syntax/type              | native compiler/LSP/type checker | tests                        | reviewer                                    |
| behavior regression      | unit/property/regression         | semantic context             | CI                                          |
| dependency vulnerability | dependency graph                 | dependency review/Dependabot | upgrade test                                |
| source security          | CodeQL/native                    | Semgrep                      | independent review                          |
| secret leak              | push protection                  | secret scanning              | rotation/history remediation                |
| API breakage             | schema/contract test             | endpoint integration         | consumer test                               |
| browser/UI breakage      | Playwright                       | endpoint/service tests       | review                                      |
| DB breakage              | native DB tests/plans            | DBHub read-only              | migration rollback                          |
| concurrency              | race/sanitizer/runtime checks    | focused load                 | telemetry                                   |
| performance              | profiler/benchmark               | representative workload      | regression baseline                         |
| cross-language breakage  | schema/ABI                       | boundary test                | end-to-end                                  |
| agent mutation           | scope policy                     | diff                         | deterministic CI + independent verification |

## Do not over-stack

Optimize for coverage per tool, not tool count. Native language tools remain authoritative; MCP and AI layers should shorten context retrieval or automate a specific capability rather than duplicate an existing deterministic tool.

## Arms only the owner can close

Each needs a person or an account this repository does not hold; `ghaudit.py` reports the live
state of every one, so this list names the setting and never a score.

- **OpenSSF best-practices badge:** register the project on the badge site, then record its id in
  `config/openssf-best-practices.json`.
- **Second reviewer:** invite one human collaborator. Only then can `required_approving_review_count`,
  code-owner review and last-push approval be switched on without wedging every merge.
