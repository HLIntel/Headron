# Git Worktrees

Git worktrees allow one repository to have multiple checked-out working directories at once. They are useful for keeping a stable branch available while an AI agent works independently on a feature, experiment, benchmark, migration, or security fix.

Official reference: https://git-scm.com/docs/git-worktree

## Recommended layout

```text
~/src/Code-Development/                 main/stable
~/src/Code-Development-wt/python-x/     Python feature
~/src/Code-Development-wt/rust-x/       Rust feature
~/src/Code-Development-wt/go-x/         Go feature
~/src/Code-Development-wt/ts-x/         TypeScript feature
```

## Create

```bash
git worktree add -b feat/python-bounded-cache ../Code-Development-wt/python-bounded-cache main
git worktree add -b feat/rust-limits ../Code-Development-wt/rust-limits main
git worktree add -b feat/go-worker-pool ../Code-Development-wt/go-worker-pool main
git worktree add -b feat/ts-tool-runtime ../Code-Development-wt/ts-tool-runtime main
```

## Inspect

```bash
git worktree list --porcelain
```

## Remove

```bash
git worktree remove ../Code-Development-wt/python-bounded-cache
git worktree prune
```

Do not manually delete a worktree and assume Git has fully cleaned its administrative state; use `git worktree remove` and `prune` when appropriate.

## AI-agent pattern

Use a dedicated worktree for an agent task when:
- the task spans multiple files
- experiments may destabilize the main checkout
- multiple agents or processes may work simultaneously
- a benchmark needs isolated dependencies/build outputs
- a migration needs a reversible branch

Recommended lifecycle:

```text
main/stable
  ↓
dedicated worktree
  ↓
agent edits
  ↓
verification
  ↓
diff review
  ↓
PR/merge
  ↓
remove worktree
```

## Language-specific convention

| Language | Suggested branch/worktree role |
|---|---|
| Python | `python-*` for env, package, async, AI experiments |
| Rust | `rust-*` for crates, unsafe, benchmarks, systems work |
| Go | `go-*` for services, modules, profiling, concurrency |
| TypeScript | `ts-*` for APIs, tooling, agent interfaces |
| C++ | `cpp-*` for native/HPC/ABI experiments |
| Zig | `zig-*` for low-level tooling and C interop |
| Mojo | `mojo-*` for accelerator/HPC experiments |
| Julia | `julia-*` for numerical/research systems |
| Elixir | `elixir-*` for OTP/distributed prototypes |
| Lean 4 | `lean-*` for proofs/formalization |

## Don't use worktrees as a substitute for dependency isolation

A worktree shares repository history and most object data. Language environments still need their own isolation strategy: Python virtual environments/lockfiles, Rust target/build strategy, Go module discipline, Node package manager state, and equivalent language-specific tooling.