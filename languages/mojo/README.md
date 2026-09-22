# Mojo

Purpose: AI-oriented systems programming, accelerator/GPU work, numerical kernels, and experiments that combine Python interoperability with lower-level performance control.

## When to choose Mojo
- A Python workflow has a measured performance bottleneck suitable for compiled kernels.
- CPU/GPU/accelerator execution is central to the workload.
- You want to explore systems-level AI code without leaving the Python ecosystem entirely.

## Python interoperability
Mojo can import Python modules and call Python APIs through its Python interoperability layer. The Python environment therefore remains part of the runtime design.

Official: https://mojolang.org/docs/

## GPU
Use the GPU programming model when the algorithm has sufficient parallel work and data movement does not dominate the expected speedup.

Always benchmark host-to-device transfers, kernel execution, occupancy/utilization, and end-to-end latency.

## AI-specific rule
Do not rewrite Python into Mojo merely because Mojo is lower-level. First identify the hot kernel, data movement, memory layout, and actual bottleneck.

## Worktree
```bash
git worktree add -b feat/mojo-task ../Code-Development-wt/mojo-task main
```