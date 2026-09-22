# V

**Status:** experimental/specialized

## Purpose
Concise native programs, CLIs, cross-platform applications, and exploration of simpler systems-language design.

## Stack
V compiler/tooling -> formatting -> tests -> Option/Result -> sum types -> channels.

## Memory
Current V docs describe a tracing GC default, an autofree mode that remains WIP, and manual memory options. Treat autofree as experimental until the documentation declares it stable.

## Common mistakes
- trusting aspirational claims over toolchain behavior
- unbounded channel/work fan-out
- ignoring error propagation
- treating experimental memory management as production default

## Streamline
Prefer small modules, explicit error values, and a narrow dependency surface.

## AI directive
Agents must verify the maturity of a V feature before relying on it in a production recommendation.

## Verify
formatter, tests, compiler checks, platform builds, memory/concurrency tests.

Official: https://docs.vlang.io/