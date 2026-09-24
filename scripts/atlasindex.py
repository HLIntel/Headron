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
from collections import Counter
from pathlib import Path

from atlascore import ROOT, atlas, route_for, tracked

STORE = ".agent/index"
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")


def policy() -> dict:
    return atlas().get("retrieval_policy") or {}


def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def python_units(source: str) -> list[tuple[int, int, str]]:
    """(start, end, symbol) per top-level definition — the AST's boundaries, never a length.

    A module's imports and constants are one unit too: dropping them would make the index unable
    to answer "where is this configured", which is most of what anyone asks a codebase.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
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
    starts = [(i + 1, line.lstrip("# ").strip())
              for i, line in enumerate(lines) if line.startswith("#")]
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
            body = "\n".join(lines[start - 1:end])
            records.append({
                "path": rel_path, "checksum": digest, "symbols": [symbol],
                "route": route_for(rel_path), "class": "unstructured",
                "last_verified_contract": version,
                "lines": [start, end], "boundary_rule": rule,
                "tokens": [t.lower() for t in TOKEN.findall(body)],
            })
    missing = [f for f in fields if records and f not in records[0]]
    store = ROOT / STORE
    store.mkdir(parents=True, exist_ok=True)
    (store / "chunks.jsonl").write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in records), encoding="utf-8")
    return {"chunks": len(records), "files": len({r["path"] for r in records}),
            "missing_sidecar_fields": missing, "skipped_by_suffix": dict(sorted(skipped.items()))}


def load() -> list[dict]:
    path = ROOT / STORE / "chunks.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _idf(records: list[dict]) -> dict[str, float]:
    seen: Counter[str] = Counter()
    for record in records:
        seen.update(set(record["tokens"]))
    total = len(records) or 1
    return {term: math.log(total / (1 + count)) + 1.0 for term, count in seen.items()}


def search(query: str, limit: int = 5) -> list[dict]:
    """Hybrid: TF-IDF cosine for overlap, exact-token for symbols. Neither alone is enough.

    The two arms disagree on purpose. Cosine buries a rare exact symbol under documents that
    mention it in passing; exact-token cannot rank at all. The fused score keeps both, and each
    result reports which arm found it so a reader can tell a name match from a topical one.
    """
    records = load()
    if not records:
        return []
    idf = _idf(records)
    terms = [t.lower() for t in TOKEN.findall(query)]
    q_weights = {t: idf.get(t, 0.0) for t in set(terms)}
    q_norm = math.sqrt(sum(w * w for w in q_weights.values())) or 1.0
    scored: list[dict] = []
    for record in records:
        counts = Counter(record["tokens"])
        norm = math.sqrt(sum((idf.get(t, 0.0) * c) ** 2 for t, c in counts.items())) or 1.0
        dot = sum(q_weights.get(t, 0.0) * idf.get(t, 0.0) * counts.get(t, 0) for t in q_weights)
        cosine = dot / (q_norm * norm)
        exact = sum(1 for t in set(terms) if t in {s.lower() for s in record["symbols"]})
        if cosine <= 0 and not exact:
            continue
        scored.append({**{k: record[k] for k in
                          ("path", "lines", "symbols", "checksum", "route", "last_verified_contract")},
                       "score": round(cosine + exact, 6),
                       "found_by": "symbol+cosine" if exact and cosine > 0 else
                                   "symbol" if exact else "cosine"})
    scored.sort(key=lambda r: (-r["score"], r["path"], r["lines"][0]))
    return scored[:limit]


def verify() -> list[str]:
    """Invalidation by CONTENT. A chunk whose file no longer hashes the same is STALE, not current.

    Modification time is refused by `retrieval_policy/never_invalidate_by` for a measured reason: a
    checkout, a clone and a format-on-save all move it without changing a byte.
    """
    problems: list[str] = []
    records = load()
    if not records:
        return ["the index is empty — `atlas index build` first; an empty index answers every "
                "question with silence, which reads exactly like a question with no answer"]
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
    parser.add_argument("command", choices=("build", "search", "verify"))
    parser.add_argument("query", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    if args.command == "build":
        state = build()
        print(f"indexed {state['chunks']} chunks over {state['files']} files, "
              f"split on declared boundaries only")
        gap = state["skipped_by_suffix"]
        print(f"NOT indexed: {sum(gap.values())} tracked files across {len(gap)} suffixes this "
              f"index cannot chunk on a declared boundary — "
              + (", ".join(f"{k}x{v}" for k, v in gap.items()) or "none") )
        print("  a binary or a format with no declared splitter is REPORTED, never chunked by")
        print("  length: half a document retrieves as a confident fragment of something that was")
        print("  never true on its own. Closing one means declaring its boundary rule first.")
        if state["missing_sidecar_fields"]:
            print(f"- sidecar fields declared and not written: {state['missing_sidecar_fields']}")
            return 1
        return 0
    if args.command == "verify":
        problems = verify()
        for problem in problems:
            print(f"- {problem}")
        print(f"index: {len(load())} chunks, {len(problems)} stale or missing — invalidated by "
              "content, never by a modification time")
        return 1 if problems else 0
    for hit in search(" ".join(args.query), args.limit):
        print(f"{hit['score']:>8.4f} [{hit['found_by']:<14}] {hit['path']}:"
              f"{hit['lines'][0]}-{hit['lines'][1]}  {', '.join(hit['symbols'])}")
        print(f"{'':>8}  cite: {hit['path']}@{hit['checksum'][:12]} (contract {hit['last_verified_contract']})")
    print("SCOPE: vocabulary overlap, not meaning. A paraphrase sharing no terms with the query is")
    print("       missed; bring a model and swap the scorer if you need semantic recall.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
