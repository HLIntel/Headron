# Python Operating Card

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
