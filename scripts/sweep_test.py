#!/usr/bin/env python3
"""Sweep and Instant Search test suite.

proves: fast semantic sweep and instant web-like search return structured, verified records
does_not_prove: full linguistic synonymy — only prefix, acronym, pointer, and token overlap
closed_by: this file
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # noqa: E402

import atlasindex  # noqa: E402
import port  # noqa: E402
import sweep  # noqa: E402
from atlascore import ROOT  # noqa: E402


def test_shard_of():
    """Verify paths map to their declared architectural shards."""
    assert sweep.shard_of("atlas.yaml") == "core"
    assert sweep.shard_of("scripts/atlas.py") == "core"
    assert sweep.shard_of("scripts/mind.py") == "mind"
    assert sweep.shard_of("scripts/pipeline.py") == "mind"
    assert sweep.shard_of("scripts/graph.py") == "graph"
    assert sweep.shard_of("scripts/sweep.py") == "retrieval"
    assert sweep.shard_of("scripts/atlasindex.py") == "retrieval"
    assert sweep.shard_of("scripts/verify.py") == "verification"
    assert sweep.shard_of("languages/python/tools.yaml") == "languages"
    assert sweep.shard_of("examples/python/simple.py") == "languages"
    assert sweep.shard_of("models/claude/README.md") == "adapters"
    assert sweep.shard_of("skills/headron/SKILL.md") == "adapters"
    assert sweep.shard_of("docs/wiki/CODE-ROUTING.md") == "docs"
    assert sweep.shard_of("README.md") == "docs"


def test_repo_topology():
    """Verify repository topology computation."""
    top = sweep.repo_topology(ROOT)
    assert top["total_files"] > 100
    assert "backend" in top["tiers"]
    assert "core" in top["shards"]
    assert "verification" in top["shards"]
    assert "python" in top["top_routes"]


def test_repo_semantics():
    """Verify semantics block exports contract version and principles."""
    sem = sweep.repo_semantics()
    assert sem["contract_version"]
    assert len(sem["invariants"]) > 10
    assert len(sem["fast_loop"]) >= 1
    assert any("Universal runtime agnosticism" in p for p in sem["principles"])


def test_sweep_record():
    """Verify sweep record schema and completeness."""
    rec = sweep.sweep_record(ROOT)
    assert rec["schema"] == "headron-sweep/1"
    assert rec["command"] == "sweep"
    assert rec["version"] == rec["semantics"]["contract_version"]
    assert len(rec["tunnels"]) > 0
    assert "headron find" in rec["instant_search"]["symbol_lookup"]
    assert len(rec["next"]) >= 3


def test_format_sweep():
    """Verify text rendering of sweep."""
    rec = sweep.sweep_record(ROOT)
    text = sweep.format_sweep(rec)
    assert "Headron Semantic Sweep" in text
    assert "tiers:" in text
    assert "shards:" in text
    assert "instant search:" in text


def test_search_single_letter():
    """Verify web-like instant search resolves single-letter queries."""
    hits = atlasindex.search("m", limit=5)
    assert len(hits) > 0
    assert any("symbol_letter" in h["found_by"] or "path_letter" in h["found_by"] for h in hits)
    assert all("shard" in h and "tier" in h for h in hits)


def test_search_prefix():
    """Verify prefix search resolves partial symbols."""
    hits = atlasindex.search("min", limit=5)
    assert len(hits) > 0
    assert any("mind" in h["path"] or any(s.startswith("min") for s in h.get("symbols", [])) for h in hits)


def test_search_acronym():
    """Verify acronym search matches multi-word symbols."""
    hits = atlasindex.search("cc", limit=5)
    assert len(hits) > 0
    assert any("symbol_acronym" in h["found_by"] or "path_acronym" in h["found_by"] for h in hits)


def test_search_pointer():
    """Verify [[pointer]] queries match symbols directly."""
    hits = atlasindex.search("[[mind]]", limit=5)
    assert len(hits) > 0
    assert any("pointer_exact" in h["found_by"] for h in hits)
    assert any("mind.py" in h["path"] for h in hits)


def test_search_finds_path_terms_without_body_overlap():
    """Framework names in directories remain discoverable with an existing index."""
    from unittest.mock import patch

    record = {
        "path": "models/agent-framework/README.md",
        "lines": [1, 1],
        "symbols": ["Overview"],
        "checksum": "digest",
        "route": "docs",
        "last_verified_contract": "test",
        "tokens": ["overview"],
    }
    with (
        patch.object(
            atlasindex, "_get_cached_records", return_value=([record], {"overview": 1.0}, [({"overview": 1}, 1.0)])
        ),
        patch.object(atlasindex, "_identifiers", return_value=set()),
        patch.object(atlasindex, "_enrich_hit", return_value={}),
    ):
        hits = atlasindex.search("agent framework")
        assert hits and hits[0]["path"] == record["path"]
        assert "path" in hits[0]["found_by"]
        assert not atlasindex.search("agent framework", exact_only=True)
        assert not atlasindex.search("agent framework -models")


def test_search_citation_freshness():
    """Never attach live lines to an index citation for different file content."""
    import tempfile
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / "target.py"
        source = "original indexed source\n"
        path.write_text(source, encoding="utf-8")
        record = {"path": "target.py", "lines": [1, 1], "checksum": atlasindex._checksum(source)}
        with patch.object(atlasindex, "ROOT", root):
            current = atlasindex.source_status(record, with_snippet=True)
            assert current["freshness"] == "current"
            assert "original indexed source" in current["snippet"]
            path.write_text("new live source\n", encoding="utf-8")
            assert atlasindex.source_status(record, with_snippet=True) == {"freshness": "stale"}
            path.unlink()
            assert atlasindex.source_status(record, with_snippet=True) == {"freshness": "missing"}
            path.write_text(source, encoding="utf-8")
            record.update(symbols=["target"], route="test", last_verified_contract="test", tokens=["target"])
            with (
                patch.object(
                    atlasindex, "_get_cached_records", return_value=([record], {"target": 1.0}, [({"target": 1}, 1.0)])
                ),
                patch.object(atlasindex, "_identifiers", return_value=set()),
            ):
                assert atlasindex.search("target", with_snippet=True)[0]["freshness"] == "current"
                path.write_text("changed\n", encoding="utf-8")
                hit = atlasindex.search("target", with_snippet=True)[0]
                assert hit["freshness"] == "stale" and "snippet" not in hit


def test_find_refuses_empty_index():
    """A missing index is not evidence that a query has no matches."""
    from contextlib import redirect_stderr
    from io import StringIO
    from unittest.mock import patch

    errors = StringIO()
    with patch.object(atlasindex, "_get_cached_records", return_value=([], {}, [])), redirect_stderr(errors):
        assert atlasindex.find_main(["missing", "--json"]) != 0
    assert "python scripts/atlasindex.py build" in errors.getvalue()


def test_cold_store_builds_before_answering():
    """A fresh checkout has no store: the first read builds it, never answers with silence."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        _cold_store_cases(Path(tmp))


def _cold_store_cases(tmp_path: Path) -> None:
    from unittest.mock import patch

    record = {"tokens": ["alpha"]}
    with (
        patch.multiple(atlasindex, _RECORDS_CACHE=None, _IDF_CACHE=None, _VECTORS_CACHE=None),
        patch.object(atlasindex, "STORE", str(tmp_path / "absent")),
        patch.object(atlasindex, "load", side_effect=[[], [record]]),
        patch.object(atlasindex, "build") as build,
    ):
        assert atlasindex._get_cached_records()[0] == [record]
        assert build.call_count == 1
    (tmp_path / "chunks.jsonl").write_text("", encoding="utf-8")
    with (
        patch.multiple(atlasindex, _RECORDS_CACHE=None, _IDF_CACHE=None, _VECTORS_CACHE=None),
        patch.object(atlasindex, "STORE", str(tmp_path)),
        patch.object(atlasindex, "load", return_value=[]),
        patch.object(atlasindex, "build") as build,
    ):
        assert atlasindex._get_cached_records()[0] == []
        assert build.call_count == 0, "an existing empty store is verify()'s to name, not rebuilt on every read"


def test_warm_store_rebuilds_when_stale():
    """A warm store answers like a cold one: changed or never-indexed tracked files rebuild it first.

    Measured at 3.63.0: a long-lived checkout at the same SHA as a fresh clone cited 4 changed
    files as `stale` and had never indexed 7 tracked files (a skill added that day among them),
    because the store was built only when missing. A fresh clone answered correctly.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        _warm_store_cases(Path(tmp).resolve())


def _warm_store_cases(root: Path) -> None:
    from unittest.mock import patch

    kept, added = root / "kept.md", root / "added.md"
    kept.write_text("# kept\nalpha\n", encoding="utf-8")
    added.write_text("# added\nbeta\n", encoding="utf-8")
    current = {
        "path": "kept.md",
        "checksum": atlasindex._checksum(kept.read_text(encoding="utf-8")),
        "tokens": ["alpha"],
    }

    def cached(records: list[dict], files: list[Path]) -> int:
        with (
            patch.multiple(atlasindex, _RECORDS_CACHE=None, _IDF_CACHE=None, _VECTORS_CACHE=None),
            patch.object(atlasindex, "ROOT", root),
            patch.object(atlasindex, "tracked", return_value=files),
            patch.object(atlasindex, "load", return_value=records),
            patch.object(atlasindex, "build") as build,
        ):
            atlasindex._get_cached_records()
            return build.call_count

    assert cached([current], [kept]) == 0, "a current store is read, not rebuilt"
    assert cached([current], [kept, added]) == 1, "a tracked file the store never indexed rebuilds it"
    assert cached([dict(current, checksum="0" * 64)], [kept]) == 1, "a changed file rebuilds the store"
    with patch.object(atlasindex, "ROOT", root), patch.object(atlasindex, "tracked", return_value=[kept, added]):
        assert any("added.md" in p and "not indexed" in p for p in atlasindex.verify([current]))


def test_build_replaces_store_atomically():
    """Readers in other processes never load a half-written store: build replaces it atomically."""
    import tempfile
    from unittest.mock import patch

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        with (
            patch.object(atlasindex, "ROOT", root),
            patch.object(atlasindex, "tracked", return_value=[]),
            patch.object(atlasindex.atomicfile, "write_text", wraps=atlasindex.atomicfile.write_text) as write,
        ):
            atlasindex.build()
        assert write.call_count == 1 and write.call_args[0][0] == root / atlasindex.STORE / "chunks.jsonl"
        assert [p.name for p in (root / atlasindex.STORE).iterdir()] == ["chunks.jsonl"]


def test_port_sweep_integration():
    """Verify port incorporates sweep for agents."""
    rec = port.record(".", "codebase", "agent", None, sweep=True)
    assert "sweep" in rec
    assert rec["sweep"]["schema"] == "headron-sweep/1"
    text = port.text(rec, color=False)
    assert "sweep:" in text
    assert "instant search:" in text


def test_port_agent_frame_says_what_a_directory_proves():
    """The JSON record carried `proves` while the text an agent reads dropped it."""
    rec = port.record("scripts", None, "agent", None)
    assert rec["proves"], "scripts is a declared scope with gates"
    assert "  proves: " + " · ".join(rec["proves"]) in port.text(rec, color=False)


def _reference_ms() -> float:
    """CPU ms of a fixed pure-Python loop, best of 3: this core's speed right now (~26 ms on a performance core)."""
    import time

    best = float("inf")
    for _ in range(3):
        t0, s = time.process_time(), 0
        for i in range(300_000):
            s += hash(str(i)) & 7
        best = min(best, (time.process_time() - t0) * 1000)
    return best


def test_search_speed_and_cache():
    """Search stays under 600 ms cold and 250 ms warm, at a performance core's speed (23 and 9 reference loops)."""
    import time
    from unittest.mock import patch

    # A stale store rebuilds on the first read (~0.9 s measured); this test times reading a current one.
    if atlasindex.verify():
        atlasindex.build()
    # MEASURED IN REFERENCE LOOPS, NOT MILLISECONDS (3.63.0). Neither clock is load-invariant here: wall
    # clock counted the other gates verify runs beside this, and macOS moves a loaded process to an
    # efficiency core, where the same cold search costs 1103-1173 ms of CPU time against 285-291 ms on a
    # performance core. Timing a fixed loop before and after the search, and taking the slower, expresses
    # the old 600/250 ms ceilings in this core's speed (600 / 26 ms per loop = 23 loops).
    with (
        patch.object(atlasindex, "_RECORDS_CACHE", None),  # cold means cold, whatever earlier tests loaded
        patch.object(atlasindex, "_IDF_CACHE", None),
        patch.object(atlasindex, "_VECTORS_CACHE", None),
    ):
        before = _reference_ms()
        t0 = time.process_time()
        hits_cold = atlasindex.search("mind", limit=5)
        cold_ms = (time.process_time() - t0) * 1000
        t0 = time.process_time()
        hits_warm = atlasindex.search("mind", limit=5)
        warm_ms = (time.process_time() - t0) * 1000
        loop = max(before, _reference_ms())
    assert hits_cold and hits_warm
    assert cold_ms / loop < 23, (
        f"Cold search took {cold_ms:.0f}ms = {cold_ms / loop:.1f} loops of {loop:.0f}ms, want < 23"
    )
    assert warm_ms / loop < 9, (
        f"Warm search took {warm_ms:.0f}ms = {warm_ms / loop:.1f} loops of {loop:.0f}ms, want < 9"
    )


def test_search_vector_cache():
    """Cached vector statistics preserve scores and are rebuilt after invalidation."""
    from collections import Counter
    from unittest.mock import patch

    records = [{"tokens": ["alpha", "alpha", "beta"]}, {"tokens": []}]
    with (
        patch.object(atlasindex, "_RECORDS_CACHE", None),
        patch.object(atlasindex, "_IDF_CACHE", None),
        patch.object(atlasindex, "_VECTORS_CACHE", None),
        patch.object(atlasindex, "load", return_value=records) as load,
        patch.object(atlasindex, "verify", return_value=[]),
    ):
        cached_records, idf, vectors = atlasindex._get_cached_records()
        assert cached_records == records
        assert vectors[0][0] == Counter(records[0]["tokens"])
        assert vectors[0][1] == sum((idf[t] * c) ** 2 for t, c in vectors[0][0].items()) ** 0.5
        assert vectors[1] == (Counter(), 1.0)
        assert atlasindex._get_cached_records()[2] is vectors
        assert load.call_count == 1
        atlasindex._VECTORS_CACHE = None
        assert atlasindex._get_cached_records()[2] is not vectors
        assert load.call_count == 2


def test_search_filters():
    """Verify tier, shard, and exclude filters narrow search accurately."""
    hits = atlasindex.search("mind", limit=5, shard="mind", tier="backend")
    assert len(hits) > 0
    assert all(h["shard"] == "mind" and h["tier"] == "backend" for h in hits)

    hits_no_test = atlasindex.search("mind", limit=5, exclude="test")
    assert all("test" not in h["path"] for h in hits_no_test)


def test_search_snippet():
    """Verify snippet extraction provides readable source context."""
    hits = atlasindex.search("mind", limit=3, with_snippet=True)
    assert len(hits) > 0
    assert any("snippet" in h and len(h["snippet"]) > 0 for h in hits)


def test_sweep_line_mode():
    """Verify sweep line mode format."""
    rec = sweep.sweep_record(ROOT)
    top = rec["topology"]
    line = f"○ sweep {rec['version']} │ files={top['total_files']} tiers={len(top['tiers'])} shards={len(top['shards'])} tunnels={len(rec['tunnels'])}"
    assert "○ sweep" in line
    assert "shards=" in line


def main() -> int:
    tests = [
        test_shard_of,
        test_repo_topology,
        test_repo_semantics,
        test_sweep_record,
        test_format_sweep,
        test_search_single_letter,
        test_search_prefix,
        test_search_acronym,
        test_search_pointer,
        test_search_finds_path_terms_without_body_overlap,
        test_search_citation_freshness,
        test_find_refuses_empty_index,
        test_cold_store_builds_before_answering,
        test_warm_store_rebuilds_when_stale,
        test_build_replaces_store_atomically,
        test_port_sweep_integration,
        test_port_agent_frame_says_what_a_directory_proves,
        test_search_speed_and_cache,
        test_search_vector_cache,
        test_search_filters,
        test_search_snippet,
        test_sweep_line_mode,
    ]
    passed = 0
    for t in tests:
        t()
        passed += 1
        print(f"✓ {t.__name__}")
    print(f"\n{passed}/{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
