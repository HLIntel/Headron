# Python

**Status:** production

## Purpose
AI/ML, LLM orchestration, automation, research, data, APIs, glue code, and fast iteration.

## Use when
- ecosystem leverage matters
- external integrations dominate
- iteration speed matters
- the hot path is elsewhere or can be isolated

## Use another language when
CPU/memory/latency constraints dominate and profiling shows Python is the bottleneck, or when compile-time ownership guarantees are a primary requirement.

## Stack
uv -> pyproject.toml/uv.lock -> Ruff -> Pyright -> pytest/Hypothesis -> profiling -> security scan
Core libraries: Pydantic, msgspec, attrs, immutables, AnyIO, HTTPX, cachetools, OpenTelemetry, Polars/PyArrow/DuckDB where data workloads justify them.

## Structure
```text
pyproject.toml
src/pkg/
tests/unit/
tests/integration/
tests/property/
scripts/
docs/
```

## State and data
Prefer typed models at boundaries. Use frozen value objects for configuration/state when practical. Do not return shared mutable objects from caches.

## Concurrency
Use TaskGroup, timeout, Semaphore, bounded queues, cancellation, and worker ownership. Avoid unmanaged create_task fan-out.

## Performance
Profile before rewriting. Check Python CPU time, allocations, serialization, network latency, and data-copy cost. Move only the measured hot path to Rust/C++/Mojo/Futhark rather than rewriting the system blindly.

## Common mistakes
- `Any` at boundaries
- giant dictionaries flowing through the application
- unlimited `gather()`/task creation
- cache without TTL/capacity
- hidden retries
- blocking calls inside async paths
- global mutable config

## Streamline
Use one project manifest, one lockfile, one validation boundary, shared helpers, table-driven configuration, and small side-effect modules.

## Learn into
typing/specification -> async structure -> validation -> profiling -> native extension boundary -> observability.

## Avoid
magic metaprogramming, framework wrappers that hide I/O, and premature native rewrites.

## AI directive
Generated Python must first become typed and bounded. Validate all model/tool/API outputs before side effects. Use a dedicated worktree for broad refactors.

## Verify
`uv run ruff check .`, `uv run pyright`, `uv run pytest` plus targeted Hypothesis/property tests.

Official: https://docs.python.org/ and https://docs.astral.sh/uv/