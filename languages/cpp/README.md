# C++

**Status:** production

## Purpose
Native high-performance systems, game/graphics engines, embedded/HPC workloads, low-latency applications, and existing C++ ecosystems.

## Stack
CMake + presets -> Ninja/appropriate build -> clang/LLVM or GCC/MSVC -> clang-tidy -> sanitizers -> GoogleTest/Catch2 -> profiler/debugger.
Package management may use Conan/vcpkg or system packages; keep dependency ownership explicit.

## Design
Prefer RAII, value semantics, explicit ownership, `std::span`/ranges where useful, and narrow interfaces.

## Memory
Avoid owning raw pointers. Make ownership and lifetime obvious. Treat manual memory, casts, macros, custom allocators, and FFI as review hotspots.

## Concurrency
Bound thread pools and queues. Use sanitizer/test support where available. Never assume native threading means unlimited safe parallelism.

## Performance
Measure allocations, cache locality, branch behavior, contention, vectorization, and I/O. Use profiling rather than intuition.

## Common mistakes
- ownership ambiguity
- unnecessary heap allocation
- header coupling
- template overengineering
- undefined behavior hidden behind optimization
- dependency/build configuration drift

## Streamline
Target-oriented CMake, presets, imported targets, modern headers/modules where toolchain support is verified, and small translation units.

## AI directive
Generated C++ must be compiled and sanitized. Treat lifetime, undefined behavior, ABI, and build-system changes as high-risk.

## Verify
Debug + sanitizers + unit/integration tests + static analysis; release/profile builds only after functional correctness.

Official: https://en.cppreference.com/ and https://cmake.org/

## Operating card

**Route:** engines, graphics, HPC, embedded, mature native ecosystems.

**Fast path:** CMake/Bazel → clang-format → clang-tidy → compiler warnings-as-errors → tests → sanitizers/fuzzing.

**Native authority:** compiler, standard library, build system, debugger, sanitizers.

**Pair with:** Rust for safer new native boundaries; Python/TypeScript for product/control planes; CUDA for GPU kernels.

**Boundary:** RAII, ownership types/conventions, narrow ABI, explicit serialization/versioning.

**Avoid:** raw owning pointers, exception/error ambiguity, giant templates, global state, data races, unchecked casts.

**Reliability:** RAII cleanup, bounded threads/queues, deadlines, explicit shutdown, ASan/UBSan/TSan where supported.

**Verify:** format → compile warnings-as-errors → tests → sanitizers → fuzz → benchmark.

**AI learning loop:** identify ownership and lifetime before editing; treat templates/macros/build files as high-context surfaces.

**Research:** https://isocpp.org/ · https://en.cppreference.com/
