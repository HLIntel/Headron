"""Five caching strategies under one crash and one direct database write — each trade-off PROVEN.

Decision record: systems/decisions.yaml `caching_strategies` (`atlas decide caching_strategies`).
The claims below are the record's; this file exits non-zero if any of them stops being true.

  write-through   every acknowledged write survives a cache crash; each write pays for the DB
  write-back      a crash between acknowledgement and flush LOSES acknowledged writes
  write-around    writes skip the cache, so a hot key re-read after a write misses once
  cache-aside     a write made straight to the DB is invisible until the entry is invalidated
  read-through    the application never touches the DB; the cache fills itself on a miss
"""
from __future__ import annotations

WRITES = [(f"k{i}", i) for i in range(10)]


def write_through(db: dict, cache: dict) -> None:
    for key, value in WRITES:
        db[key] = value          # the DB write finishes before the caller is acknowledged
        cache[key] = value


def write_back(db: dict, cache: dict, flush_after: int) -> None:
    dirty: dict = {}
    for n, (key, value) in enumerate(WRITES, 1):
        cache[key] = dirty[key] = value   # acknowledged here, durable only after a flush
        if n == flush_after:
            db.update(dirty)
            dirty.clear()
    cache.clear()                # the crash: the cache node dies, unflushed writes with it


def lost(db: dict) -> int:
    return sum(1 for key, value in WRITES if db.get(key) != value)


def main() -> int:
    db, cache = {}, {}
    write_through(db, cache)
    cache.clear()                # the same crash
    assert lost(db) == 0, "write-through lost an acknowledged write"

    db = {}
    write_back(db, {}, flush_after=6)
    assert lost(db) == 4, f"write-back should lose the 4 unflushed writes, lost {lost(db)}"

    db, cache, misses = {"hot": 1}, {"hot": 1}, 0
    db["hot"] = 2                # write-around: the write goes to the DB only
    cache.pop("hot", None)       # ...and invalidates, so the next read must miss
    if "hot" not in cache:
        misses += 1
        cache["hot"] = db["hot"]
    assert misses == 1 and cache["hot"] == 2, "write-around should miss once, then read fresh"

    db, cache = {"price": 10}, {"price": 10}
    db["price"] = 12             # cache-aside, written straight to the DB, never invalidated
    assert cache["price"] == 10, "cache-aside should serve the stale value until invalidated"

    calls = []

    def read_through(key: str) -> int:
        if key not in cache:
            calls.append(key)    # only the cache layer ever reaches the DB
            cache[key] = db[key]
        return cache[key]
    cache = {}
    assert [read_through("price") for _ in range(3)] == [12] * 3 and calls == ["price"]

    print("caching: write-through 0 lost · write-back 4 lost · write-around 1 miss · "
          "cache-aside stale until invalidated · read-through 1 DB call for 3 reads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
