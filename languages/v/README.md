# V

**Status:** experimental/specialized

## Purpose
Simple native CLIs, cross-platform programs, and projects interested in a concise language with static typing and native compilation.

## Stack
V compiler/tooling -> v fmt -> v test -> sum types -> Option/Result -> channels.

## Memory
Current V documentation describes a default tracing GC, an autofree mode that remains WIP, and a manual mode. Do not standardize autofree in a production policy without verifying the current compiler/runtime state.

## Concurrency
Channels are the preferred communication mechanism in the documented concurrency model. Still bound channel capacity and worker count.

## Common mistakes
- trusting a maturity claim without testing the current toolchain
- unbounded channels
- assuming Option/Result eliminates all runtime errors
- using experimental memory management modes casually

## Streamline
Keep packages small, use sum types and Result/Option to make failure states explicit, and prefer simple control flow.

## AI directive
Agents must mark V features that are mature vs experimental and verify memory/concurrency behavior against current documentation.

## Verify
`v fmt`, `v test`, compiler checks, platform builds, and focused memory/concurrency tests.

Official: https://docs.vlang.io/

## Operating card

**Route:** compact native CLIs, utilities, cross-platform experiments.

**Fast path:** `v fmt` → build → tests → cross-platform compile.

**Native authority:** V compiler/toolchain and generated target behavior.

**Pair with:** C/Rust for established systems boundaries; Go/Python for larger service ecosystems.

**Boundary:** explicit FFI and resource ownership; test generated/native assumptions.

**Avoid:** relying on immature ecosystem behavior without pinning versions; implicit global state.

**Reliability:** bounded buffers/tasks, explicit error handling, deterministic cleanup.

**Verify:** format → compile → tests → target build → smoke test.

**AI learning loop:** prefer simple language constructs and inspect generated/runtime behavior for critical code.

**Research:** https://docs.vlang.io/
