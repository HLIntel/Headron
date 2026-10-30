#!/usr/bin/env python3
"""A retrieval index that obeys the policy this repository declares, instead of describing one.

WHY (2.16.0). `atlas.yaml/retrieval_policy` named AST chunking, hybrid search, checksum
invalidation and a citation rule, and nothing here implemented any of it — a declaration with no
artifact, which is the exact shape `never_shipped_arm` refuses elsewhere in this tree. This builds
it, with the same standard-library-only constraint as the rest of the harness.

WHAT "DENSE" MEANS HERE, STATED PRECISELY BECAUSE THE WORD IS USUALLY BORROWED. This uses TF-IDF
cosine over token vectors. It is a real vector method and it is NOT a neural embedding: it matches
VOCABULARY OVERLAP, not meaning, so a true paraphrase sharing no terms with the query is missed.
That gap is named rather than papered over — a consumer who needs semantic recall brings a model
and swaps the scorer, and `retrieval_policy/search` still requires two methods because the sparse
arm finds exact symbols the cosine arm buries and vice versa.

EVERY RESULT CARRIES ITS PATH, ITS LINE RANGE AND THE CHECKSUM IT WAS READ AT. An answer whose
source cannot be opened is an answer that cannot be checked, and a chunk whose file has since
changed is reported STALE rather than returned as current.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import sys
import threading
from collections import Counter
from pathlib import Path

from atlascore import ROOT, atlas, parsed_python, route_for, tracked

STORE = ".agent/index"
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")
# ZIPF-AWARE WEIGHTING (3.60.0). Code tokens follow Zipf's distribution: f(r) ∝ 1/r^α.
# High-frequency syntax tokens (def, class, import, return, if, for, while, etc.) carry near-zero
# semantic information. Rare tokens (domain-specific function names, custom types) carry
# disproportionately high semantic weight. This set of stop tokens is down-weighted by the Zipf factor.
ZIPF_STOP = frozenset(
    "def class import from return if else elif for while try except finally with as in not and or is "
    "True False None self NoneType pass break continue yield lambda global nonlocal assert raise del "
    "print len range str int float list dict set tuple type isinstance issubclass property staticmethod "
    "classmethod super __init__ __name__ __main__ __file__ __doc__ __all__ __import__ __future__ "
    "abstractmethod abstractmethod abc os sys re json pathlib math time typing cast Any Optional Union "
    "List Dict Tuple Set FrozenSet Callable Iterator Iterable Sequence Mapping MutableMapping "
    "AbstractSet Collection".split()
)
# The Zipf penalty: high-frequency tokens get this weight multiplier (0.1 = 10% of normal weight)
ZIPF_PENALTY = 0.1
# CONTEXTUAL CHUNKING (3.60.0). Anthropic technique: include surrounding context lines before each
# chunk so the embedding captures the semantic environment, not just the isolated function.
CONTEXT_LINES = 3


def policy() -> dict:
    return atlas().get("retrieval_policy") or {}


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def python_units(source: str) -> list[tuple[int, int, str]]:
    """(start, end, symbol) per top-level definition — the AST's boundaries, never a length.

    A module's imports and constants are one unit too: dropping them would make the index unable
    to answer "where is this configured", which is most of what anyone asks a codebase.
    """
    if (tree := parsed_python(source, "<index>")) is None:
        return []
    units: list[tuple[int, int, str]] = []
    preamble_end = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            units.append((node.lineno, node.end_lineno or node.lineno, node.name))
        else:
            preamble_end = max(preamble_end, node.end_lineno or 0)
    if preamble_end:
        units.insert(0, (1, preamble_end, "<module preamble>"))
    return units


def markdown_units(source: str) -> list[tuple[int, int, str]]:
    """One unit per heading. A heading IS the declared boundary of a document's unit of thought."""
    lines = source.splitlines()
    starts = [(i + 1, line.lstrip("# ").strip()) for i, line in enumerate(lines) if line.startswith("#")]
    if not starts:
        return [(1, len(lines), "<document>")] if lines else []
    units = []
    for index, (line_no, title) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        units.append((line_no, end, title))
    return units


def units_for(path: Path, source: str) -> tuple[list[tuple[int, int, str]], str]:
    """The declared boundaries for one file, and WHICH rule produced them.

    A suffix with no declared splitter yields ONE unit for the whole file — never a length-based
    split, which is what `retrieval_policy/never_chunk_by` forbids. A whole file is a truthful
    unit; half a function is not.
    """
    if path.suffix == ".py":
        return python_units(source), "ast_boundaries/python"
    if path.suffix.lower() == ".md":
        return markdown_units(source), "ast_boundaries/markdown_headings"
    return ([(1, len(source.splitlines()) or 1, path.name)], "whole_file")


def build() -> dict:
    """Chunk every tracked text file on a declared boundary and write one sidecar per chunk."""
    global _RECORDS_CACHE, _IDF_CACHE, _VECTORS_CACHE
    fields = [str(f) for f in policy().get("sidecar_fields") or []]
    version = str(atlas().get("version"))
    records: list[dict] = []
    # WHAT IT DID NOT INDEX, BY SUFFIX. The first version skipped every suffix it could not chunk
    # and said nothing, so `1156 chunks` read as coverage of the tree when it covered eight
    # suffixes. A roster that narrows silently is the shape this repository refuses everywhere
    # else, and an index is a roster of what a reader can be told about.
    skipped: dict[str, int] = {}
    for path in tracked():
        if path.is_symlink() or not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".md", ".yaml", ".yml", ".json", ".txt", ".toml", ".sh"}:
            skipped[path.suffix.lower() or "(no suffix)"] = skipped.get(path.suffix.lower() or "(no suffix)", 0) + 1
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        digest = _checksum(source)
        lines = source.splitlines()
        units, rule = units_for(path, source)
        rel_path = path.resolve().relative_to(ROOT.resolve()).as_posix()
        for start, end, symbol in units:
            body = "\n".join(lines[start - 1 : end])
            # CONTEXTUAL CHUNKING: include surrounding context lines so the index captures
            # the semantic environment, not just the isolated function. This reduces failed
            # retrievals by giving each chunk explanatory context (Anthropic technique).
            ctx_start = max(1, start - CONTEXT_LINES)
            ctx_end = min(len(lines), end + CONTEXT_LINES)
            ctx_body = "\n".join(lines[ctx_start - 1 : ctx_end])
            # Tokens include both the chunk body and its context for better retrieval
            all_tokens = TOKEN.findall(body) + TOKEN.findall(ctx_body)
            records.append(
                {
                    "path": rel_path,
                    "checksum": digest,
                    "symbols": [symbol],
                    "route": route_for(rel_path),
                    "class": "unstructured",
                    "last_verified_contract": version,
                    "lines": [start, end],
                    "boundary_rule": rule,
                    "tokens": [t.lower() for t in all_tokens],
                }
            )
    missing = [f for f in fields if records and f not in records[0]]
    store = ROOT / STORE
    store.mkdir(parents=True, exist_ok=True)
    with _CACHE_LOCK:
        (store / "chunks.jsonl").write_text(
            "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in records), encoding="utf-8"
        )
        _RECORDS_CACHE = None
        _IDF_CACHE = None
        _VECTORS_CACHE = None
    return {
        "chunks": len(records),
        "files": len({r["path"] for r in records}),
        "missing_sidecar_fields": missing,
        "skipped_by_suffix": dict(sorted(skipped.items())),
    }


def load() -> list[dict]:
    path = ROOT / STORE / "chunks.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _idf(records: list[dict]) -> dict[str, float]:
    """TF-IDF with Zipf-aware weighting: high-frequency syntax tokens get penalized.

    Code tokens follow Zipf's distribution (f(r) ∝ 1/r^α). A token that appears in nearly every
    chunk (def, class, import, return) has low discriminative power. The Zipf penalty multiplies
    its IDF score down, so rare domain-specific tokens dominate the ranking.
    """
    seen: Counter[str] = Counter()
    for record in records:
        seen.update(set(record["tokens"]))
    total = len(records) or 1
    idf_base = {term: math.log(total / (1 + count)) + 1.0 for term, count in seen.items()}
    # Apply Zipf penalty: tokens in ZIPF_STOP get reduced weight
    return {term: weight * ZIPF_PENALTY if term in ZIPF_STOP else weight for term, weight in idf_base.items()}


def _identifiers() -> set[str]:
    a = atlas()
    return {
        str(k).lower()
        for block in ("gate_tools", "agent_failure_modes", "processes", "task_profiles")
        for k in (a.get(block) or {})
    }


_RECORDS_CACHE: list[dict] | None = None
_IDF_CACHE: dict[str, float] | None = None
_VECTORS_CACHE: list[tuple[Counter[str], float]] | None = None
_CACHE_LOCK = threading.RLock()  # reentrant: a cold cache builds the store, and build() takes this lock too
_TIER_CACHE: dict[str, str] = {}
_SHARD_CACHE: dict[str, str] = {}


def _get_cached_records() -> tuple[list[dict], dict[str, float], list[tuple[Counter[str], float]]]:
    global _RECORDS_CACHE, _IDF_CACHE, _VECTORS_CACHE
    with _CACHE_LOCK:
        if _RECORDS_CACHE is None or _IDF_CACHE is None or _VECTORS_CACHE is None:
            records = load()
            if not records and not (ROOT / STORE / "chunks.jsonl").exists():
                # A missing store is a fresh checkout, not a repo with no matches: build it rather than
                # answer every query with silence. An empty store that exists is left to verify() to name.
                build()
                records = load()
            idf = _idf(records)
            vectors = []
            for record in records:
                counts = Counter(record["tokens"])
                norm = math.sqrt(sum((idf.get(t, 0.0) * c) ** 2 for t, c in counts.items())) or 1.0
                vectors.append((counts, norm))
            _RECORDS_CACHE, _IDF_CACHE, _VECTORS_CACHE = records, idf, vectors
        return _RECORDS_CACHE, _IDF_CACHE, _VECTORS_CACHE


def snippet_for(rel_path: str, lines: list[int], max_lines: int = 3) -> str:
    path = ROOT / rel_path
    if not path.is_file():
        return ""
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, lines[0])
        end = min(len(content), lines[1], start + max_lines - 1)
        return "\n".join(f"{i:>4} | {content[i - 1]}" for i in range(start, end + 1))
    except OSError:
        return ""


def _acronym(symbol: str) -> str:
    """Generate acronym for snake_case or camelCase symbol."""
    if "_" in symbol:
        return "".join(part[0].lower() for part in symbol.split("_") if part)
    letters = [ch.lower() for ch in symbol if ch.isupper()]
    return "".join(letters) if letters else symbol[:2].lower()


def _symbol_match_score(query: str, symbols: list[str], path: str) -> tuple[float, str]:
    """Score symbol overlap: exact, pointer, prefix, acronym, or single-letter match."""
    q = query.lower()
    fname = Path(path).stem.lower()
    if any(q == s.lower() for s in symbols) or q == fname:
        return 3.0, "symbol_exact"
    if q.startswith("[[") and q.endswith("]]"):
        inner = q[2:-2].strip().lower()
        if any(inner == s.lower() for s in symbols) or inner == fname:
            return 3.5, "pointer_exact"
    if len(q) == 1:
        if any(s.lower().startswith(q) for s in symbols):
            return 2.0, "symbol_letter"
        if fname.startswith(q):
            return 1.5, "path_letter"
        return 0.0, "none"
    for s in symbols:
        if s.lower().startswith(q):
            return round(2.0 + (len(q) / max(len(s), 1)), 4), "symbol_prefix"
    if fname.startswith(q):
        return round(1.5 + (len(q) / max(len(fname), 1)), 4), "path_prefix"
    for s in symbols:
        if len(q) >= 2 and _acronym(s) == q:
            return 2.5, "symbol_acronym"
    if len(q) >= 2 and _acronym(fname) == q:
        return 2.2, "path_acronym"
    return 0.0, "none"


def _enrich_hit(record: dict, with_snippet: bool = False) -> dict:
    """Enrich a search hit with stack tier, shard, and knowledge graph edges/tunnels."""
    import graph  # noqa: PLC0415
    import port  # noqa: PLC0415
    import sweep  # noqa: PLC0415

    path = record["path"]
    symbols = record.get("symbols") or []
    fname = Path(path).stem
    g = graph.get_graph()

    matched_nodes = [node_id for s in [fname, *symbols] if (node_id := s.lower()) in g.nodes]
    pointers = [p.to_node for p in g.pointers if p.from_node in matched_nodes]
    edges = [f"{e.type.value} → {e.target}" for e in g.edges if e.source in matched_nodes]
    tunnels = [t.name for t in g.tunnels if any(n in t.path for n in matched_nodes)]

    if path not in _TIER_CACHE:
        _TIER_CACHE[path] = port.tier_of(path)
    if path not in _SHARD_CACHE:
        _SHARD_CACHE[path] = sweep.shard_of(path)

    res = {
        "tier": _TIER_CACHE[path],
        "shard": _SHARD_CACHE[path],
        "pointers": sorted(set(pointers)),
        "edges": sorted(set(edges)),
        "tunnels": sorted(set(tunnels)),
    }
    if with_snippet:
        res["snippet"] = snippet_for(path, record.get("lines") or [1, 1])
    return res


def search(
    query: str,
    limit: int = 5,
    path_filter: str | None = None,
    tier: str | None = None,
    shard: str | None = None,
    exclude: str | None = None,
    exact_only: bool = False,
    with_snippet: bool = False,
) -> list[dict]:
    """Hybrid instant search: TF-IDF cosine, exact symbol, prefix, acronym, pointers and tunnels.

    Combines dense TF-IDF vocabulary overlap with instant symbol/prefix/acronym matching, and
    enriches top candidates with architectural shards, stack tiers, and knowledge graph tunnels.
    """
    records, idf, vectors = _get_cached_records()
    if not records:
        return []

    raw_terms = query.strip().split()
    negatives = [w[1:].lower() for w in raw_terms if w.startswith("-") and len(w) > 1]
    if exclude:
        negatives.append(exclude.lower())
    pos_terms = [w for w in raw_terms if not w.startswith("-")]
    cleaned_query = " ".join(pos_terms)

    terms = [t.lower() for t in TOKEN.findall(cleaned_query)]
    q_weights = {t: idf.get(t, 0.0) for t in set(terms)}
    for name in {n for t in set(terms) if len(t) > 3 for n in _identifiers() if t in n} - set(q_weights):
        q_weights[name] = 0.5 * idf.get(name, 0.0)
    q_norm = math.sqrt(sum(w * w for w in q_weights.values())) or 1.0

    scored: list[tuple[float, str, dict]] = []
    q_stripped = cleaned_query.strip()
    for record, (counts, norm) in zip(records, vectors, strict=True):
        rec_path = record["path"]
        rec_symbols = record.get("symbols") or []

        if negatives and any(
            neg in rec_path.lower() or any(neg in s.lower() for s in rec_symbols) for neg in negatives
        ):
            continue
        if path_filter and path_filter.lower() not in rec_path.lower():
            continue

        sym_score, sym_found = _symbol_match_score(q_stripped, rec_symbols, rec_path)
        if exact_only and sym_found not in ("symbol_exact", "pointer_exact"):
            continue

        dot = sum(q_weights.get(t, 0.0) * idf.get(t, 0.0) * counts.get(t, 0) for t in q_weights)
        cosine = (dot / (q_norm * norm)) if (q_norm and norm) else 0.0
        exact = sum(1 for t in set(terms) if t in {s.lower() for s in rec_symbols})

        prominence = 1.0 if rec_symbols and rec_symbols[0] not in ("<module preamble>", "<document>") else 0.7
        path_terms = set(re.findall(r"[a-z0-9]+", rec_path.lower()))
        matched_path = {t for t in terms if len(t) > 1 and t in path_terms}
        path_score = 0.5 * len(matched_path) / len(set(terms)) if terms else 0.0
        total_score = round((cosine + exact + sym_score + path_score) * prominence, 6)
        if total_score <= 0:
            continue

        if tier or shard:
            import port  # noqa: PLC0415
            import sweep  # noqa: PLC0415

            if rec_path not in _TIER_CACHE:
                _TIER_CACHE[rec_path] = port.tier_of(rec_path)
            if rec_path not in _SHARD_CACHE:
                _SHARD_CACHE[rec_path] = sweep.shard_of(rec_path)
            if tier and _TIER_CACHE[rec_path] != tier:
                continue
            if shard and _SHARD_CACHE[rec_path] != shard:
                continue

        found_by = (
            f"{sym_found}+cosine"
            if sym_score > 0 and cosine > 0
            else sym_found
            if sym_score > 0
            else "symbol+cosine"
            if exact and cosine > 0
            else "symbol"
            if exact
            else "cosine"
        )
        if path_score:
            found_by = f"{found_by}+path" if found_by != "cosine" or cosine else "path"
        scored.append((total_score, found_by, record))

    scored.sort(key=lambda item: (-item[0], item[2]["path"], item[2]["lines"][0]))
    top_candidates = scored[:limit]

    results = []
    for score_val, found_by_str, rec in top_candidates:
        enrichment = _enrich_hit(rec, with_snippet=with_snippet)
        results.append(
            {
                **{k: rec[k] for k in ("path", "lines", "symbols", "checksum", "route", "last_verified_contract")},
                **enrichment,
                "score": score_val,
                "found_by": found_by_str,
            }
        )
    return results


def verify() -> list[str]:
    """Invalidation by CONTENT. A chunk whose file no longer hashes the same is STALE, not current.

    Modification time is refused by `retrieval_policy/never_invalidate_by` for a measured reason: a
    checkout, a clone and a format-on-save all move it without changing a byte.
    """
    problems: list[str] = []
    records = load()
    if not records:
        return [
            "the index is empty — `atlas index build` first; an empty index answers every "
            "question with silence, which reads exactly like a question with no answer"
        ]
    digests: dict[str, str] = {}
    for record in records:
        path = ROOT / str(record["path"])
        if not path.exists():
            problems.append(f"{record['path']} is indexed and no longer in the tree")
            continue
        if record["path"] not in digests:
            digests[record["path"]] = _checksum(path.read_text(encoding="utf-8", errors="replace"))
        if digests[record["path"]] != record["checksum"]:
            problems.append(f"{record['path']} changed since it was indexed (STALE, not current)")
    return sorted(set(problems))


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="atlasindex.py")
    parser.add_argument("command", choices=("build", "search", "verify", "check"))
    parser.add_argument("query", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    if args.command == "build":
        state = build()
        print(f"indexed {state['chunks']} chunks over {state['files']} files, split on declared boundaries only")
        gap = state["skipped_by_suffix"]
        print(
            f"NOT indexed: {sum(gap.values())} tracked files across {len(gap)} suffixes this "
            f"index cannot chunk on a declared boundary — " + (", ".join(f"{k}x{v}" for k, v in gap.items()) or "none")
        )
        print("  a binary or a format with no declared splitter is REPORTED, never chunked by")
        print("  length: half a document retrieves as a confident fragment of something that was")
        print("  never true on its own. Closing one means declaring its boundary rule first.")
        if state["missing_sidecar_fields"]:
            print(f"- sidecar fields declared and not written: {state['missing_sidecar_fields']}")
            return 1
        return 0
    if args.command in ("verify", "check"):
        if args.command == "check":
            # ONE GATE, NOT TWO: readers run concurrently, so a separate build gate raced verify and found an empty index.
            build()
        problems = verify()
        for problem in problems:
            print(f"- {problem}")
        print(
            f"index: {len(load())} chunks, {len(problems)} stale or missing — invalidated by "
            "content, never by a modification time"
        )
        return 1 if problems else 0
    for hit in search(" ".join(args.query), args.limit):
        extra = f" ({hit.get('shard')}/{hit.get('tier')})" if hit.get("shard") else ""
        print(
            f"{hit['score']:>8.4f} [{hit['found_by']:<16}] {hit['path']}:"
            f"{hit['lines'][0]}-{hit['lines'][1]}  {', '.join(hit['symbols'])}{extra}"
        )
        print(f"{'':>8}  cite: {hit['path']}@{hit['checksum'][:12]} (contract {hit['last_verified_contract']})")
        if hit.get("tunnels"):
            print(f"{'':>8}  tunnels: {' · '.join(hit['tunnels'][:3])}")
        if hit.get("pointers"):
            print(f"{'':>8}  pointers: {' · '.join(hit['pointers'][:3])}")
    print("SCOPE: vocabulary overlap, not meaning. A paraphrase sharing no terms with the query is")
    print("       missed; bring a model and swap the scorer if you need semantic recall.")
    return 0


def find_main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="headron find", description="Instant web-like autonomous search")
    parser.add_argument("query", nargs="+", help="search query, symbol, abbreviation, or single letter")
    parser.add_argument("--limit", type=int, default=5, help="max hits to return")
    parser.add_argument(
        "--tier",
        default=None,
        choices=("frontend", "middle-frontend", "middle", "middle-backend", "backend", "database"),
        help="filter by stack tier",
    )
    parser.add_argument(
        "--shard",
        default=None,
        choices=("core", "mind", "graph", "retrieval", "verification", "languages", "adapters", "docs"),
        help="filter by architectural shard",
    )
    parser.add_argument("--path", default=None, help="filter by path substring")
    parser.add_argument("--exclude", default=None, help="exclude paths or symbols matching term")
    parser.add_argument("--exact", action="store_true", help="match exact symbols only")
    parser.add_argument("--snippet", action="store_true", help="display inline code snippet preview")
    parser.add_argument("--line", action="store_true", help="emit compact single-line per hit")
    parser.add_argument("--json", action="store_true", help="emit as JSON record")
    args = parser.parse_args(argv)

    if not _get_cached_records()[0]:
        print("search index is empty; run `python scripts/atlasindex.py build` first", file=sys.stderr)
        return 1
    q = " ".join(args.query)
    hits = search(
        q,
        limit=args.limit,
        path_filter=args.path,
        tier=args.tier,
        shard=args.shard,
        exclude=args.exclude,
        exact_only=args.exact,
        with_snippet=args.snippet,
    )
    if args.json:
        record = {"schema": "headron-find/1", "command": "find", "query": q, "count": len(hits), "hits": hits}
        print(json.dumps(record, separators=(",", ":")))
        return 0
    if args.line:
        for h in hits:
            syms = ",".join(h.get("symbols") or [])
            print(
                f"{h['path']}:{h['lines'][0]}-{h['lines'][1]} [{h.get('shard')}/{h.get('tier')}] score={h['score']:.4f} symbols={syms} cite={h['checksum'][:12]}"
            )
        return 0
    for hit in hits:
        extra = f" [{hit.get('shard')}/{hit.get('tier')}]" if hit.get("shard") else ""
        print(
            f"{hit['score']:>8.4f} [{hit['found_by']:<16}] {hit['path']}:"
            f"{hit['lines'][0]}-{hit['lines'][1]}  {', '.join(hit['symbols'])}{extra}"
        )
        print(f"{'':>8}  cite: {hit['path']}@{hit['checksum'][:12]} (contract {hit['last_verified_contract']})")
        if hit.get("tunnels"):
            print(f"{'':>8}  tunnels: {' · '.join(hit['tunnels'][:3])}")
        if hit.get("pointers"):
            print(f"{'':>8}  pointers: {' · '.join(hit['pointers'][:3])}")
        if hit.get("snippet"):
            print(f"{'':>8}  snippet:")
            for s_line in hit["snippet"].splitlines():
                print(f"{'':>10}  {s_line}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
