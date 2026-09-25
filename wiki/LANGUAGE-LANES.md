# Language Lanes

Each language has its own guide and machine route. That does not require a permanent Git branch.

## Policy

```text
language identity = path + Atlas route + label
development isolation = short-lived branch + optional worktree
repository contract = main
```

## Suggested lane names

<!-- BEGIN generated: language-lanes (python scripts/atlas.py index --write) -->
Derived from `atlas.yaml/artifact_routes` + `branch_policy.language_lane_pattern`.

| Route | Label | Branch namespace |
|---|---|---|
| `bash` | `lang/bash` | `lang/bash/*` |
| `bqn` | `lang/bqn` | `lang/bqn/*` |
| `c` | `lang/c` | `lang/c/*` |
| `carbon` | `lang/carbon` | `lang/carbon/*` |
| `chapel` | `lang/chapel` | `lang/chapel/*` |
| `cpp` | `lang/cpp` | `lang/cpp/*` |
| `cuda` | `lang/cuda` | `lang/cuda/*` |
| `elixir` | `lang/elixir` | `lang/elixir/*` |
| `forth` | `lang/forth` | `lang/forth/*` |
| `fsharp` | `lang/fsharp` | `lang/fsharp/*` |
| `futhark` | `lang/futhark` | `lang/futhark/*` |
| `gleam` | `lang/gleam` | `lang/gleam/*` |
| `go` | `lang/go` | `lang/go/*` |
| `hare` | `lang/hare` | `lang/hare/*` |
| `haskell` | `lang/haskell` | `lang/haskell/*` |
| `julia` | `lang/julia` | `lang/julia/*` |
| `lean4` | `lang/lean4` | `lang/lean4/*` |
| `mojo` | `lang/mojo` | `lang/mojo/*` |
| `nim` | `lang/nim` | `lang/nim/*` |
| `ocaml` | `lang/ocaml` | `lang/ocaml/*` |
| `odin` | `lang/odin` | `lang/odin/*` |
| `python` | `lang/python` | `lang/python/*` |
| `quantum/qsharp` | `lang/qsharp` | `lang/quantum/qsharp/*` |
| `quantum/silq` | `lang/silq` | `lang/quantum/silq/*` |
| `r` | `lang/r` | `lang/r/*` |
| `roc` | `lang/roc` | `lang/roc/*` |
| `rust` | `lang/rust` | `lang/rust/*` |
| `scala` | `lang/scala` | `lang/scala/*` |
| `sql` | `lang/sql` | `lang/sql/*` |
| `swift` | `lang/swift` | `lang/swift/*` |
| `typescript` | `lang/typescript` | `lang/typescript/*` |
| `uiua` | `lang/uiua` | `lang/uiua/*` |
| `v` | `lang/v` | `lang/v/*` |
| `webassembly` | `lang/webassembly` | `lang/webassembly/*` |
| `zig` | `lang/zig` | `lang/zig/*` |
<!-- END generated: language-lanes -->

For Qiskit and Silq, use the `area/quantum` label and task branch namespace unless the change is isolated to their dedicated guide.

## When a lane should graduate to a normal topic branch

Move from `lang/*` to `feat/*`, `fix/*`, or `research/*` when:
- a change crosses a language boundary
- Atlas/control files change
- shared MCP/runtime behavior changes
- CI/security/versioning changes
- the branch starts accumulating unrelated work

A language label can remain on the PR after the branch changes; branch names describe workflow isolation, while labels describe the change.

## What enforces this now

`branchstate.py` measures what a lane actually holds — unpushed commits and their age — against
`branch_policy/unpushed_bound`. The bound is in COMMITS AND HOURS rather than in branches,
because when it was measured the tree had three branches and two worktrees while eight commits
sat unpushed for three hours: a container count is not the quantity.

It also reports the four LANDING STATES separately — committed, pushed, merged, published —
because three of them look identical from a terminal and only the last is what anybody outside
observes. It never pushes: that is an outward-facing act, not a tidy-up.
