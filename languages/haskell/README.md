# Haskell

**Status:** mature-specialized

## Purpose
Compilers, formal-ish domain modeling, research, finance, high-level correctness, concurrent software, and functional architecture.

## Stack
GHC -> Cabal or Stack -> HLS -> formatter/linter -> Hspec/QuickCheck-style testing -> profiling/eventlog.

## Core strengths
Purity, strong static types, algebraic data types, type classes, and compositional abstractions make invariants visible in APIs.

## Concurrency
Study STM, async, bounded concurrency, resource pools, and cancellation. Laziness does not remove the need for resource bounds.

## Performance
Use GHC's time/space profiling, eventlog, strictness analysis, and benchmarks. Watch thunk retention and accidental laziness in resource-heavy paths.

## Common mistakes
- space leaks
- unnecessary abstraction
- orphan instances
- partial functions
- unchecked exception-like IO failures

## Streamline
Use algebraic data types and total pattern matching to encode states rather than defensive runtime branching everywhere.

## AI directive
Prefer types that make invalid states unrepresentable. Generate explicit total matches and tests around invariants.

## Verify
GHC compile/warnings, test suite, QuickCheck properties, profiling for hot/resource-heavy paths.

Official: https://www.haskell.org/ and https://downloads.haskell.org/ghc/latest/docs/

## Operating card

**Route:** correctness-heavy services, compilers, research, finance, functional architecture.

**Fast path:** Cabal/Stack → formatter → GHC warnings → Hspec or tasty + QuickCheck → profiling.

**Native authority:** GHC, package environment, type system, runtime profiler.

**Pair with:** Rust/C for narrow native work; Python/TypeScript for product edges; SQL for data boundaries.

**Boundary:** encode invariants in types where they reduce runtime checks; keep FFI isolated.

**Avoid:** accidental laziness in resource-sensitive paths, giant typeclass indirection, opaque effects.

**Reliability:** explicit resource scopes, bounded queues, timeout semantics, deterministic test generators.

**Verify:** format → compile with warnings → unit/property tests → profiling → integration tests.

**AI learning loop:** read types and effect boundaries before implementation; let compiler feedback drive the design.

**Research:** https://www.haskell.org/documentation/ · https://ghc.gitlab.haskell.org/ghc/doc/users_guide/
