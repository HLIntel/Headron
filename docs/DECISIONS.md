# Architecture Decisions

Use this file as the short index of decisions. Detailed decisions can become `docs/decisions/ADR-####-slug.md` later.

## Decision template

```markdown
# ADR-####: Title

Status: proposed | accepted | superseded | rejected

## Context

## Decision

## Why

## Alternatives considered

## Invariants preserved

## Tradeoffs

## Verification

## References
```

## Rules

- Record decisions that affect architecture, security, state ownership, resource bounds, integration trust, or deployment behavior.
- Do not record trivial implementation choices.
- When a package is selected over an alternative, capture the scoped reason.
- If a later decision changes the architecture, mark the old decision superseded rather than silently rewriting history.