# Python Operating Card

**Route:** AI/ML, automation, orchestration, data, APIs, prototypes.

**Fast path:** `uv`/virtualenv → Ruff → Pyright → pytest → Hypothesis → targeted profiler.

**Native authority:** CPython, `python -m`, packaging metadata, debugger, profiler.

**Pair with:** Rust/Mojo for hot native kernels; Go/Rust for long-lived services when concurrency/resource guarantees dominate; SQL for data ownership.

**Boundary:** Pydantic/JSON Schema or equivalent at external boundaries; explicit payload/time/queue limits; never trust model output as typed state.

**Avoid:** giant `__init__` exports, implicit globals, mutable defaults, `asyncio.create_task()` without ownership, infinite retries, unbounded caches, dependency duplication.

**Reliability:** deadlines, cancellation, bounded executors/queues, idempotency keys, health/readiness, structured logs.

**Verify:** `ruff check .` → `ruff format --check .` → `pyright` → `pytest` → targeted Hypothesis/fuzz/mutation.

**AI learning loop:** trace call graph → inspect types/contracts → make smallest edit → run narrow test → run full gate → record invariant.

**Research:** https://docs.python.org/3/ · https://packaging.python.org/ · https://docs.astral.sh/ruff/
