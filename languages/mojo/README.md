# Mojo

**Status:** experimental/specialized

## Purpose
AI-oriented systems programming, numerical kernels, CPU/GPU/accelerator exploration, and performance-sensitive components that can interoperate with Python.

## Use when
A measured hot path needs compiled performance or accelerator-oriented control and the current Mojo toolchain supports the required feature.

## Do not use when
The ecosystem/toolchain maturity is the dominant requirement or a Python/NumPy/compiled-extension approach already solves the measured bottleneck.

## Stack
Mojo compiler/toolchain + Modular/MAX ecosystem + Python interoperability + accelerator/GPU tooling. Verify current compiler/API details before standardizing.

## Design
Keep the Python orchestration layer when it is productive; isolate kernels or specialized components behind small contracts.

## Performance
Benchmark end-to-end, including transfers, compilation effects, memory layout, vectorization, kernel launch, and synchronization.

## Common mistakes
- rewriting too much Python without a measured bottleneck
- ignoring data movement
- treating benchmark claims as universal
- coupling application architecture to experimental compiler details

## AI directive
Use Mojo for a measured boundary. The agent must identify the hot kernel and data-transfer path before proposing a large rewrite.

## Verify
Compiler checks + representative CPU/GPU benchmarks + Python interoperability tests.

Official: https://mojolang.org/docs/