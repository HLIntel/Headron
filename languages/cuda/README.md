# CUDA

**Status:** production-specialized

## Purpose
GPU kernels, accelerator computing, parallel numerical workloads, and NVIDIA GPU execution.

## Position
CUDA is a GPU programming platform/toolchain rather than a general-purpose replacement for the host language.

## Stack
CUDA Toolkit -> `nvcc` -> C/C++ host code + CUDA kernels -> Nsight Systems/Compute -> tests/benchmarks.

## Core practice
Separate host/device responsibilities. Analyze memory movement, coalescing, occupancy, synchronization, and kernel launch overhead.

## Common mistakes
- optimizing kernel code while ignoring host/device transfer
- unbounded GPU work
- excessive synchronization
- assuming more threads always means more performance
- architecture-specific assumptions without build targets

## Streamline
Keep kernels small, data-oriented, and benchmarkable. Use the host language for orchestration and policy.

## AI directive
The agent must identify kernel boundaries, input shapes, memory layout, transfer cost, and target architecture before proposing a GPU rewrite.

## Verify
Functional tests plus representative GPU benchmarks. Use Nsight tools for execution/memory analysis.

Official: https://docs.nvidia.com/cuda/cuda-programming-guide/