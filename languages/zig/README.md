# Zig

Purpose: low-level tooling, explicit allocation, C interoperability, cross-compilation, system utilities, and small performance-sensitive binaries.

## When to choose Zig
- Need explicit memory management without a large abstraction layer.
- Need straightforward C interoperability or cross-compilation.
- Need a small systems tool with strong build control.

## Core ideas
- allocators are explicit
- comptime enables compile-time specialization
- const expresses no reassignment for a binding
- the build system can manage reproducible dependency/build configuration

Official: https://ziglang.org/documentation/master/ and https://ziglang.org/learn/build-system/

## Memory
Pass allocators explicitly through APIs where ownership depends on allocation strategy.

Test with `std.testing.allocator` to expose leaks in tests.

## Cross-compilation
Use explicit targets rather than assuming the developer machine equals the deployment machine.

`zig targets` can expose supported target combinations.

## Performance
Measure allocations, binary size, startup time, and hot-path work. Use comptime when it makes a meaningful workload improvement without hiding runtime behavior.

## AI-specific guidance
- Make allocation ownership visible in generated code.
- Reject hidden global state when local ownership is possible.
- Have agents explain allocator ownership before changing memory-heavy code.

## Worktree
```bash
git worktree add -b feat/zig-task ../Code-Development-wt/zig-task main
```