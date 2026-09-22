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
12. common mistakes
13. streamlining
14. learning direction
15. avoid
16. AI coding directive
17. verification
18. worktree/parallel development
19. official sources
20. VS Code + MCP integration

The final section must name native editor/LSP/debugger/test tooling, MCP recommendation level, applicable shared profiles, duplication to avoid, external services/keys, and bounded tool behavior.

Do not invent dedicated MCPs. When none is credible, use native tooling plus the shared GitHub/documentation/semantic layers where appropriate.
