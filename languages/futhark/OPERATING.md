# Futhark Operating Card

**Route:** data-parallel GPU/CPU kernels and functional array programming.

**Fast path:** compiler → tests → backend build → benchmark/profiler.

**Native authority:** Futhark compiler, type system, backend/runtime.

**Pair with:** Python/Julia for research orchestration; CUDA for hand-tuned CUDA-only kernels.

**Boundary:** arrays/shapes/types are explicit contracts; validate host/device transfer costs.

**Avoid:** unnecessary host-device copies, unbounded arrays, opaque backend assumptions.

**Reliability:** bounded data sizes, deterministic kernels, explicit numerical tolerances.

**Verify:** type/compile → functional tests → backend tests → numerical differential tests → benchmark.

**Profile a kernel:** Find costly GPU kernels or memory transfers using a representative dataset. Install the compiler from the [official installation guide](https://futhark.readthedocs.io/en/stable/installation.html). A `.fut` file needs a benchmark dataset; for example:

```futhark
-- ==
-- input { 1 } output { 2 }
entry main (x: i32): i32 = x + 1
```

Run `futhark test example.fut`, then `futhark bench --backend=opencl --profile --json=result.json example.fut` and `futhark profile result.json`. Inspect `result.prof/` for summaries and logs. Choose an installed GPU backend and representative inputs; the C backend does not record useful profiling information. The benchmark can ignore a program with no datasets, so confirm that its output names the dataset. These commands compile and run the program and create report files; they are an investigative workflow, not a read-only gate.

**AI learning loop:** understand array transformations and fusion before hand-optimizing kernels.

**Research:** https://futhark-lang.org/docs.html · https://futhark-lang.org/
