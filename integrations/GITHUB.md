# GitHub as a control plane

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

## GitHub App — Thea as an actor on every pull request

The companion `atlas.yaml/companions/github_app` is ONE module, `scripts/githubapp.py`, around one
verdict function. `python scripts/githubapp.py --base <sha> [--head HEAD] [--json]` is that function run
locally; the service runs the same `build_report` over a checkout of each head, so a check run on GitHub
and a local run over the same SHAs cannot disagree. Its webhook, auth and conclusion mapping were
harvested from the App's first, out-of-repository webhook and keep its wire behaviour.

| entry point | job |
|---|---|
| `githubapp.py serve <port>` | `POST /github/webhook` (signature first, enqueue, answer within GitHub's 10 s), `GET /health`, and a worker thread that drains the queue |
| `githubapp.py drain` | run every queued job once and exit — for a host that prefers a timer to the thread |
| `githubapp.py --base <sha>` | the verdict alone, no GitHub |

### Sequence

1. **Delivery.** A `pull_request` `opened`/`synchronize`/`reopened`, a `check_suite` `requested`/
   `rerequested`, or a `check_run` `rerequested` on `Thea verify` arrives. An unsigned, wrongly signed,
   or secret-less delivery is `401` before the body is parsed (`X-Hub-Signature-256`, HMAC-SHA256,
   `hmac.compare_digest`).
2. **Queue.** The job `{repo, clone_url, head_sha, base_sha, pr, installation_id, owner}` goes to
   `pending/`, keyed by (repo, head SHA): the pull request and its check suite for the same push, or a
   redelivery, verify once (`200`, not `202`). A rerequest re-queues a finished head. `installation` and
   `installation_repositories` append to `installations.jsonl`.
3. **Claim.** The worker moves the job to `running/` by atomic rename; a worker that dies leaves it to
   lease recovery, and three failures end it NOT RUN.
4. **Token.** App JWT (RS256 by `openssl`, `iat` -60 s, `exp` +540 s, `iss` = App id) →
   `POST /app/installations/{id}/access_tokens`, for the installation that sent the event.
5. **Check run starts.** `POST /repos/{repo}/check-runs` `{name: "Thea verify", head_sha, status: in_progress}`.
6. **Allowlist.** Verify runs the graded repository's own gates, so a head is code this host executes:
   only when the repository's owner AND the head's owner are in `THEA_APP_RUN_OWNERS`. A fork's PR or
   an unlisted installation gets a neutral NOT RUN that says why — never a silent skip, never green.
7. **Verify.** Full-history fetch of head and base (a shallow one fails the contract gate; the token
   reaches git as an http header through env — never argv, never `.git/config`), detach at head,
   `build_report(base, head, tree)`: `scripts/verify.py --json --changed` with `THEA_BASE`, the CLI's own
   path. No base (a push with no PR) is a full verify. A head with no `atlas.yaml` is NOT RUN.
8. **Check run completes.** A fresh token (a long suite outlives the first one's hour). Each FAIL /
   NOT RUN gate on a changed file becomes an annotation, sent in batches of 50 (GitHub's cap; later
   PATCHes append); the last PATCH carries `status: completed` and `conclusion`: `success` only when
   verify exited 0 AND measured a PASS; `failure` on any FAIL or a non-0/2 exit; otherwise `neutral`.
9. **Timeline.** A head not cleared to merge appends a `refusal` row to `timeline.jsonl`: what (repo,
   PR, SHAs, event), why (each blocked gate, path, verdict, failure text), and which guard covers it
   (the gate id plus any `agent_failure_modes` ledger id whose signature matches). A later
   `pull_request` `closed` with `merged: true` on a refused head appends an `override` row naming who
   merged it.

Proof, offline: `githubapp_test.py` (run by the planted suite) drives a recorded `pull_request` fixture
through signature → queue → a real `git` fetch → `build_report` → a fake GitHub transport → timeline,
then the merged fixture to an override row; the signature check and the conclusion mapping are each
planted wrong and must be caught. Only the gate run inside verify is canned there — verify's own suite proves it.

### Configuration (environment only; nothing secret is tracked)

`THEA_GITHUB_APP_ID`, `THEA_GITHUB_APP_PRIVATE_KEY_B64` (the PEM, base64), `THEA_GITHUB_APP_WEBHOOK_SECRET`
— `serve` refuses to start without all three — and `THEA_APP_RUN_OWNERS` (comma list; empty runs
nothing). Optional: `THEA_GITHUB_APP_STATE` (queue + timeline directory, default
`$XDG_STATE_HOME/thea-github-app`), `THEA_GITHUB_API` for Enterprise Server. The service binds
`127.0.0.1` on the port the host assigns; TLS and the public URL belong to the proxy in front of it.
App permissions: Checks read & write, Contents read, Pull requests read, Metadata read; events:
Pull request, Check suite, Check run, Installation.

### Not live yet

- **Required check.** Branch protection / a ruleset requiring `Thea verify`, declared in
  [config/github-controls.json](../config/github-controls.json) and compared by `ghaudit.py` —
  until that is set, a refusal is advice, not a block.
- **THEA REPORT comment.** The body is built; posting it as a PR comment is not wired.
- **Next, out of scope here:** org/team policy packs, OAuth roles, and the dashboard over `timeline.jsonl`.

The App's webhook is configured on the App, not on a repository, so the "webhooks declared as zero"
control below still holds for every repository.

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
