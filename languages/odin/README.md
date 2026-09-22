# Odin

**Status:** production-specialized

## Place in the Atlas
Use Odin under **data-oriented native systems** and **game/graphics tooling**, not as a universal C++ replacement.

## Purpose
High-performance native software where data layout, simplicity, control, and systems-level behavior matter.

## Strong fits
- game engines
- graphics
- simulation
- data-oriented systems
- performance-sensitive native tools

## Core practice
Design data layout before clever abstraction. Keep hot data contiguous and minimize unnecessary indirection.

## Common mistakes
- copying object-oriented architecture from C++ directly
- over-allocating
- hiding data movement
- optimizing without a workload

## Streamline
Use Odin's standard/core packages first, explicit memory/resource ownership, and simple procedures. Keep subsystems small.

## AI directive
Generated code should identify data layout, ownership, allocation frequency, and hot loops before proposing optimization.

## Verify
Compiler checks, tests, release builds, workload benchmarks, and graphics/API integration tests where relevant.

Official: https://odin-lang.org/