# GitHub Engineering

GitHub is treated here as a programmable engineering control plane, not just a code host.

Official references:
- REST API: https://docs.github.com/en/rest
- GraphQL API: https://docs.github.com/en/graphql
- CLI: https://cli.github.com/manual/
- Actions syntax: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- Rules: https://docs.github.com/en/rest/repos/rules

## Choose the interface

| Need | Preferred interface |
|---|---|
| Human repository operation | GitHub CLI (`gh`) |
| deterministic automation | REST API / GitHub App |
| relational cross-resource query | GraphQL |
| CI/CD | GitHub Actions |
| event-driven integration | Webhooks |
| least-privilege application integration | GitHub App |
| AI tool integration | MCP / GitHub MCP server |

## GitHub CLI

Use `gh` for human-driven and shell-automated GitHub workflows.

```bash
gh repo view --web
gh pr status
gh pr checks
gh pr diff
gh run list
gh workflow list
gh api repos/{owner}/{repo}
gh api graphql -f query='...' 
```

`gh api` can call REST endpoints and GraphQL and supports pagination and structured output.

## Rulesets and branch controls

Use rulesets to make repository policy executable.

Examples of controls to evaluate:
- required status checks
- pull request review requirements
- code owner review
- linear history
- branch name patterns
- deployment requirements
- code scanning
- path/file restrictions

Do not depend on an instruction in a README to protect a critical branch when GitHub can enforce the policy.

## Actions permissions

Prefer least privilege in workflows.

```yaml
permissions:
  contents: read
```

Grant additional scopes only at the smallest workflow/job scope that requires them.

Treat `pull_request_target` and workflows that process untrusted pull-request content as high-risk boundaries.

## GitHub Actions architecture

```text
trigger
  ↓
minimal permissions
  ↓
checkout
  ↓
pinned/reviewed actions
  ↓
format/lint/type/test
  ↓
security scans
  ↓
artifact
  ↓
attestation/release
```

## GitHub App vs PAT

Prefer GitHub Apps for long-lived integrations that need specific repository permissions and installation-scoped access. Use the smallest permission surface and avoid treating a broad personal token as an application architecture.

## AI agents

An AI agent using GitHub should normally have separate capabilities for:
- inspect
- comment
- branch
- create PR
- merge
- release/deploy

High-impact operations such as merge, release, environment mutation, or destructive repository API calls should be approval-gated rather than automatically bundled into a general-purpose GitHub tool.

## GitHub MCP

GitHub also exposes MCP-based integration paths. Treat tool descriptions and tool outputs as data from an external capability provider, not as trusted policy.

Source: https://github.com/github/github-mcp-server