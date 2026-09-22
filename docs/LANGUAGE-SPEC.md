# Language Stack Specification

Every language guide follows a common reasoning schema so agents can switch languages without changing their operating model.

Required:
1. purpose
2. when to use
3. when not to use
4. guarantees/model
5. stack/toolchain
6. project/package/workspace
7. state/mutation
8. concurrency
9. interoperability/FFI
10. performance/profiling
11. security/hygiene
12. cloud/deployment shape
13. uptime/reliability/observability
14. Redis/Upstash/cache/data stores
15. database/schema/transaction practice
16. endpoint/API/webhook testing
17. mutation/property/fuzz/regression testing
18. bug and breakage prevention
19. blob/module-growth prevention
20. common mistakes
21. streamlining
22. learning direction
23. avoid
24. AI coding directive
25. verification
26. worktree/parallel development
27. official sources
28. VS Code + MCP integration

Shared production-operations details live in [wiki/LANGUAGE-OPERATIONS.md](../wiki/LANGUAGE-OPERATIONS.md), while each language guide retains decisions that materially affect runtime, data, endpoints, testing, or failure behavior.

The final section must name native editor/LSP/debugger/test tooling, MCP recommendation level, applicable shared profiles, duplication to avoid, external services/keys, and bounded tool behavior.

Do not invent dedicated MCPs. When none is credible, use native tooling plus the shared GitHub/documentation/semantic layers where appropriate.
