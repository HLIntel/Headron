# Language Stack Specification

Every language guide in this repository follows the same schema so agents can switch languages without changing their reasoning model.

## Required sections
1. Purpose
2. When to use
3. When not to use
4. Core guarantees/model
5. Stack/toolchain
6. Project/package/workspace structure
7. Data/state/mutation model
8. Concurrency model
9. Performance/profiling
10. Security/hygiene
11. Common mistakes
12. Streamlining/efficiency
13. What to learn into next
14. What to avoid
15. AI coding directive
16. Verification
17. Worktree/parallel-development
18. Official sources

## Consistency rule
If a language lacks a tool or feature, say so. Do not force every language into the same architecture.

## Status tags
- `production` — appropriate for production under normal engineering controls
- `mature-specialized` — mature but scope-specific
- `experimental` — useful for research/evaluation, not a default production choice
- `research` — primarily useful for language/algorithm research

## Evidence rule
Do not convert an ecosystem claim into a repository fact without a primary source. Mark experimental or aspirational claims explicitly.