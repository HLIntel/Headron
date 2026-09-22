# C

**Status:** foundational/production

## Purpose
Operating systems, embedded, runtimes, native libraries, FFI boundaries, and low-level components.

## Stack
Clang/GCC -> CMake or Make/Ninja -> clang-tidy/static analysis -> sanitizers -> unit tests -> debugger/profiler.

## Core practice
Ownership must be explicit because the language does not provide Rust-style ownership checking. Treat pointers, lifetimes, buffers, integer conversions, and FFI as primary review surfaces.

## Common mistakes
- buffer bounds errors
- use-after-free
- integer overflow/underflow
- ownership ambiguity
- unchecked return values
- macro side effects

## Streamline
Keep APIs small, use structs to bundle invariants, pair allocation/free responsibility, and wrap unsafe C APIs behind narrow adapters.

## AI directive
Generated C must pass sanitizers/static analysis and include explicit ownership/bounds reasoning.

## Verify
Compiler warnings at high level, ASan/UBSan/TSan where applicable, tests, and targeted fuzzing.

Sources: https://clang.llvm.org/ and https://en.cppreference.com/w/c