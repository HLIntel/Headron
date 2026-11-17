# Nim

**Status:** mature-specialized

## Purpose
Native developer tools, small services/CLIs, automation with compiled performance, and cross-platform native binaries.

## Stack
Nim compiler -> Nimble -> ORC/ARC memory management -> C/C++/Objective-C/JS backends as appropriate -> tests/docs.

## Memory
The official Nim memory docs recommend ORC for newly written code; confirm against them before a task relies on it, as this pack's `provenance` requires. ARC/ORC use deterministic-style reference-counting techniques; async designs should account for the documented cycle behavior of ARC.

## Compile-time power
Nim supports substantial compile-time execution and macros. Keep compile-time logic readable and bounded.

## Interop
Use C/C++ FFI deliberately. Treat native library linkage as a security and supply-chain boundary.

## Common mistakes
- excessive macros
- hidden compile-time complexity
- unsafe FFI assumptions
- memory-mode mismatch
- global state

## Streamline
Use the standard library/Nimble before adding a dependency. Keep backend choice explicit.

## AI directive
The agent must state memory-management mode and native dependencies when changing low-level code.

## Verify
`nim check`, test suite, release compilation, and backend-specific integration tests.

Official: https://nim-lang.org/docs/

## Operating card

**Route:** compiled automation, CLIs, native services, rapid systems tooling.

**Fast path:** `nimble`/project config → formatter/linter → tests → native profiling.

**Native authority:** Nim compiler, package manager, generated C/C++/JS boundary where used.

**Pair with:** C/Rust for mature native boundaries; Python for ecosystem-heavy data/AI; SQL for persistence.

**Boundary:** generated-code assumptions are tested; macros/templates stay local and documented.

**Avoid:** macro-heavy architecture, implicit ownership assumptions, unchecked FFI, dependency sprawl.

**Reliability:** explicit buffers, timeouts, bounded workers/queues, deterministic cleanup.

**Verify:** compile with warnings → tests → static analysis → target build → benchmark.

**AI learning loop:** inspect generated/native behavior when using macros; keep abstractions smaller than the problem.

**Research:** https://nim-lang.org/docs/ · https://nim-lang.org/documentation.html
