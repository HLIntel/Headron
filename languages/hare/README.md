# Hare

**Status:** mature-specialized

## Purpose
Simple systems programming with static typing, manual memory management, and a minimal runtime.

## Strong fits
System tools, networking, compilers, low-level utilities, and small performance-sensitive programs.

## Core practice
Keep ownership and cleanup obvious. Prefer simple data/control structures over abstraction-heavy designs.

## Common mistakes
- unclear allocation ownership
- manual cleanup paths that are not tested
- platform assumptions
- overly clever low-level code

## Streamline
Use the minimal runtime and language surface to reduce dependency and operational complexity.

## AI directive
Every allocation and cleanup path in generated code should be locally understandable and testable.

## Verify
Compiler checks, tests, platform builds, and profiling/debugging for native behavior.

Official: https://harelang.org/
