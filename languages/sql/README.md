# SQL / PostgreSQL

**Status:** foundational/production

## Purpose
Persistent data, transactions, relational constraints, analytical queries, and backend state.

## Core practice
Model invariants in the database where appropriate: types, constraints, indexes, unique keys, foreign keys, and transactions.

## Performance
Use `EXPLAIN`/`EXPLAIN ANALYZE`, inspect query plans, indexes, row estimates, buffers, and memory behavior before rewriting application code.

## Common mistakes
- N+1 queries
- missing constraints
- unbounded result sets
- SELECT * across large tables
- dynamic SQL/string interpolation
- transactions that live too long
- cache becoming source of truth

## Streamline
Use prepared statements, set-based operations, appropriate indexes, pagination/cursors, and narrow projections.

## AI directive
Agents must state transaction boundary, expected cardinality, indexes affected, and idempotency before generating high-impact database changes.

## Verify
Migration tests, constraint tests, query-plan checks, concurrency tests, and rollback validation.

Official: https://www.postgresql.org/docs/current/