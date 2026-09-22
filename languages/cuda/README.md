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

## VS Code + MCP
Native: NVIDIA/CUDA VS Code tooling, compiler, debugger/profilers.
MCP: Serena where CUDA semantic support is installed; GitHub, Context7, Semgrep.
Do not let MCP replace Nsight or executable benchmark evidence.

## Verify
compile -> targeted correctness tests -> numerical tolerance tests -> profiler -> representative workload -> regression baseline.
