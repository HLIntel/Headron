# Futhark

**Status:** research/specialized

## Purpose
Data-parallel numerical kernels compiled to efficient CPU/GPU code.

## Best use
Small compute-intensive components with regular data parallelism, especially when GPU/CPU kernel generation is the main value.

## Integration
`host language -> Futhark kernel -> C/Python/other generated interface -> result`

## Core idea
Functional/data-parallel structure enables compiler transformations while uniqueness-based approaches preserve practical in-place performance.

## Common mistakes
- using Futhark for orchestration
- ignoring host/device transfer cost
- assuming every algorithm maps efficiently to GPU execution

## Streamline
Keep the Futhark surface small and stable. Move orchestration, I/O, and policy into the host language.

## AI directive
The agent must identify parallelism/data movement before generating a Futhark rewrite.

## Verify
Compiler checks plus representative CPU/GPU benchmark comparisons and interface tests.

Official: https://futhark-lang.org/