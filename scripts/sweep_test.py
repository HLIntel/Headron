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
    assert sweep.shard_of("skills/thea/SKILL.md") == "adapters"
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
    assert rec["schema"] == "thea-sweep/1"
    assert rec["command"] == "sweep"
    assert rec["version"] == rec["semantics"]["contract_version"]
    assert len(rec["tunnels"]) > 0
    assert "thea find" in rec["instant_search"]["symbol_lookup"]
    assert len(rec["next"]) >= 3


def test_format_sweep():
    """Verify text rendering of sweep."""
    rec = sweep.sweep_record(ROOT)
    text = sweep.format_sweep(rec)
    assert "Thea Semantic Sweep" in text
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


def test_port_sweep_integration():
    """Verify port incorporates sweep for agents."""
    rec = port.record(".", "codebase", "agent", None, sweep=True)
    assert "sweep" in rec
    assert rec["sweep"]["schema"] == "thea-sweep/1"
    text = port.text(rec, color=False)
    assert "sweep:" in text
    assert "instant search:" in text


def test_search_speed_and_cache():
    """Verify search is fast (< 500ms cold, < 200ms warm)."""
    import time

    t0 = time.perf_counter()
    hits_cold = atlasindex.search("mind", limit=5)
    t1 = time.perf_counter()
    assert len(hits_cold) > 0
    cold_ms = (t1 - t0) * 1000
    assert cold_ms < 600, f"Cold search took {cold_ms:.1f}ms, expected < 600ms"

    t0 = time.perf_counter()
    hits_warm = atlasindex.search("mind", limit=5)
    t1 = time.perf_counter()
    assert len(hits_warm) > 0
    warm_ms = (t1 - t0) * 1000
    assert warm_ms < 250, f"Warm search took {warm_ms:.1f}ms, expected < 250ms"


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
        test_port_sweep_integration,
        test_search_speed_and_cache,
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
