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

## What enforces this now

**Every store cycles, and the bound is in BYTES.** The audit stream is the worked example:
`agent_policy/audit/max_stream_bytes` caps it, and the cap is a REFUSAL rather than a prune —
a rotation there would delete the evidence the stream exists to hold. The refusal is itself the
last event, so a truncated stream and a finished one can never be read as the same file.

The stream is a **hash chain, not a log**: each event carries the hash of the one before it, so a
removed or edited event breaks every hash after it and `agentaudit.py verify` names the first
break by sequence number. A log its own subject can append to can also be edited, and an edited
log is indistinguishable from an honest one.

Its reader tolerates a malformed line and REPORTS it rather than raising — a verifier that crashes
on the tampering it exists to detect reports none of it.
