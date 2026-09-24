# GitHub as a control plane

**One page, because there were two.** `GITHUB.md` and `GITHUB-TOOLS.md` covered the same nine
surfaces in the same order, with different wording and different omissions — the shape this
repository refuses everywhere else. Merged here; the tool table and the policy rules are below.

## Surface selection — the narrowest one that can finish the task

| surface | best use |
|---|---|
| `git` | local history, branches, worktrees, diff |
| `gh` | interactive and scripted repository work |
| REST API | deterministic single-resource operations |
| GraphQL | related nodes in one request, with bounded pagination and depth |
| GitHub App | least-privilege, installation-scoped service integration |
| Actions | CI and policy execution |
| Webhooks | event ingress — **and see below: this repository declares zero** |
| GitHub MCP | model-accessible capabilities, narrowed per task |
| rulesets | enforced repository policy |

`inspect -> narrow capability -> execute -> verify -> record`

## What is policy here, and where it lives

**Executable policy belongs in rulesets, Actions permissions and scanning — but the declaration
belongs in Git.** This repository states every control it expects in
[config/github-controls.json](../config/github-controls.json) and compares it to the live API with
`python scripts/ghaudit.py`, which exits non-zero on a difference and refuses rather than reporting
when it cannot reach the API. Three facts that are easy to get wrong from prose alone:

- **Actions are pinned to a commit SHA, unconditionally.** Not "where appropriate": `@v4` on
  `codeql-action` and `@v5` on `dependency-review-action` were release BRANCHES, so "pinned to v4"
  meant "whatever that branch points at today". The release tag rides in a trailing comment so
  Dependabot still maintains the pin.
- **Webhooks are declared as zero, and checked in both directions.** A webhook is an outbound data
  path; one added through the UI and recorded nowhere is a finding here, not a feature.
- **Review requirements are a recorded NON-control.** `required_approving_review_count` is 0 and
  `require_code_owner_review` is false, because a solo maintainer cannot approve their own pull
  request — making it required would make the bypass load-bearing instead of optional.
  [docs/CERTIFICATION.md](../docs/CERTIFICATION.md) records that as structural, with what it costs
  on the Scorecard branch-protection check.

## Capability bands for an agent

`read -> branch -> commit -> PR -> merge -> release/admin`

A coding agent gets the lowest band that completes the task. **Do not bundle merge, release or
admin into an ordinary coding tool**, and treat every GitHub MCP action as privileged: narrow the
imported surface and review the side effects before enabling it.

## API hygiene

Bound pagination. Select fields explicitly where the API supports it. Cache stable, non-sensitive
metadata only — never a secret and never permission-sensitive state. Handle rate limits as a
declared policy rather than a retry loop, and keep destructive operations behind explicit approval.

Official: https://docs.github.com/ · https://cli.github.com/manual/
