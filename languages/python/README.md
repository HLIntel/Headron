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
uv -> pyproject.toml/uv.lock -> Ruff -> basedpyright -> pytest/Hypothesis -> profiling -> security scan
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
`uv run ruff check .`, `uv run basedpyright`, `uv run pytest` plus targeted Hypothesis/property tests.

Official: https://docs.python.org/ and https://docs.astral.sh/uv/

## Operating card

**Route:** AI/ML, automation, orchestration, data, APIs, prototypes.

**Fast path:** `uv`/virtualenv → Ruff → basedpyright → pytest → Hypothesis → targeted profiler.

**Native authority:** CPython, `python -m`, packaging metadata, debugger, profiler.

**Pair with:** Rust/Mojo for hot native kernels; Go/Rust for long-lived services when concurrency/resource guarantees dominate; SQL for data ownership.

**Boundary:** Pydantic/JSON Schema or equivalent at external boundaries; explicit payload/time/queue limits; never trust model output as typed state.

**Avoid:** giant `__init__` exports, implicit globals, mutable defaults, `asyncio.create_task()` without ownership, infinite retries, unbounded caches, dependency duplication.

**Reliability:** deadlines, cancellation, bounded executors/queues, idempotency keys, health/readiness, structured logs.

**Verify:** `ruff check .` → `ruff format --check .` → `basedpyright` → `pytest` → targeted Hypothesis/fuzz/mutation.

**Benchmark a Python function:** Write a pytest test that calls the `benchmark` fixture on the function and checks its result. With a project environment and a benchmark file, run `uv run --with 'pytest<9.2' --with 'pytest-benchmark==5.3.0' pytest tests/test_benchmark.py --benchmark-only`. Adjust the path to the project's benchmark tests. This combination passed a local sample; pytest 9.2.0 failed with pytest-benchmark 5.3.0. Project dependency constraints may require a different compatible combination. Compare runs on the same workload and environment; installing the plugin or running pytest alone is not evidence that a benchmark ran. See [pytest-benchmark usage](https://pytest-benchmark.readthedocs.io/en/stable/usage.html).

**AI learning loop:** trace call graph → inspect types/contracts → make smallest edit → run narrow test → run full gate → record invariant.

**Research:** https://docs.python.org/3/ · https://packaging.python.org/ · https://docs.astral.sh/ruff/
