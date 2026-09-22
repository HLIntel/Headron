# Mojo Operating Card

**Route:** AI kernels, heterogeneous CPU/GPU/accelerator workloads, Python-adjacent performance work.

**Fast path:** Mojo toolchain → formatter/compiler checks → focused tests → benchmark/profile on target hardware.

**Native authority:** Mojo compiler/runtime and current official docs; pin toolchain versions because ecosystem/toolchain maturity changes.

**Pair with:** Python for orchestration/ecosystem; CUDA for CUDA-specific control; Rust/C++ for mature native boundaries.

**Boundary:** keep Python/native interfaces explicit; validate numerical precision, device assumptions, memory ownership, and kernel launch constraints.

**Avoid:** assuming benchmark claims transfer to your workload, premature kernel rewrites, unbounded device memory, opaque Python/native crossings.

**Reliability:** explicit device/resource budgets, deterministic test fixtures, numerical tolerance contracts, fallback paths.

**Verify:** compiler checks → correctness tests → target-device benchmark → profiler → regression baseline.

**AI learning loop:** learn the generated/native execution model before optimizing syntax; preserve Python compatibility only where it reduces total complexity.

**Research:** https://docs.modular.com/mojo/ · https://www.modular.com/mojo
