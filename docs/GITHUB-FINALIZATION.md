# GitHub Finalization and Security/AI Stack

This repository is public and behaves as a documentation-heavy engineering atlas with Python verification code. Finalization should add controls without forcing every possible tool onto every change.

## Current audit — measured 2026-09-24

**An audit with no date is a claim with no expiry.** Three lines of the previous audit had gone
stale and read as current: it said topics were empty, that no ruleset was returned, and that
branch-protection detail was unreachable. All three were false by the time anyone read them.
Every line below names the instrument that produced it, so the next reader can re-run it rather
than trust it.

Instrument: `gh api repos/ApianSoftware/Code-Development`, `.../rulesets`, `.../actions/workflows`.

- public repository · default branch `main` · topics: `ai-agents, code-quality, developer-tools,
  mcp, polyglot, static-analysis` (**six, not empty**)
- secret scanning **enabled** · push protection **enabled**
- ruleset `main-protection` (id 23838023) is **active** on branch target and IS readable —
  administrative access is no longer the blocker it was recorded as
- six workflows active: Atlas CI, Dependency Review, OpenSSF Scorecard, Dependabot Updates,
  Dependency Graph, CodeQL

### The gap this audit exists to surface

`main-protection` enforces exactly three rules — `deletion`, `non_fast_forward` and
`required_linear_history`. It **requires no pull request, no approving review, and no status
check.** Atlas CI, Dependency Review and CodeQL all run, and **nothing makes any of them pass
before a merge.** The contract harness that this repository is built around is therefore
advisory on the default branch: a direct push with a failing contract is accepted.

That is the difference between policy DECLARED in Git, policy CONFIGURED in GitHub, and policy
ENFORCED at merge. This repository currently has the first two and not the third.

**Required checks to add, by their exact job names** (a ruleset naming a check that does not exist
blocks every merge, so these are copied from the live workflow list, not typed from memory):
`Atlas CI`, `Dependency Review`. Add `CodeQL` only once it reports for this repository's Python.

### Declared, configured, enforced — keep the three separate

| layer | where it lives | how it is verified |
|---|---|---|
| declared | this repository, in Git | `atlas.py check` |
| configured | GitHub settings and rulesets | `gh api .../rulesets` |
| enforced | merge is refused without it | a PR that fails a required check cannot merge |

A control present in the first two columns and absent from the third is an unshipped arm: it reads
as covered on the roster and stops nothing.

Three workflows are file-declared in `.github/workflows/`; **CodeQL, Dependabot Updates and
Dependency Graph are GitHub-managed default setup and have no file in this repository.** Neither
form is wrong, but a reader who greps `.github/workflows/` sees three and the repository runs six.

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
