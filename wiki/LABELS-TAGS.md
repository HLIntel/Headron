# Labels and Tags

Use metadata to make the repository machine-routable without turning metadata into another uncontrolled taxonomy.

## Three layers

| Mechanism | Purpose | Scope |
|---|---|---|
| GitHub issue/PR labels | route and triage work | task |
| GitHub repository topics | discovery/search | repository |
| Git tags | immutable contract/release points | repository history |

Labels are orthogonal filters. A single issue should normally have one `kind/*`, one or more relevant `lang/*` or `area/*`, and status/risk labels only when useful.

## Label namespaces

### kind/*
`kind/bug`, `kind/feature`, `kind/refactor`, `kind/docs`, `kind/research`, `kind/security`, `kind/performance`, `kind/architecture`, `kind/tooling`

### lang/*
One label per language route, for example:
`lang/python`, `lang/rust`, `lang/go`, `lang/typescript`, `lang/cpp`, `lang/cuda`, `lang/sql`.

The full machine catalog is in [config/github-labels.json](../config/github-labels.json).

### area/*
`area/model`, `area/atlas`, `area/mcp`, `area/ide`, `area/agent`, `area/polyglot`, `area/ci`, `area/docs`, `area/wiki`, `area/research`, `area/quantum`

### runtime/*
`runtime/vscode`, `runtime/opencode`, `runtime/codex`, `runtime/claude`, `runtime/cursor`, `runtime/hermes`, `runtime/github-actions`

### mcp/*
`mcp/github`, `mcp/serena`, `mcp/context7`, `mcp/playwright`, `mcp/semgrep`, `mcp/dbhub`

### risk/*
`risk/breaking`, `risk/high-impact`, `risk/dependency`, `risk/security`

### status/*
`status/needs-triage`, `status/blocked`, `status/ready`, `status/experimental`

## Routing examples

A Rust debugging PR can be:

`kind/bug + lang/rust + area/agent + status/ready`

A SQL agent integration can be:

`kind/feature + lang/sql + area/mcp + mcp/dbhub + risk/high-impact`

A repository routing change can be:

`kind/refactor + area/atlas + area/ci`

Avoid labels that merely restate the title. Prefer labels that enable filtering, routing, automation, or ownership.

## Repository topics

Repository topics are declared in [config/github-controls.json](../config/github-controls.json)
and compared to the live repository by `python scripts/ghaudit.py`. This page states no list:
a second roster of topics is the one thing that can disagree with the declaration.
`programming-languages`, `polyglot`, `ai-agents`, `coding-agents`, `mcp`, `vscode`, `github`, `developer-tools`, `code-navigation`, `software-engineering`.

Topics are repository-level discovery metadata, not substitutes for issue labels.

## Git tags

Use semantic contract/release tags such as:

```text
v0.7.3
v0.8.0
v1.0.0
```

Do not create language tags such as `python` or `rust` for development routing. Language identity belongs in paths, Atlas routes, and GitHub labels.

## Machine source

The label catalog is [config/github-labels.json](../config/github-labels.json), and it is
**enforced, not planned**: `atlas.py check` fails when a route resolves to a label the catalog
does not contain, and `atlas_test.py` plants that defect to prove the check still bites. Creating
the label definitions in GitHub remains an administrative step — the catalog is the declaration,
and a label that exists here and not there is a finding for whoever syncs them.
