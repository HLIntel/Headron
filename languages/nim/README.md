# Nim

**Status:** mature-specialized

## Purpose
Native tools, compact services, automation, and cross-platform binaries with a productive high-level syntax.

## Stack
Nim compiler -> Nimble -> ORC/ARC memory management -> C/C++/JS backends -> tests/docs.

## Key leverage
Compile-time execution and macros can remove runtime work, but also move complexity into the compiler phase.

## Memory
The official docs currently recommend ORC for new code. ARC/ORC trade cycle behavior and code-size/runtime considerations differently.

## Common mistakes
- macro overuse
- compile-time side effects
- FFI safety assumptions
- wrong memory-management mode
- backend-specific behavior left implicit

## Streamline
Use Nimble and the standard library before adding dependencies. Keep backend and memory mode explicit for nontrivial systems.

## AI directive
The agent must state backend, memory-management mode, native dependencies, and compile-time macro impact for low-level changes.

## Verify
`nim check`, test suite, release build, backend-specific integration, and native dependency checks.

Official: https://nim-lang.org/docs/