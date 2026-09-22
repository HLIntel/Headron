# Futhark Operating Card

**Route:** data-parallel GPU/CPU kernels and functional array programming.

**Fast path:** compiler → tests → backend build → benchmark/profiler.

**Native authority:** Futhark compiler, type system, backend/runtime.

**Pair with:** Python/Julia for research orchestration; CUDA for hand-tuned CUDA-only kernels.

**Boundary:** arrays/shapes/types are explicit contracts; validate host/device transfer costs.

**Avoid:** unnecessary host-device copies, unbounded arrays, opaque backend assumptions.

**Reliability:** bounded data sizes, deterministic kernels, explicit numerical tolerances.

**Verify:** type/compile → functional tests → backend tests → numerical differential tests → benchmark.

**AI learning loop:** understand array transformations and fusion before hand-optimizing kernels.

**Research:** https://futhark-lang.org/docs.html · https://futhark-lang.org/
