# Python Advanced Engineering

Python is the main language in this repository for AI, orchestration, research, data, and automation.

## Core stack
| Tool | Use |
|---|---|
| Pydantic | Runtime contracts and validation |
| msgspec | Fast typed serialization and validation |
| immutables | Persistent immutable mappings |
| attrs | Frozen and structured classes |
| dataclasses | Standard-library value objects |
| Pyright | Static type analysis |
| Ruff | Linting and formatting |
| Hypothesis | Property-based testing |
| AnyIO | Structured async abstractions |
| cachetools | Bounded caches |

## Immutability
Use frozen dataclasses, frozen Pydantic models, attrs frozen classes, immutable mappings, tuples, and narrow interfaces.

Important distinctions:
- Final controls rebinding intent.
- ReadOnly describes an interface that should not mutate a field.
- frozen=True prevents ordinary field assignment.
- immutable containers prevent nested mutation.

Do not describe Python frozen objects as absolute recursive immutability.

## Async bounds
Prefer asyncio.TaskGroup, asyncio.timeout, and semaphores.

Every task should have an owner, a cancellation path, and a bounded concurrency model.

Bad architecture: create a task for every input without a limit.
Better architecture: bounded worker concurrency plus structured task lifetime.

## Cache discipline
Use explicit capacity and TTL. Document eviction policy, invalidation, ownership, and stale behavior.

## Validation
Boundary flow:
external bytes -> parser -> size checks -> schema validation -> typed model -> application logic

Do not allow arbitrary external dictionaries to travel deep into the application.

## AI-generated Python
Run Ruff, Pyright, unit tests, property-based tests where useful, security scanning, dependency scanning, and diff review.