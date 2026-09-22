# Security Policy

## Reporting

Do not disclose an unpatched security vulnerability in a public issue, discussion, pull request, or commit.

Use GitHub's repository **Security** area and private vulnerability reporting/security advisory flow when it is available for the repository. Include enough reproduction detail to validate the issue without publishing secret material.

## Scope

Security-sensitive areas include:
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

Security fixes should normally use a short-lived `security/<topic>` branch or isolated worktree, add regression coverage when practical, and preserve rollback/auditability for high-impact changes.

Never commit real credentials. Rotate exposed credentials even after removing them from the working tree if they may have reached Git history or an external system.

See [docs/GITHUB-FINALIZATION.md](docs/GITHUB-FINALIZATION.md) for platform controls.
