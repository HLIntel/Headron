# Julia

Purpose: scientific computing, simulation, numerical research, optimization, quantitative computing, and high-performance analytical workloads.

## When to choose Julia
- Numerical algorithms and scientific models are central.
- Multiple dispatch naturally expresses the domain.
- You want high-level research code that can approach compiled numerical performance after optimization.

## Project discipline
Keep `Project.toml` and `Manifest.toml` aligned with reproducible environments.

Use package environments instead of a global dependency state.

Official: https://docs.julialang.org/

## Performance
Use Julia's profiler and allocation tools before optimizing.

Watch type instability, allocations in hot loops, unnecessary copying, and global mutable state.

Prefer concrete, stable data representations in performance-critical paths.

## AI/data use
Julia fits as a research kernel behind Python or a standalone numerical service. Keep data-contract boundaries explicit when Python/Go/Rust/TypeScript call into Julia.

## Worktree
```bash
git worktree add -b feat/julia-task ../Code-Development-wt/julia-task main
```