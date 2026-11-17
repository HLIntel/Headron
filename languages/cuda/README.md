# CUDA

Status: specialized production ecosystem.

## Purpose
NVIDIA GPU kernels, accelerator components, HPC, scientific computing, and ML systems.

## Stack
CUDA toolkit/compiler, CUDA runtime, Nsight tooling, C/C++ host toolchain, CMake as appropriate, GPU unit/integration tests and workload benchmarks.

## Execution and memory
Explicitly model host/device ownership, transfers, streams, events, synchronization, allocation lifetime, launch configuration, and device errors.

## Concurrency
CUDA concurrency spans threads, blocks, kernels, streams, and host orchestration. Bound work, memory, streams, queued kernels, and synchronization points.

## Interop
Common boundaries include C/C++ host APIs, Python bindings, and accelerator frameworks. Treat tensor shape, dtype, device, stride/layout, ownership, and synchronization as interface contracts.

## Performance
Profile kernel time, occupancy, memory throughput, launch overhead, host/device transfers, synchronization, and end-to-end latency. Never infer performance from generated source alone.

## Editor and MCP
Native tooling first; the MCP layer per route is in [MCP-LANGUAGE-MATRIX.md](../../integrations/MCP-LANGUAGE-MATRIX.md). MCP never replaces profiler or executable benchmark evidence.

## Verify
compile -> targeted correctness tests -> numerical tolerance tests -> profiler -> representative workload -> regression baseline.

## Operating card

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
