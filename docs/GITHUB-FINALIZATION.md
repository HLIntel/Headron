# GitHub Finalization and Security/AI Stack

This repository is public and behaves as a documentation-heavy engineering atlas with Python verification code. Finalization should add controls without forcing every possible tool onto every change.

## What is enforced, and how you check it

**Nothing on this page states the current platform state.** An audit typed into prose is honest on
the day it is written and unfalsifiable afterwards; three lines of an earlier audit here had gone
stale and read as current. The state is declared as data in
[config/github-controls.json](../config/github-controls.json) and compared to the live API by
`python scripts/ghaudit.py`, which exits non-zero on any difference and refuses when it cannot
reach GitHub.

### The gap this page existed to surface, and how it closed

`main-protection` enforced exactly three rules — `deletion`, `non_fast_forward` and
`required_linear_history`. It required **no pull request and no passing check**: Atlas CI,
Dependency Review and CodeQL all ran, and nothing made any of them pass before a merge, so the
contract this repository is built around was advisory on its own default branch.

It now also carries `pull_request` (zero approvals required, so a solo maintainer is not blocked)
and `required_status_checks`. Two things about those check names are worth keeping:

- **A required check is a CHECK RUN name — a job's `name:` — not a workflow name.** The gate is
  `Contract`, the job inside Atlas CI. Requiring `Atlas CI`, the workflow, would name a context
  that never reports and wedge every merge. This is the same shape as branching on a rendering
  instead of a declared identity, and the failure is silent until the first pull request.
- **A check that does not report on every pull request cannot be a gate.** `Supply-chain hygiene`
  (OpenSSF Scorecard) runs on push and on a schedule, never on a pull request. CodeQL default
  setup reported `Analyze (python)` on one pull request and `Analyze (actions)` not at all. Both
  are recorded, with the reason, under `ruleset._not_required_yet` in the declaration file, so the
  next person does not have to rediscover why a plausible context is missing.

**A bypass actor is still a bypass.** `main-protection` grants repository admins an always-bypass,
so every rule above is advisory for that role by design. `ghaudit.py` prints the bypass list beside
the verdict rather than letting a green audit imply that nobody can skip.

### Declared, configured, enforced — keep the three separate

| layer | where it lives | how it is verified |
|---|---|---|
| declared | this repository, in Git | `atlas.py check` |
| configured | GitHub settings and rulesets | `ghaudit.py` |
| enforced | merge is refused without it | a pull request failing a required check cannot merge |

A control present in the first two columns and absent from the third is an unshipped arm: it reads
as covered and stops nothing.

**Workflow files are not the workflow roster.** Three workflows are file-declared in
`.github/workflows/`; CodeQL, Dependabot Updates and Dependency Graph are GitHub-managed default
setup and have no file here. Neither form is wrong, but a reader who greps the directory sees three
where six run. `gh api .../actions/workflows` is the roster.

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

Public repositories receive secret scanning automatically. Enable repository-level push protection so supported secrets are blocked before landing. Do not treat AI instructions or scanner output as a substitute for credential rotation when a secret is exposed.

### Dependabot / dependency graph / dependency review

Keep dependency graph and Dependabot security features enabled. [dependabot.yml](../.github/dependabot.yml) currently covers GitHub Actions because this repo has no other real package manifests to update.

[dependency-review.yml](../.github/workflows/dependency-review.yml) checks introduced dependency changes and fails on high or critical vulnerabilities once a dependency delta exists.

Do not create fake language manifests just to produce scanner coverage.

### OpenSSF Scorecard

[scorecard.yml](../.github/workflows/scorecard.yml) adds supply-chain/workflow-hygiene analysis and uploads SARIF into code scanning.

### CODEOWNERS / review policy

[CODEOWNERS](../.github/CODEOWNERS) establishes repository ownership metadata. When administrative branch/ruleset controls are available, use it together with required checks and review policy appropriate to the repository.

### GitHub Code Quality

GitHub Code Quality is a separate paid feature tier. Keep it optional. CodeQL + native quality tools + tests are sufficient as a baseline for this atlas.

## Tool-selection matrix

| Failure class | First | Second | Third |
|---|---|---|---|
| syntax/type | native compiler/LSP/type checker | tests | reviewer |
| behavior regression | unit/property/regression | semantic context | CI |
| dependency vulnerability | dependency graph | dependency review/Dependabot | upgrade test |
| source security | CodeQL/native | Semgrep | independent review |
| secret leak | push protection | secret scanning | rotation/history remediation |
| API breakage | schema/contract test | endpoint integration | consumer test |
| browser/UI breakage | Playwright | endpoint/service tests | review |
| DB breakage | native DB tests/plans | DBHub read-only | migration rollback |
| concurrency | race/sanitizer/runtime checks | focused load | telemetry |
| performance | profiler/benchmark | representative workload | regression baseline |
| cross-language breakage | schema/ABI | boundary test | end-to-end |
| agent mutation | scope policy | diff | deterministic CI + independent verification |

## Do not over-stack

Optimize for coverage per tool, not tool count. Native language tools remain authoritative; MCP and AI layers should shorten context retrieval or automate a specific capability rather than duplicate an existing deterministic tool.
