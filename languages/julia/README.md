# Julia

**Status:** production-specialized

## Purpose
Scientific computing, numerical modeling, simulation, optimization, quantitative research, and high-performance analytical workloads.

## Stack
Pkg -> Project.toml/Manifest.toml -> Julia formatter/language tooling -> tests -> BenchmarkTools/Profile -> domain packages such as Arrow, Tables, DataFrames, CUDA where needed.

## State/type model
Use concrete data representations in hot paths. Avoid broad `Any`-typed collections when performance matters.

## Multiple dispatch
Use dispatch to encode domain behavior cleanly, but avoid method ambiguity and excessive dispatch layers.

## Common mistakes
- type instability
- unnecessary allocations
- global mutable state
- optimizing before profiling
- mixing environment dependencies globally

## Streamline
Keep environments project-scoped. Separate pure numerical kernels from I/O and orchestration.

## Performance
Measure type inference/allocations, loop costs, compilation latency, and steady-state runtime. Distinguish first-call latency from warmed performance.

## AI directive
The agent should inspect the performance profile and environment before changing algorithm/data structures.

## Verify
`Pkg.test`, targeted benchmarks, profiling, allocation checks, and reproducible project environments.

Official: https://docs.julialang.org/
