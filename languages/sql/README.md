# SQL

Status: production.

## Purpose
Declarative data access, relational schema design, transactions, analytical queries, migrations, constraints, and database-backed application state.

## Stack
Database-native client, migration system, schema formatter/linter, query-plan tooling, test database, backup/restore tooling.

## State
Schema, constraints, transactions, isolation level, locking, indexes, and migrations are part of the program. Treat schema changes as versioned code.

## Concurrency
Understand transactions, isolation, locks, deadlocks, connection pools, queueing, statement timeouts, and retry/idempotency behavior.

## Interop
Cross-language interfaces should use typed schemas or generated models. Never depend on implicit column order or undocumented coercions.

## Performance
Use EXPLAIN/query plans, indexes, cardinality, row counts, I/O, lock waits, connection saturation, and representative workloads.

## Security
Parameterized queries, least-privilege accounts, bounded result sizes, statement timeouts, migration review, and separate development/staging/production credentials.

## VS Code + MCP
Native: database extension/client, SQL language support, migration tools, query plans.
MCP: DBHub for bounded database/schema/query access; GitHub for migration history; Context7 for client/framework docs.
Default to read-only connections for agent exploration.

## Verify
schema migration -> constraint tests -> representative queries -> plan review -> integration tests -> backup/rollback check for high-impact changes.
