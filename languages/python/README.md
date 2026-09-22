# Python

Purpose: AI, automation, orchestration, research, data, APIs, and fast application/system prototyping.

## When to choose Python
- Model APIs, ML/LLM pipelines, research notebooks, automation, data transformations, service orchestration.
- Choose a faster systems language for CPU-hot inner loops, memory-sensitive services, or strict systems boundaries.

## Core stack
- Pydantic: contracts and runtime validation
- msgspec: high-performance serialization/validation
- immutables: persistent immutable mappings
- attrs / dataclasses: structured values
- Pyright: static typing
- Ruff: lint/format
- Hypothesis: property-based tests
- AnyIO: structured async
- cachetools: bounded caching
- uv: environment/package workflow

## Recommended project shape
```text
pyproject.toml
src/package_name/
tests/
  unit/
  integration/
  property/
scripts/
docs/
```

Keep application imports and package metadata centralized in `pyproject.toml`. Avoid undocumented shell installation state.

## Strictness
Use type annotations throughout application boundaries. Prefer `unknown-like` discipline with Python's `object`/precise unions over `Any` where possible.

Use `Final` for non-rebinding intent and frozen models/value objects for state that should not change.

## Async
Prefer `asyncio.TaskGroup` for owned task lifetimes and `asyncio.timeout()` for deadlines.

Bound concurrency with semaphores or a bounded worker pool. Do not create one unmanaged task per untrusted input.

## Caching
Every cache needs an explicit maximum size, expiration, key definition, ownership strategy, and invalidation strategy.

## Performance
Measure first. Use `cProfile`, `py-spy`, sampling profilers, allocation measurements, and workload benchmarks before optimizing.

Common move: keep the Python orchestration layer and move only proven hot paths to Rust/extension code instead of rewriting the whole system.

## AI-specific guidance
- Validate model/tool output before side effects.
- Put side-effecting code behind narrow functions.
- Make generated code pass Ruff and Pyright before integration.
- Use property tests for parsers, validators, financial/data transformations, and state machines.
- Run generated code in a worktree for multi-file or risky changes.

## Worktree
```bash
git worktree add -b feat/python-task ../Code-Development-wt/python-task main
```

Language docs: https://docs.python.org/ and https://typing.python.org/