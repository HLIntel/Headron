# Repository Versioning

Current version: 2.0.0

Version tracks the behavioral and tooling contract — **not the content**. Adding a paragraph to a
guide is not a version change; changing what the harness enforces, what a route resolves to, or
what a gate requires always is.

## The same-commit rule

A contract, route, MCP role, CI/security policy, verification requirement, canonical structure, or
repository operating-policy change updates **MODEL.md, VERSION, README.md, ABOUT.md, the affected
docs/patterns/adapters, and atlas.yaml together, in one commit.**

This is enforced, not requested. `atlas.py check` reads `VERSION` and fails when the string is
absent from `MODEL.md`, `README.md`, `ABOUT.md` or this file, or when `atlas.yaml`'s `version`
disagrees. **Six places, one declaration** — the check exists because two version strings that
agree only because someone typed the same digits disagree the first time one is edited.

## What earns which bump

| bump | earns it |
|---|---|
| **major** | a route, manifest or contract shape that existing consumers must change to satisfy. Worked case: 2.0.0 renamed `provenance.authored` to `provenance.since` and bumped the manifest's own `schema` to 2 — a reader pinned to format 1 is told, rather than left to find a field missing. |
| **minor** | a new enforced check, a new instrument, a new invariant, a new route, or a gate that now blocks something it did not |
| **patch** | a correction inside the existing contract — a repaired check, a fixed parser, a stale claim re-measured |

**A new instrument is a minor bump even if no rule changed**, because the next reader's options
changed. Skipping the bump is how a tool ends up in the tree that nothing announces.

## Release procedure

The changelog line and the release are **two different artifacts, and for a long time only the
first existed** — 17 versions were named here and never tagged, so no reader could fetch the tree
any of them described. A version with no tag is a claim with no artifact.

1. `python scripts/atlas.py check` → must exit 0.
2. `python scripts/atlas_test.py` → must report all cases pass.
3. `ruff check .` → must exit 0.
4. Bump the six places above in one commit.
5. Add exactly one line here: `<version> <what changed, in one sentence>`.
6. `git tag -a v<version> -m "<the same sentence>"` on that commit.
7. Push the tag, then cut the GitHub release from it.

**Entries are kept in ascending semver order.** They were not: the list ran
`1.0.1 → 1.1.0 → 1.0.2 → 1.0.0`, which made three versions unreadable in sequence and is the
reason this section exists.

## One line per version, and it is the only changelog

No `CHANGELOG.md`, no release-notes generator, no conventional-commit tooling. A second changelog
is a second declaration: one copy goes stale and the next reader cannot tell which is live. The
commit message carries the detail; this file carries the sentence.

0.7.0 language-by-language MCP and VS Code capability routing
0.7.1 current-source licensing correction for Serena
0.7.2 Atlas CI runtime simplification
0.7.3 complete language targets and documentation reachability
0.8.0 repository wiki, code-specific routing, taxonomy, and branch/worktree policy
0.9.0 production operations matrix, assurance stack, GitHub security/AI finalization, and tool orchestration
0.9.1 validator repair and repository ownership/security metadata
0.9.2 Markdown-link parser self-test and escaping correction
0.9.3 link diagnostics and CI repository-surface checks
0.9.4 symlink-aware Markdown link validation
0.9.5 model/runtime routing, progressive context policy, language operating cards, and GitHub backend control plane
0.9.6 machine-routed language tool manifests, explicit task verification gates, severity/baseline policy, and dynamic Atlas planning
0.9.7 YAML-parsed harness, single-sourced task profiles, directory routing, manifest schema validation, generated language index, label check, CodeQL as default setup
1.0.0 first stable control contract: a tool manifest for every route, every atlas.yaml restatement generated and drift-checked, the learn command, provenance on manifests, every resolved count printed
1.0.1 mutation tests for the harness, route edge cases, working-directory-independent entry point, devcontainer
1.0.2 every hard invariant is enforced by a check or declared with its reason; the contract fails on an unowned invariant
1.1.0 all 25 hard invariants enforced by real checks over this repository's own artifacts (none declared), one planted defect per check, worktree lifecycle rules
1.2.0 contract instruments named with their blind spots, packprobe toolchain coverage, pyproject declaring the tools already in use, five classical laws harvested, GitHub audit re-measured and dated
1.2.1 private vulnerability reporting enabled and SECURITY.md re-measured against it; first tagged release verified on the remote
1.3.0 tool manifests validated against a JSON Schema that declares each entry's kind; the harness split into router, generators and contract; machine-readable route/plan/probe output and a generated llms.txt; every instrument and its closer declared in atlas.yaml; ghaudit compares the live GitHub controls to config/github-controls.json; main-protection requires the Contract and Dependency Review checks; MIT licence
2.0.0 manifest format 2: provenance carries the contract version it was authored at instead of a calendar date, and the contract refuses a date anywhere in a tracked file — this is a MAJOR bump because an existing tools.yaml reader must change; adds `atlas.py doctor`, the banner is content-addressed, and the research file is reviewed rather than harvested
