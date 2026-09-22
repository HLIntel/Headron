# GitHub Tool Atlas

Use the narrowest GitHub surface that can complete the task.

| Tool | Best use |
|---|---|
| `git` | local history, branches, worktrees, diff |
| `gh` | human/CLI GitHub workflows |
| REST API | deterministic resource operations |
| GraphQL | relational/cross-resource reads |
| GitHub App | least-privilege long-lived integration |
| Actions | CI/CD and policy execution |
| Webhooks | event-driven ingress |
| GitHub MCP | model-accessible GitHub capabilities |
| repository rulesets | enforced repository policy |

## Preferred flow
`inspect -> narrow capability -> execute -> verify -> record`

## CLI
Use `gh repo`, `gh pr`, `gh issue`, `gh run`, `gh workflow`, and `gh api` for focused operations.

## API
Use pagination for collections and explicit field selection where supported. Cache stable metadata where appropriate, but never cache secrets or permission-sensitive state indefinitely.

## GraphQL
Use GraphQL when the task needs related nodes in one request. Bound pagination and field depth.

## GitHub Apps
Prefer installation-scoped permissions for service integrations. Separate read, write, and administrative capabilities.

## Actions
Use minimal permissions, reviewed/pinned actions where appropriate, protected environments for deployment, and separate build from release permissions.

## MCP
Expose GitHub MCP capabilities narrowly. Do not give a coding agent arbitrary repository administration when it only needs read, branch, commit, or PR operations.

## Automation
Keep destructive operations behind explicit policy/approval.

Official: https://docs.github.com/ , https://cli.github.com/manual/