# Julia Operating Card

**Route:** numerical computing, simulation, scientific research, optimization, quant/research.

**Fast path:** project environment → formatter/linter → tests → BenchmarkTools → profiler.

**Native authority:** Julia package environments, compiler, standard library, profiler, multiple dispatch.

**Pair with:** Python for ecosystem-heavy ML; C/Rust/Fortran for narrow native kernels when measurement proves need.

**Boundary:** explicit array shapes/types where useful; isolate Python/ C/Fortran interop behind tested adapters.

**Avoid:** accidental type instability, global state in hot paths, unnecessary allocations, benchmarking with compilation noise.

**Reliability:** bounded tasks, explicit numerical tolerances, deterministic seeds for tests, resource-aware parallelism.

**Verify:** instantiate project → tests → allocation/type-stability inspection → benchmark → profiler.

**AI learning loop:** inspect dispatch + allocations before rewriting algorithms; preserve numerical invariants explicitly.

**Research:** https://docs.julialang.org/ · https://julialang.org/learning/ · https://julialang.org/research/
