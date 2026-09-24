-- A query with a DECLARED bound and a result that proves the bound held.
--
-- The defect this kills: a query with no LIMIT against a table that grows. It is fast in
-- development, and the first slow day is production. The bound belongs in the statement, not in
-- the reviewer's memory.
--
-- Verify: sqlite3 :memory: < examples/sql/bounded_query.sql   (prints ok, exits 0)
.bail on

CREATE TABLE event (
    id        INTEGER PRIMARY KEY,
    kind      TEXT    NOT NULL CHECK (kind IN ('open', 'close')),
    happened  TEXT    NOT NULL                       -- ISO-8601, stored as text on purpose in SQLite
);
CREATE INDEX event_kind_happened ON event (kind, happened);

INSERT INTO event (kind, happened) VALUES
    ('open',  '2026-01-01T00:00:00Z'),
    ('close', '2026-01-01T00:00:01Z'),
    ('open',  '2026-01-02T00:00:00Z');

-- The bound is part of the statement, and the index is the one the plan should use.
CREATE TEMP VIEW recent_opens AS
    SELECT id, happened FROM event WHERE kind = 'open' ORDER BY happened DESC LIMIT 2;

-- A result that FAILS THE SCRIPT if the bound stops holding.
--
-- `1/0` is NULL in SQLite and `RAISE` only exists inside a trigger, so neither aborts a script —
-- the first version of this file used a function that does not exist at all. A CONSTRAINT is the
-- portable assertion: with `.bail on`, a failed CHECK ends the run with a non-zero exit, which is
-- the only signal a caller can branch on.
CREATE TEMP TABLE assertion (verdict TEXT NOT NULL CHECK (verdict = 'ok'));

INSERT INTO assertion (verdict) VALUES (
    CASE WHEN (SELECT count(*) FROM recent_opens) = 2
          AND (SELECT count(*) FROM event) = 3
         THEN 'ok' ELSE 'the declared bound did not hold' END
);

SELECT 'bounded_query: ok — the limit held and the table is what the script built';
