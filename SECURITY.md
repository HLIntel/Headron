# Security Policy

**Repository contract: v1.2.1** · platform controls: [docs/GITHUB-FINALIZATION.md](docs/GITHUB-FINALIZATION.md)

## The property this repository is built on

This is the only public repository in its organization, and it is public so that any model or agent
can fetch a raw URL without a token. That single decision sets the security rule, and the rule has
no exceptions:

> **No secret, credential, token, private-project path or internal hostname enters this repository.**
> Not in a file, not in an example, not in a commit message, not in history.

Operational systems, their state and their keys live in private repositories. What lives here is the
method. A reader should be able to hand this entire tree to an unknown agent without reviewing it
first — that is the test, and it is the reason the rule is absolute rather than risk-weighted.

## Reporting a vulnerability

Do not disclose an unpatched vulnerability in a public issue, discussion, pull request, or commit.

**Measured 2026-09-24** (instrument:
`gh api repos/ApianSoftware/Code-Development/private-vulnerability-reporting -q .enabled` → `true`):
**private vulnerability reporting is ENABLED.**

Use **Security → Report a vulnerability** on this repository. Include enough reproduction detail to
validate the issue without publishing secret material. You will get a private advisory thread; the
report stays unlisted until a fix ships.

*This section previously recorded the feature as DISABLED, with an interim public-issue protocol.
It was disabled; it was enabled on 2026-09-24 and this text was re-measured in the same change. A
fix to a control must expire the documentation that control's absence produced — otherwise the
repaired system keeps publishing the verdict it wrote while it was broken.*

## Platform controls — measured, not assumed

| control | state | instrument |
|---|---|---|
| secret scanning | **enabled** | `gh api repos/… -q .security_and_analysis` |
| push protection | **enabled** | same |
| Dependabot security updates | **enabled** | same |
| secret scanning — non-provider patterns | **disabled** | same |
| secret scanning — validity checks | **disabled** | same |
| private vulnerability reporting | **enabled** | `gh api …/private-vulnerability-reporting` |
| branch ruleset `main-protection` | **active**, but requires no status check | `gh api …/rulesets` |

**The row that matters most is the last one.** `main-protection` blocks deletion, force-push and
non-linear history, and requires **no pull request and no passing check**. Atlas CI, Dependency
Review and CodeQL all run and none of them gate a merge. A control that is configured but not
required is an unshipped arm: it reads as covered and stops nothing. See
[docs/GITHUB-FINALIZATION.md](docs/GITHUB-FINALIZATION.md).

Two rows are declared gaps rather than settings nobody looked at: non-provider patterns and
validity checks are off. A declared blind spot is a promise to come back, not an exemption.

## Scope

Security-sensitive areas:

- AI agent/tool execution and permissions
- MCP and connector boundaries
- secrets and authentication
- GitHub Actions and workflow permissions
- external endpoints and webhooks
- database/Redis access
- native/FFI/ABI boundaries
- dependency and supply-chain changes
- generated or downloaded executable artifacts

## Repository expectations

Security fixes use a short-lived `security/<topic>` branch or isolated worktree, add regression
coverage when practical, and preserve rollback and auditability for high-impact changes.

**Never commit a real credential.** If one may have reached Git history or any external system,
**rotate it at the provider** — removing it from the working tree does not revoke it, and a local
cache miss is not revocation. Verify the rotation at the provider, never by a tool's local state.
