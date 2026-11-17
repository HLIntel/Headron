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

## Operating card

**Route:** AI kernels, heterogeneous CPU/GPU/accelerator workloads, Python-adjacent performance work.

**Fast path:** Mojo toolchain → formatter/compiler checks → focused tests → benchmark/profile on target hardware.

**Native authority:** Mojo compiler/runtime and current official docs; pin toolchain versions because ecosystem/toolchain maturity changes.

**Pair with:** Python for orchestration/ecosystem; CUDA for CUDA-specific control; Rust/C++ for mature native boundaries.

**Boundary:** keep Python/native interfaces explicit; validate numerical precision, device assumptions, memory ownership, and kernel launch constraints.

**Avoid:** assuming benchmark claims transfer to your workload, premature kernel rewrites, unbounded device memory, opaque Python/native crossings.

**Reliability:** explicit device/resource budgets, deterministic test fixtures, numerical tolerance contracts, fallback paths.

**Verify:** compiler checks → correctness tests → target-device benchmark → profiler → regression baseline.

**AI learning loop:** learn the generated/native execution model before optimizing syntax; preserve Python compatibility only where it reduces total complexity.

**Research:** https://mojolang.org/docs/ · https://www.modular.com/mojo
