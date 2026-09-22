# Haskell Operating Card

**Route:** correctness-heavy services, compilers, research, finance, functional architecture.

**Fast path:** Cabal/Stack → formatter → GHC warnings → Hspec/HUnit/QuickCheck → profiling.

**Native authority:** GHC, package environment, type system, runtime profiler.

**Pair with:** Rust/C for narrow native work; Python/TypeScript for product edges; SQL for data boundaries.

**Boundary:** encode invariants in types where they reduce runtime checks; keep FFI isolated.

**Avoid:** accidental laziness in resource-sensitive paths, giant typeclass indirection, opaque effects.

**Reliability:** explicit resource scopes, bounded queues, timeout semantics, deterministic test generators.

**Verify:** format → compile with warnings → unit/property tests → profiling → integration tests.

**AI learning loop:** read types and effect boundaries before implementation; let compiler feedback drive the design.

**Research:** https://www.haskell.org/documentation/ · https://ghc.gitlab.haskell.org/ghc/doc/users_guide/
