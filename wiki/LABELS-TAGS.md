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

`kind/*`, `lang/*` (one per language route), `area/*`, `runtime/*`, `mcp/*`, `risk/*` and
`status/*`. Every label in them is declared in
[config/github-labels.json](../config/github-labels.json); this page states no list, because a
second roster is the one thing that can disagree with the catalog.

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

Topics are repository-level discovery metadata, not substitutes for issue labels.

## Git tags

The pattern, not examples that age:

```text
v<major>.<minor>.<patch>
```

What earns each bump, and the one line per version that is the only changelog, live in
[docs/VERSIONING.md](../docs/VERSIONING.md). `python scripts/ghaudit.py` fails on a tag with no
release, because a tag with no release is an artifact nobody can find.

Do not create language tags such as `python` or `rust` for development routing. Language identity belongs in paths, Atlas routes, and GitHub labels.

## What enforces this now

The catalog `config/github-labels.json` is **enforced, not planned**, and checked BOTH WAYS by
`atlas.py check`: a route whose label is missing from the catalog fails, a `lang/*` label that no
route resolves to fails as debris, and a label outside every declared namespace prefix fails too.
`atlas_test.py` plants the first defect to prove the check still bites. Creating the label
definitions in GitHub remains an administrative step — the catalog is the declaration, and a label
that exists here and not there is a finding for whoever syncs them.

That two-way check is the pattern this repository applies to every roster — a one-directional
check proves a route has a label and never that a label has a route, and the second direction is
what catches something added through a UI or left behind by a deletion.
