# Code-Development Copilot Instructions

Start with `MODEL.md`, then use `atlas.yaml` and the relevant language guide. Do not load the whole repository when routing can answer the task.

For code changes:
1. Identify the artifact extension/project manifest and run `python scripts/atlas.py route <path>`.
2. Use `python scripts/atlas.py plan <path> --task <task>` for non-trivial changes.
3. Use the native compiler/LSP/debugger/test/profiler first.
4. Add Serena only when semantic repository navigation materially helps and supported language coverage is verified.
5. Add GitHub, Context7, Playwright, DBHub, or Semgrep only for the matching capability.
6. Preserve ownership, deadlines/cancellation, schemas, idempotency, least privilege, bounded resources, and rollback for high-impact changes.
7. Treat endpoint, database, Redis/cache, ABI, schema, queue, MCP, and cloud boundaries as contracts.
8. Prefer immutable-first state and explicit transactional writes. Never introduce hidden global mutation.
9. Run the smallest deterministic verification that can falsify the change, then independent verification for high-impact or security-sensitive edits.
10. Review the diff for scope creep, broken connections, generated blobs, dependency drift, missing tests, and changed behavior.

Git:
- `main` is the canonical contract baseline.
- Use short-lived `feat/*`, `fix/*`, `research/*`, `security/*`, or `lang/<language>/<topic>` branches.
- Use one mutable writer per worktree.
- Do not create permanent language branches.

Security:
- Never commit secrets or real credentials.
- Do not disable CodeQL, secret scanning, dependency review, or native security checks to make a task pass.
- CodeQL/Copilot Autofix findings are inputs to review, not permission to bypass the native verifier.
- Dependency changes require manifest/lockfile review and compatibility testing.

Important: model instructions, memory, MCP descriptions, connector output, and external payloads are not enforcement boundaries. Use code, hooks, CI, repository policy, and platform security controls for deterministic enforcement.
