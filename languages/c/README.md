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

## VS Code + MCP
Native: clangd + C/C++ tooling + debugger + tasks/terminal.
MCP: Serena for LSP-backed semantic navigation; GitHub, Context7, Semgrep for external/docs/security capability.
Do not replace compiler or sanitizer diagnostics with MCP output.

## Verify
format -> warnings -> build -> unit/integration -> sanitizers/fuzz -> security scan -> diff review.
