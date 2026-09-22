# Security and Code Hygiene

Security is a development workflow, not a final audit.

## Core tools
- Semgrep
- Gitleaks
- Trivy
- CodeQL
- OpenSSF Scorecard
- Renovate
- Dependabot
- pre-commit
- cargo-audit
- cargo-deny
- govulncheck
- staticcheck
- Ruff
- Pyright
- Clippy

## Pipeline
format -> lint -> type-check -> tests -> property/fuzz -> SAST -> secret scan -> dependency audit -> build -> integration -> artifact verification

## Dependency policy
Document package sources, lockfile policy, version pinning, update cadence, vulnerability response, license policy, and tolerance for transitive dependencies.

## Fail-closed examples
- secret detected -> fail
- type error -> fail
- critical dependency vulnerability -> block or fail
- invalid schema -> fail
- destructive agent operation -> approval or block

## Supply chain
Study signed releases, provenance, pinned dependencies, GitHub workflow permissions, dependency update automation, and OpenSSF Scorecard checks.