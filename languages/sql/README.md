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

## Verify
schema migration -> constraint tests -> representative queries -> plan review -> integration tests -> backup/rollback check for high-impact changes.

## Operating card

**Route:** durable data, transactional state, analytics/query boundaries.

**Fast path:** migration tool → schema lint → transaction tests → query plan → integration tests.

**Native authority:** target database engine, SQL dialect, migration tool, query planner.

**Pair with:** Python/Go/Rust/TypeScript services; Redis only as explicitly non-authoritative cache/queue unless the design says otherwise.

**Boundary:** schema/version/transaction/isolation contracts; parameterized queries; explicit limits and pagination.

**Avoid:** N+1 queries, unbounded scans, dynamic SQL concatenation, implicit transactions, cache-as-source-of-truth.

**Reliability:** migrations reversible where practical, indexes measured, timeouts, connection pool limits, transaction scopes.

**Verify:** migration → schema tests → query plans → integration/rollback tests → representative load.

**AI learning loop:** inspect schema and indexes before query edits; understand transaction semantics before changing writes.

**Research:** https://www.postgresql.org/docs/ · https://dev.mysql.com/doc/ · https://sqlite.org/docs.html
