# Lean 4

Purpose: formal verification, theorem proving, precise specifications, proof-producing programs, and validation of mathematical or algorithmic claims.

## When to choose Lean
- A correctness property is more important than ordinary test evidence alone.
- You need machine-checked invariants or formal specifications.
- You want to connect program definitions with proofs about their behavior.

## Build/project system
Lake is Lean 4's build system and package manager.

Typical files:
```text
lakefile.toml or lakefile.lean
lean-toolchain
Main.lean
```

Official: https://github.com/leanprover/lean4/tree/master/src/lake and https://lean-lang.org/

## AI use
Lean is especially useful as an independent verifier for claims that an AI model proposes but should not be trusted to prove merely by explanation.

Useful pattern:
```text
AI proposes theorem/specification
  ↓
Lean checker
  ↓
proof accepted or rejected
```

## Engineering caution
Formal verification verifies the formalized statement. Spend time making sure the formal specification matches the real system.

## Worktree
```bash
git worktree add -b feat/lean-task ../Code-Development-wt/lean-task main
```