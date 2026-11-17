# C

Status: production.

## Purpose
Foundational systems programming, embedded, kernels, native libraries, ABI boundaries, and performance-critical components.

## Stack
Compiler (Clang/GCC/MSVC as required), CMake/Make/Ninja, clangd, formatter/linter, GDB/LLDB, ASan/UBSan/TSan, fuzzing, package tooling appropriate to the target.

## State and memory
Ownership is manual. Make allocation/free responsibility explicit at every interface. Prefer clear lifetimes, narrow mutable state, checked sizes, and explicit cleanup paths.

## Concurrency
Choose OS threads, atomics, or runtime libraries deliberately. Bound worker count, queues, waits, retries, and shutdown.

## Interop
C is a preferred ABI boundary when the interface must be language-neutral. Define layout, ownership, error codes, versioning, and allocator ownership.

## Performance
Measure CPU, cache behavior, allocations, syscalls, contention, and tail latency. Use compiler optimization only after a representative baseline.

## Security
Use sanitizers, fuzzing, compiler warnings, static analysis, dependency scanning, and hardened build flags where appropriate.

## Editor and MCP
Native tooling first; the MCP layer per route is in [MCP-LANGUAGE-MATRIX.md](../../integrations/MCP-LANGUAGE-MATRIX.md). MCP output never replaces compiler or sanitizer diagnostics.

## Verify
format -> warnings -> build -> unit/integration -> sanitizers/fuzz -> security scan -> diff review.

## Operating card

**Route:** kernels, embedded, OS/runtime boundaries, FFI, minimal native dependencies.

**Fast path:** compiler warnings → clang-format → static analysis → unit tests → sanitizers/fuzzing.

**Native authority:** compiler, libc/platform ABI, debugger, sanitizers.

**Pair with:** Rust/C++ for safer higher-level native components; Python/Go for orchestration.

**Boundary:** every pointer has documented ownership/lifetime; every buffer has a size; ABI/version assumptions are tested.

**Avoid:** unchecked string/buffer operations, implicit ownership, integer overflow assumptions, global mutable state.

**Reliability:** explicit cleanup paths, bounds checks, watchdog/timeout behavior, deterministic resource release.

**Verify:** warnings-as-errors → tests → ASan/UBSan/TSan where applicable → fuzzing → cross-target build.

**AI learning loop:** trace pointer lifetime and error paths before changing code; do not “fix” warnings by suppressing them.

**Research:** https://www.iso.org/standard/82075.html · https://clang.llvm.org/docs/
