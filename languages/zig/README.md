# Zig

**Status:** mature-specialized

## Purpose
Explicit low-level tooling, C interoperability, cross-compilation, small native binaries, and systems code where allocator/build control matters.

## Stack
Zig compiler/build system -> `zig fmt` -> `zig test` -> `std.testing` -> explicit allocator discipline -> `zig cc` for C-family toolchain integration.

## Core model
Allocators are explicit and comptime provides compile-time metaprogramming without a conventional macro system.

## Memory
Make allocator ownership visible. Use testing allocators in tests. Distinguish allocation strategy from lifetime strategy.

## Concurrency
Bound workers and queues at the application level. Do not mistake explicit memory management for automatic concurrency safety.

## Common mistakes
- leaking allocator ownership across APIs
- global state
- compile-time cleverness that harms readability
- assuming C interop is automatically safe
- platform assumptions

## Streamline
Centralize build configuration in `build.zig`, use explicit targets, and keep allocator choices close to the subsystem that owns memory.

## Performance
Measure binary size, startup, allocations, hot loops, and syscall behavior.

## AI directive
Every generated allocation should make ownership and deallocation discoverable. Do not accept hidden ownership transfer.

## Verify
`zig fmt --check` where supported by workflow, `zig test`, target builds, and focused allocator/leak tests.

Official: https://ziglang.org/documentation/master/