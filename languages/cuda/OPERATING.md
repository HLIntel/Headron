# CUDA Operating Card

**Route:** GPU kernels, deep learning primitives, numerical acceleration, high-throughput compute.

**Fast path:** compile → correctness test → Nsight profiling → occupancy/memory analysis → regression benchmark.

**Native authority:** CUDA compiler/toolkit, runtime, profiler, sanitizers/debugging tools.

**Pair with:** Python/C++/Rust host code; Mojo/Futhark when portability or higher-level kernel generation is useful.

**Boundary:** explicitly manage host/device ownership, streams, synchronization, shapes, strides, and precision.

**Avoid:** unnecessary synchronization, hidden transfers, unchecked indexing, assuming occupancy equals performance.

**Reliability:** device-memory caps, stream ownership, synchronization contracts, error checking, deterministic test cases.

**Verify:** compile → kernel correctness → compute-sanitizer where applicable → Nsight profile → benchmark.

**AI learning loop:** inspect memory traffic and synchronization before changing kernels; measure on target hardware.

**Research:** https://docs.nvidia.com/cuda/ · https://developer.nvidia.com/nsight-systems
