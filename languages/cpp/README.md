# C++

Purpose: native high-performance systems, game/graphics engines, embedded systems, HPC, low-latency workloads, and existing C++ ecosystems.

## When to choose C++
- Performance and ecosystem requirements justify native complexity.
- Existing platform/engine/ABI constraints make C++ the practical choice.

## Modern baseline
Prefer modern C++ with RAII, smart pointers, value semantics, ranges, spans, concepts where justified, and clear ownership.

C++20 modules and C++23 library features are part of the modern language/tooling landscape, but toolchain support must be checked before standardizing them.

Reference: https://en.cppreference.com/

## Memory
Prefer deterministic ownership. Avoid raw owning pointers and hidden ownership transfers.

Use sanitizers during development where supported: AddressSanitizer, UndefinedBehaviorSanitizer, and ThreadSanitizer are valuable safety layers.

## Performance
Use profiling before optimization. Benchmark hot paths and watch allocations, cache locality, branch behavior, and synchronization.

## Concurrency
Use clear ownership and bounded queues. Treat thread creation and background work as resources.

## AI-specific guidance
- Generated C++ needs compiler and sanitizer feedback, not visual confidence.
- Ask the compiler and static analyzers to expose lifetime/API mistakes.
- Treat templates, macros, unsafe casts, manual memory, and FFI as elevated review zones.

## Worktree
```bash
git worktree add -b feat/cpp-task ../Code-Development-wt/cpp-task main
```