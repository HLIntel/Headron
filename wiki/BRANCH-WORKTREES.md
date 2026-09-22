# Branches and Worktrees

GitHub branches isolate development work, while worktrees let multiple branches be checked out simultaneously. See the [GitHub branches documentation](https://docs.github.com/en/pull-requests/reference/branches).

## Recommended structure

```text
main
 |
 +-- feat/<topic>
 +-- fix/<topic>
 +-- research/<topic>
 +-- security/<topic>
 +-- lang/<language>/<topic>
```

Every active branch should have one clear purpose.

### Language branches

Do **not** create permanent branches such as:

```text
python
rust
go
typescript
cpp
```

Use temporary language lanes instead:

```text
lang/python/agent-harness
lang/rust/boundary-tests
lang/go/worker-pool
lang/typescript/vscode-router
```

This gives an agent language-local context without turning the repository into many incompatible versions.

## Worktree rule

Use one mutable writer per worktree.

```text
main checkout              -> stable inspection
worktree A                 -> lang/python/agent-harness
worktree B                 -> lang/rust/boundary-tests
worktree C                 -> feat/mcp-routing
```

A worktree isolates the checkout and mutable working tree, but not external dependency caches, credentials, running services, or build outputs outside the worktree. Those boundaries must still be explicit.

## Choose the branch by change scope

| Change | Branch |
|---|---|
| one language guide/tooling | `lang/<language>/<topic>` |
| one feature across shared code | `feat/<topic>` |
| defect | `fix/<topic>` |
| experiment/evaluation | `research/<topic>` |
| security | `security/<topic>` |
| MODEL/atlas/CI/version contract | `feat/<topic>` or `fix/<topic>` |
| multiple language boundary | repository-wide topic branch |

## Agent handoff

Every worktree/branch should carry:
- task objective
- allowed paths
- forbidden paths
- native commands
- verification checks
- expected artifact/diff
- budget/deadline
- rollback or snapshot point for high-impact work

See [systems/AGENT-HARNESS.md](../systems/AGENT-HARNESS.md).

## Merge rule

All meaningful language lanes merge back through the canonical `main` contract. A language lane must not redefine repository-wide model, routing, MCP, CI, security, or version policy independently.

## Safe cleanup

```bash
git worktree list --porcelain
git worktree remove ../Code-Development-wt/lang-python-agent
git worktree prune
```
