# GitHub Finalization and Security/AI Stack

This repository is public and currently behaves as a documentation-heavy engineering atlas with Python verification code. Finalization should add controls without forcing every possible tool onto every change.

## Current audit

Verified through GitHub:
- public repository
- default branch: `main`
- GitHub Actions present
- repository Wiki capability is enabled
- repository topics are empty
- no GitHub rulesets are returned by the accessible ruleset endpoint
- branch-protection details require administrative access unavailable to the current connector

The dependency graph has been enabled for this repository.

## Enable in GitHub settings

### CodeQL

Use **Code Security -> CodeQL analysis -> Default setup**.

Default setup is the low-maintenance choice for this atlas. It automatically selects supported languages and scans pushes, pull requests, and weekly. If no CodeQL-supported source exists, no scan is run; supported languages added later are automatically included.

Current CodeQL-supported languages: C/C++, C#, Go, Java/Kotlin, JavaScript/TypeScript, Python, Ruby, Rust, Swift, and GitHub Actions workflows.

Do not run a second full CodeQL workflow for the same repository unless a documented advanced configuration requires it.

### Copilot security and coding assistance

CodeQL enables Copilot Autofix for supported public repositories. Autofix generates a proposed remediation from a CodeQL alert; the patch still requires review and normal verification.

Copilot cloud agent can work from code-scanning alerts where available, explore related code, re-run verification, and open a PR.

Copilot code review is a separate AI reviewer. Treat it as secondary review, not the authoritative verifier.

Repository instructions live in [.github/copilot-instructions.md](../.github/copilot-instructions.md). They improve repository-aware Copilot Chat/CLI/cloud-agent work. Do not depend on them as a deterministic CI gate.

### Secret scanning / push protection

Public repositories receive secret scanning automatically. Enable repository-level push protection so supported secrets are blocked before landing. Keep user-level push protection enabled.

GitHub also applies push-protection behavior to GitHub MCP interactions with public repositories.

### Dependabot

Keep Dependabot alerts/security updates enabled. This repository includes [.github/dependabot.yml](../.github/dependabot.yml) for weekly GitHub Actions updates.

Add language ecosystems only when real manifests/lockfiles exist.

### Dependency review

[dependency-review.yml](../.github/workflows/dependency-review.yml) checks introduced dependency changes and fails on high or critical vulnerabilities. Once stable, make the check required for `main`.

### OpenSSF Scorecard

[scorecard.yml](../.github/workflows/scorecard.yml) adds a separate supply-chain/workflow-hygiene signal and uploads SARIF to code scanning.

This complements:
- CodeQL -> source security
- Scorecard -> workflow/supply-chain posture
- secret scanning -> credential exposure
- dependency review -> introduced dependency risk

### GitHub Code Quality

GitHub Code Quality is a Team/Enterprise Cloud feature. It uses CodeQL-based quality rules, coverage signals, and Copilot-powered fixes. Keep it optional rather than treating it as a public/Free baseline.

### Branch/ruleset finalization

When administrative access is available, protect `main` with successful CI/security checks, no force pushes, no branch deletion, and review requirements appropriate to the repository's collaboration model.

Do not add elaborate deployment environments or merge queues until the repository has real production artifacts that need them.

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

Do not simultaneously load multiple tools that produce the same signal. Optimize for coverage per tool, not tool count.
