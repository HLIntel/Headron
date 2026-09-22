# Storage and State

Storage is part of the system's correctness model, not merely persistence.

## Choose by state shape
| Need | Typical fit |
|---|---|
| local transactional state | SQLite |
| relational/shared state | PostgreSQL or equivalent |
| ephemeral bounded cache | bounded in-memory cache |
| shared cache/queue | Redis-compatible store when justified |
| analytical columnar data | Parquet + Arrow |
| local analytics | DuckDB |
| object/blob storage | S3-compatible object store |
| vector retrieval | vector store only when semantic retrieval is actually required |

## State rules
Document:
- owner
- source of truth
- schema/version
- consistency requirement
- transaction boundary
- retention
- deletion
- backup/recovery
- concurrency
- idempotency

## Mutation model
`input -> validate -> transactional write -> commit -> observable result`

Do not let cache state become the source of truth accidentally.

## Schema evolution
Prefer additive migrations. Version breaking changes. Make readers tolerant when a rolling deployment requires it.

## Durability
Know whether a write is:
- memory only
- journaled
- committed
- replicated
- externally acknowledged

Do not call an operation durable merely because an in-process function returned.

## AI/bot storage
Agents and bots need explicit retention and state budgets. Avoid unlimited conversation/history persistence.

## Optimization
Use batching, prepared statements, indexes, columnar formats, compression, and caching only after profiling the actual bottleneck.