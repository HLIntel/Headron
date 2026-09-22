# Language Stack Specification

Every language guide follows the same reasoning schema so agents can switch languages without changing their operating model.

## Required sections
1. Purpose
2. When to use
3. When not to use
4. Core guarantees/model
5. Stack/toolchain
6. Project/package/workspace structure
7. Data/state/mutation model
8. Concurrency model
9. Interoperability/FFI
10. Performance/profiling
11. Security/hygiene
12. Common mistakes
13. Streamlining/efficiency
14. What to learn into next
15. What to avoid
16. AI coding directive
17. Verification
18. Worktree/parallel-development
19. Official sources

## Interoperability
Every guide should state how the language crosses:
- process boundaries
- native FFI boundaries
- service/RPC boundaries
- data/columnar boundaries
- WebAssembly boundaries where relevant

Name ownership, lifetime, serialization, compatibility, error, timeout, and observability expectations rather than merely listing libraries.

## Consistency rule
If a language lacks a tool or feature, say so. Do not force every language into the same architecture.

## Status tags
production, mature-specialized, experimental, research

## Evidence rule
Do not convert ecosystem claims into repository facts without a primary source. Mark experimental or aspirational claims explicitly.
