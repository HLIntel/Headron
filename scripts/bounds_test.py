"""Planted unbounded-growth cases (3.54.0): every writer that grew by one per run now has a bound.

Run inside atlas_test's counted main, like vanish_test and fetch_test. Each case plants the state the
writer grew into and kills the implementation that would have kept growing.
"""

from __future__ import annotations

import contextlib
import gzip
import io
import os
import tempfile
import time
from pathlib import Path


def _releases(atlas_cli, cache: Path) -> list[str]:
    """Five locked release trees, oldest first, plus one unmarked: only the newest KEPT_RELEASES stay."""
    for i in range(5):
        tree = cache / f"atlas-1.0.{i}"
        (tree / "scripts").mkdir(parents=True)
        (tree / atlas_cli.MARKER).write_text("x\n")
        os.utime(tree / atlas_cli.MARKER, (1000 + i, 1000 + i))
        (cache / "pycache" / str(tree).lstrip("/")).mkdir(parents=True)
    (cache / "atlas-unpacking").mkdir()  # no marker: an interrupted unpack is never counted as a release
    atlas_cli._prune_releases(cache)
    return sorted(p.name for p in cache.glob("atlas-*")) + sorted(p.name for p in (cache / "pycache").rglob("atlas-*"))


def _history(abtest, ledger: Path) -> tuple[int, int, int]:
    run = {"provider": "p", "model": "m", "questions": 1, "arms": {"scoped": {"correct": 1, "asked": 1}}}
    first = abtest.append_history(ledger, [run], "1.0.0")
    ledger.write_bytes(ledger.read_bytes() + b" " * abtest.HISTORY_MAX_BYTES)  # a history already at its cap
    size = ledger.stat().st_size
    with contextlib.redirect_stderr(io.StringIO()):
        second = abtest.append_history(ledger, [run], "1.0.1")
    return first, second, ledger.stat().st_size - size


def _months(agents, field: Path) -> tuple[list[str], list[str], bool]:
    field.mkdir(parents=True)
    names = [f"2025-{m:02d}.jsonl" for m in range(1, 13)] + ["2026-01.jsonl", "2026-02.jsonl"]
    for name in names:
        (field / name).write_text(f'{{"month": "{name}"}}\n')
    moved = agents.archive_months(field)
    whole = all(gzip.decompress(p.read_bytes()) == f'{{"month": "{p.name[:-3]}"}}\n'.encode() for p in moved)
    return sorted(p.name for p in field.glob("*.jsonl")), sorted(p.name for p in moved), whole


def _orphans(agents, home: str) -> list[str]:
    sessions = Path(home) / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for name, age in (("old.tmp", agents.KEEP_SECONDS + 60), ("fresh.tmp", 60)):
        (sessions / name).write_text("{}")
        os.utime(sessions / name, (now - age, now - age))
    saved = os.environ.get("HEADRON_HOME")
    os.environ["HEADRON_HOME"] = home
    try:
        agents.records(now)
    finally:
        if saved is None:
            del os.environ["HEADRON_HOME"]
        else:
            os.environ["HEADRON_HOME"] = saved
    return sorted(p.name for p in sessions.glob("*.tmp"))


def _footprint(doctor, root: Path) -> tuple[bool, bool, bool, bool]:
    """(clean, foreign, over, unbudgeted) verdicts of the doctor's state row on planted stores."""
    env = {"HEADRON_HOME": root / "headron", "XDG_CACHE_HOME": root / "xdg", "HEADRON_GITHUB_APP_STATE": root / "app"}
    (root / "headron" / "field").mkdir(parents=True)
    (root / "headron" / "field" / "2026-10.jsonl").write_bytes(b"x" * 100)
    budgets = {"headron_home": 1000, "release_cache": 1000, "github_app": 1000}
    saved = {name: os.environ.get(name) for name in env}
    os.environ.update({name: str(path) for name, path in env.items()})
    try:
        clean = doctor._state_row(budgets)["ok"]
        over = doctor._state_row({**budgets, "headron_home": 99})["ok"]
        unbudgeted = doctor._state_row({k: v for k, v in budgets.items() if k != "github_app"})["ok"]
        (root / "headron" / "field" / "sandbox.sqlite").write_bytes(b"")
        foreign = doctor._state_row(budgets)["ok"]
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    return clean, foreign, over, unbudgeted


def run(module) -> None:
    import abtest
    import agents
    import atlas_cli
    import doctor

    with tempfile.TemporaryDirectory(prefix="headron-bounds-") as tmp:
        root = Path(tmp)
        kept = _releases(atlas_cli, root / "cache")
        history = _history(abtest, root / "ab-history.jsonl")
        plain, archived, whole = _months(agents, root / "field")
        orphans = _orphans(agents, str(root / "home"))
        footprint = _footprint(doctor, root / "state")
    newest = [f"atlas-1.0.{i}" for i in (2, 3, 4)]
    cases = [
        (
            "the release cache keeps the newest KEPT_RELEASES locked trees and drops the bytecode; an unmarked one is left",
            "a cache that gained one atlas tree per upgrade and never lost one",
            kept == sorted([*newest, "atlas-unpacking"]),
            kept,
        ),
        (
            "a history append that would pass HISTORY_MAX_BYTES is refused whole; the file is never trimmed",
            "an ab-history.jsonl that grew one line per recorded run, forever",
            history == (1, 0, 0),
            history,
        ),
        (
            "field months beyond FIELD_MONTHS are gzipped aside, read back whole, and only then removed",
            "a field ledger capped per month but not in months: no total bound",
            len(plain) == agents.FIELD_MONTHS and archived == ["2025-01.jsonl.gz", "2025-02.jsonl.gz"] and whole,
            (plain, archived, whole),
        ),
        (
            "a session .tmp older than KEEP_SECONDS is swept when the registry is listed; a fresh one stays",
            "a writer killed between write and replace leaving a .tmp no reader ever removes",
            orphans == ["fresh.tmp"],
            orphans,
        ),
        (
            "the doctor's state row passes stores within budget and fails a foreign file, an overrun or no budget",
            "a footprint row that summed nothing, so another tool's 26.9 MB sqlite in field/ stayed unseen",
            footprint == (True, False, False, False),
            footprint,
        ),
    ]
    for name, kills, ok, got in cases:
        if not ok:
            raise SystemExit(f"FAIL {name}\n  got: {got!r}\n  kills: {kills}")
        module.CASES.append((name, kills))
        print(f"  ok    {name}")
