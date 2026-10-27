#!/usr/bin/env python3
"""Fast semantic sweep: repo-wide understanding, sharding, joint embeddings, edges, pointers, tunnels.

WHY (3.60.0). When an agent or chat assistant plugs into Headron, reading files breadth-first violates
the core rule ('Never read this repository breadth-first. Ask where to go...'). A fast semantic
sweep generates an instantaneous, low-token mental map of the entire repository:
1. Repository topology and stack tiers (frontend -> middle -> backend -> database)
2. Architectural shards (core, mind, graph, retrieval, verification, adapters, languages, docs)
3. Active knowledge pointers and verified decision tunnels
4. Headron native semantics (contract version, invariants, fast loops, refusal policies)
5. Actionable instant navigation commands (find, port, gate, verify)

proves: the repository can be semantically surveyed in one pass without breadth-first traversal
does_not_prove: that individual files are syntactically valid (closed by own_enforcement)
closed_by: sweep_test.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import graph
from atlascore import atlas, ls_files, route_for, worktree

SHARD_RULES = (
    ("core", ("atlas.yaml", "scripts/atlascore.py", "scripts/atlas.py", "scripts/agreement.py", "scripts/slot.py")),
    (
        "mind",
        ("scripts/mind.py", "scripts/mind_test.py", "scripts/pipeline.py", "scripts/decide.py", "scripts/reflex.py"),
    ),
    ("graph", ("scripts/graph.py", "scripts/edges.py", "scripts/stategraph.py", "scripts/stategraph_test.py")),
    ("retrieval", ("scripts/atlasindex.py", "scripts/sweep.py", "scripts/sweep_test.py", ".agent/index")),
    (
        "verification",
        (
            "scripts/verify.py",
            "scripts/enforce.py",
            "scripts/astshape.py",
            "scripts/mdshape.py",
            "scripts/branchstate.py",
        ),
    ),
)


def shard_of(path: str) -> str:
    """The architectural shard a file belongs to, by prefix or explicit match."""
    rel = path.replace("\\", "/")
    for shard_name, patterns in SHARD_RULES:
        if any(rel == p or rel.startswith(p) for p in patterns):
            return shard_name
    if rel.startswith("languages/") or rel.startswith("examples/"):
        return "languages"
    if (
        rel.startswith("models/")
        or rel.startswith("skills/")
        or rel.startswith(".agent/")
        or rel.startswith(".githooks/")
    ):
        return "adapters"
    if rel.startswith("docs/") or rel.endswith(".md"):
        return "docs"
    if rel.startswith("scripts/"):
        return "verification"
    return "core"


def repo_topology(tree: Path) -> dict[str, Any]:
    """Tracked files partitioned by tier, shard, and language route."""
    import port  # noqa: PLC0415

    files = ls_files(tree)
    tiers = port.stack_tiers(tree)
    tier_counts = Counter(port.tier_of(f, tiers) for f in files)
    shard_counts = Counter(shard_of(f) for f in files)
    routes = Counter(r for r in map(route_for, files) if r)
    return {
        "total_files": len(files),
        "tiers": dict(tier_counts.most_common()),
        "shards": dict(shard_counts.most_common()),
        "top_routes": dict(routes.most_common(8)),
    }


def repo_semantics() -> dict[str, Any]:
    """Contract facts, invariants, fast loop gates, and universal operating principles."""
    data = atlas()
    inv = data.get("hard_invariants") or []
    vp = data.get("verification_policy") or {}
    return {
        "contract_version": str(data.get("version")),
        "invariants": list(inv),
        "fast_loop": list(vp.get("fast_loop") or []),
        "principles": [
            "Deterministic exit-code verification (never output scraping)",
            "Universal runtime agnosticism: no vendor lock-in or single-runtime privilege",
            "A skipped check is never a pass (SKIP != PASS)",
            "No unmeasured counts in prose (generated or measured by instruments)",
            "Zero calendar dates (contract version pinning only)",
        ],
    }


def repo_tunnels() -> list[dict[str, Any]]:
    """Verified operational and decision tunnels from the knowledge graph."""
    g = graph.get_graph()
    return [{"name": t.name, "path": t.path} for t in g.get_tunnels()]


def repo_pointers() -> list[dict[str, str]]:
    """Obsidian-style wiki-links and symbol pointers from the knowledge graph."""
    g = graph.get_graph()
    return [{"from": p.from_node, "to": p.to_node, "context": p.context} for p in g.pointers]


def sweep_record(tree: Path | None = None) -> dict[str, Any]:
    """The complete fast semantic sweep record."""
    target_tree = (tree or worktree()).resolve()
    top = repo_topology(target_tree)
    sem = repo_semantics()
    tunnels = repo_tunnels()
    pointers = repo_pointers()
    return {
        "schema": "headron-sweep/1",
        "command": "sweep",
        "version": sem["contract_version"],
        "target": str(target_tree),
        "topology": top,
        "semantics": sem,
        "tunnels": tunnels,
        "pointers": pointers,
        "instant_search": {
            "symbol_lookup": "headron find <letter|symbol|pointer>",
            "examples": ["headron find m", "headron find mind", "headron find cc", "headron find [[mind]]"],
        },
        "next": ["headron port .", "headron find <query>", "headron gate <file>", "headron verify"],
    }


def format_sweep(rec: dict[str, Any]) -> str:
    """Format the sweep record into compact high-density text."""
    top = rec["topology"]
    sem = rec["semantics"]
    lines = [
        f"○ Headron Semantic Sweep │ contract {rec['version']} │ {top['total_files']} files │ {len(top['shards'])} shards │ {len(rec['tunnels'])} tunnels",
        "  tiers: " + " · ".join(f"{k}: {v}" for k, v in top["tiers"].items() if k != "none"),
        "  shards: " + " · ".join(f"{k} ({v})" for k, v in top["shards"].items()),
        "  tunnels: " + " · ".join(t["name"] for t in rec["tunnels"][:6]),
        "  invariants: " + " · ".join(sem["invariants"][:5]) + f" (+{len(sem['invariants']) - 5} more)",
        "  instant search: " + rec["instant_search"]["symbol_lookup"] + " (e.g. 'headron find m', 'headron find cc')",
        "  next: " + " · ".join(rec["next"]),
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="headron sweep", description="Fast semantic sweep of the repository")
    parser.add_argument("target", nargs="?", default=".", help="target path or directory; defaults to repo root")
    parser.add_argument("--line", action="store_true", help="emit as a compact single glyph line")
    parser.add_argument("--json", action="store_true", help="emit as JSON record")
    args = parser.parse_args(argv)

    target_path = Path(args.target).resolve()
    target_tree = target_path if target_path.is_dir() else target_path.parent
    rec = sweep_record(target_tree)
    if args.json:
        print(json.dumps(rec, separators=(",", ":")))
    elif args.line:
        top = rec["topology"]
        print(
            f"○ sweep {rec['version']} │ files={top['total_files']} tiers={len(top['tiers'])} shards={len(top['shards'])} tunnels={len(rec['tunnels'])}"
        )
    else:
        print(format_sweep(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
