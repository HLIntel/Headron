# Git Worktrees and Branch Lanes

Git worktrees allow one repository to have multiple checked-out working directories at once. They are useful for keeping a stable branch available while an AI agent works independently on a feature, experiment, benchmark, migration, or security fix.

Official reference: https://git-scm.com/docs/git-worktree

## Branch model

`main` is the canonical contract baseline.

Use short-lived topic branches:
- `feat/<topic>` for implementation
- `fix/<topic>` for defects
- `research/<topic>` for experiments/research
- `security/<topic>` for security work
- `lang/<language>/<topic>` for changes primarily isolated to one language

A `lang/*` branch is a temporary development lane, not a permanent branch for that language.

### Why not one permanent branch per language?

This repository is one atlas/control system, not a set of independently released language projects. Permanent `python`, `rust`, `go`, etc. branches would create:
- duplicated contract surfaces
- stale routing and index edges
- inconsistent MCP/runtime policy
- harder cross-language changes
- merge pressure back into `main`
- parallel versions of the same repository rules

The directory structure already provides language isolation. Branches should isolate **work**, not permanently divide the repository by language.

## When to use a language lane

Use `lang/<language>/<topic>` when:
- the change is dominated by one language guide or language-specific implementation
- verification can run without unrelated language branches
- parallel work on another language is expected
- an AI agent benefits from a narrow context surface

Use a repository-wide topic branch instead when the change touches:
- `MODEL.md`, `atlas.yaml`, versioning, or CI
- multiple language boundaries
- MCP profiles/shared integrations
- repository-wide security/reliability rules
- shared indexes or generated artifacts

## Worktree layout

```text
~/src/Code-Development/                         main
~/src/Code-Development-wt/lang-python-agent/  lang/python/agent
~/src/Code-Development-wt/lang-rust-core/     lang/rust/core
~/src/Code-Development-wt/feat-routing/       feat/routing
```

Create:

```bash
git worktree add -b lang/python/agent ../Code-Development-wt/lang-python-agent main
git worktree add -b lang/rust/core ../Code-Development-wt/lang-rust-core main
git worktree add -b feat/routing ../Code-Development-wt/feat-routing main
```

Inspect:

```bash
git worktree list --porcelain
```

Remove:

```bash
git worktree remove ../Code-Development-wt/lang-python-agent
git worktree prune
```

Do not use a worktree as a substitute for dependency isolation. Language environments still need their own manifests, lockfiles, virtual environments, build directories, package stores, and credentials boundaries.

## AI-agent lifecycle

```text
main
  -> topic/language branch
  -> dedicated worktree
  -> scout/plan
  -> edit
  -> native verification
  -> independent verification
  -> diff review
  -> PR
  -> merge to main
  -> remove worktree
```

For concurrent agents, each writer gets its own worktree. Read-only agents may share a checkout only when they have no mutable build/state side effects.

## Protected baseline

When repository protection is enabled, require the authoritative CI check before merge and keep `main` free of agent work-in-progress changes. GitHub supports branch protection rules for status checks, reviews, signed commits, linear history, merge queues, and related controls. See the GitHub branch documentation linked from the wiki.
