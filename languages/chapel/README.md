# Chapel

**Status:** mature-specialized/research

## Purpose
Large-scale parallel and distributed computing, HPC, data-parallel algorithms, and GPU-aware parallel workflows.

## Core model
Chapel has task parallelism, data parallelism, locales for distributed memory, and structured constructs such as `cobegin` and `coforall`.

## Bounds
A `coforall` creates a task per iteration. The application must still reason about task count and work size. Use structured parallelism and explicit problem sizing.

## GPU
Chapel can target GPU sublocales and generate kernels for eligible parallel constructs. Treat GPU offload as a workload/data-movement decision, not an automatic speedup.

## Common mistakes
- unbounded coforall fan-out
- ignoring communication cost
- assuming distributed memory is free
- overlooking CPU/GPU placement

## Streamline
Express parallelism at the highest useful abstraction level, then profile communication, synchronization, and memory movement.

## AI directive
Agents must specify task count, locale placement, data distribution, and synchronization behavior before generating large parallel loops.

## Verify
Correctness tests on single locale first, then multi-locale/GPU tests; profile communication and synchronization.

Official: https://chapel-lang.org/docs/
