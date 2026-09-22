# Language Lanes

Each language has its own guide and machine route. That does not require a permanent Git branch.

## Policy

```text
language identity = path + Atlas route + label
development isolation = short-lived branch + optional worktree
repository contract = main
```

## Suggested lane names

| Language | Label | Branch namespace |
|---|---|---|
| Python | `lang/python` | `lang/python/*` |
| Rust | `lang/rust` | `lang/rust/*` |
| Go | `lang/go` | `lang/go/*` |
| TypeScript | `lang/typescript` | `lang/typescript/*` |
| C | `lang/c` | `lang/c/*` |
| C++ | `lang/cpp` | `lang/cpp/*` |
| Zig | `lang/zig` | `lang/zig/*` |
| Mojo | `lang/mojo` | `lang/mojo/*` |
| Julia | `lang/julia` | `lang/julia/*` |
| Elixir | `lang/elixir` | `lang/elixir/*` |
| Gleam | `lang/gleam` | `lang/gleam/*` |
| Nim | `lang/nim` | `lang/nim/*` |
| V | `lang/v` | `lang/v/*` |
| Odin | `lang/odin` | `lang/odin/*` |
| Hare | `lang/hare` | `lang/hare/*` |
| Futhark | `lang/futhark` | `lang/futhark/*` |
| Haskell | `lang/haskell` | `lang/haskell/*` |
| F# | `lang/fsharp` | `lang/fsharp/*` |
| Chapel | `lang/chapel` | `lang/chapel/*` |
| BQN | `lang/bqn` | `lang/bqn/*` |
| Uiua | `lang/uiua` | `lang/uiua/*` |
| Lean 4 | `lang/lean4` | `lang/lean4/*` |
| Carbon | `lang/carbon` | `lang/carbon/*` |
| Roc | `lang/roc` | `lang/roc/*` |
| Q# | `lang/qsharp` | `lang/qsharp/*` |
| CUDA | `lang/cuda` | `lang/cuda/*` |
| SQL | `lang/sql` | `lang/sql/*` |
| Bash | `lang/bash` | `lang/bash/*` |
| WebAssembly | `lang/webassembly` | `lang/webassembly/*` |

For Qiskit and Silq, use the `area/quantum` label and task branch namespace unless the change is isolated to their dedicated guide.

## When a lane should graduate to a normal topic branch

Move from `lang/*` to `feat/*`, `fix/*`, or `research/*` when:
- a change crosses a language boundary
- Atlas/control files change
- shared MCP/runtime behavior changes
- CI/security/versioning changes
- the branch starts accumulating unrelated work

A language label can remain on the PR after the branch changes; branch names describe workflow isolation, while labels describe the change.
