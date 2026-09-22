# SQL Operating Card

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
