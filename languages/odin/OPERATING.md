# Odin Operating Card

**Route:** data-oriented engines, games, graphics, simulations, performance-heavy native tools.

**Fast path:** `odin check`/build → tests → profiler → representative workload.

**Native authority:** Odin compiler/toolchain, explicit data layout, allocators, debugger/profiler.

**Pair with:** C/C++/GPU APIs for graphics boundaries; Python for tooling; Rust for selected safety-critical native components.

**Boundary:** own allocators and lifetimes explicitly; define SoA/AoS decisions from workload measurements.

**Avoid:** accidental pointer-heavy designs, hidden global state, speculative abstraction layers, premature SIMD.

**Reliability:** bounded worker queues, deterministic teardown, explicit memory arenas, resource budgets.

**Verify:** compile/check → tests → debug runtime → profiler → release benchmark.

**AI learning loop:** model data layout and ownership first; optimize access patterns only after profiling.

**Research:** https://odin-lang.org/docs/ · https://github.com/odin-lang/Odin
