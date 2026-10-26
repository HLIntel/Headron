## Routing

- Language/domain: <!-- e.g. Python verifier, GitHub integration -->
- Task: <!-- user outcome, not implementation-only -->
- Affected paths: <!-- every changed source, declaration, and generated file -->
- Branch/worktree: <!-- branch name and any lane being closed -->
- Relevant labels: <!-- routing, risk, or release labels -->

## Change

<!-- State the consumer-visible outcome and the smallest reason this change is needed. -->

## Verification

- Native compiler/LSP/checker: <!-- command + exit code, or NOT RUN -->
- Unit/property/integration tests: <!-- command + exit code, or NOT RUN -->
- Mutation testing or fuzzing: <!-- command + exit code, or NOT RUN -->
- Security/dependency checks: <!-- command + exit code, or NOT RUN -->
- Endpoint/DB/boundary tests: <!-- command + exit code, or NOT RUN -->
- CI result: <!-- head SHA and required checks -->

## Breakage review

- [ ] API/schema/ABI compatibility checked
- [ ] Timeouts/retries/cancellation are bounded
- [ ] State ownership and mutation are explicit
- [ ] No unintended generated/blob artifacts
- [ ] Dependencies/lockfiles reviewed
- [ ] Scope is limited to the task
- [ ] High-impact changes have rollback or snapshot coverage

## AI/tooling

List any model, MCP, connector, browser, database, security, or automated reviewer that materially changed or verified the code.
