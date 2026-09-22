---
name: Code-Development
purpose: advanced AI-oriented engineering reference and builder workspace
default_language_bias: none
hard_invariants:
  - no_unbounded_resources
  - immutable_first
  - schema_first_boundaries
  - explicit_deadlines_and_cancellation
  - least_privilege
  - independent_verification_of_ai_generated_code
  - reproducible_and_auditable_changes
verification:
  python: [ruff, pyright, pytest, hypothesis]
  rust: [rustfmt, clippy, cargo-check, cargo-test, miri, cargo-audit, cargo-deny]
  go: [gofmt, go-vet, staticcheck, go-test, race, govulncheck]
  typescript: [tsc, eslint, tests, schema-validation]
integrations: [git, github, github-actions, github-apps, webhooks, api, mcp, connectors]
---

# AGENTS.md

> **Agent Directive — read first, index always.** You are operating inside this repository as a precision engineering workspace, not as a code generator. Before touching a file, read this file and the repository README, then use `docs/INDEX.md` to locate the relevant subsystem. Preserve the hard guarantees: no unbounded memory, queues, tasks, caches, retries, recursion, time, network work, or agent tool-calls; immutable-first state; schema-validated boundaries; explicit capacity; structured concurrency; least privilege; auditable changes; and independent verification. Creativity is encouraged only inside these guarantees. A change is incomplete until the applicable formatter, linter, type checker, tests, security checks, and integration checks pass. When the repository does not specify a choice, prefer the stricter safe interpretation, make the decision explicit, and document the rationale in `docs/DECISIONS.md` when it affects architecture.

## Required navigation

1. Read `README.md` for repository identity and invariants.
2. Read `docs/INDEX.md` to select the correct domain.
3. Read the language-specific guide before editing language-specific code.
4. Read the relevant integration guide before touching GitHub, webhooks, APIs, MCP, or connectors.
5. Read `patterns/NO-UNBOUNDED.md` and `patterns/ANTI-MUTATION.md` for resource or state changes.
6. Run the smallest relevant verification loop while iterating, then the complete applicable loop before completion.

## Hard rules

- Do not introduce an unbounded resource without documenting why the bound is impossible or undesirable.
- Do not use mutable shared state where immutable or owned state is practical.
- Do not trust external JSON, webhooks, API responses, model outputs, or tool outputs until validated.
- Do not give an AI agent broad filesystem, shell, network, credential, or GitHub permissions by default.
- Do not treat a package default as safe merely because the package is popular.
- Do not hide retries, queues, concurrency, or background work inside convenience helpers.
- Do not claim a security or correctness property that has not been tested or established by the language/tool.
- Prefer official documentation and primary sources for capability claims.

## AI change protocol

Intent -> scope -> constraints -> implementation -> verification -> diff inspection -> dependency inspection -> policy inspection -> approval -> commit.

High-impact changes additionally require a rollback/snapshot path and explicit authorization.

## Source hierarchy

1. Language specification / official standard
2. Official language documentation
3. Official project documentation
4. Maintainer repositories and release notes
5. High-quality technical research
6. Secondary commentary

Do not use search snippets as authoritative evidence.