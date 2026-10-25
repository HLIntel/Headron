#!/usr/bin/env python3
"""State-graph encoder — a deterministic typed graph of the repository's Python code.

Each module, class and function is a node keyed by `path::qualname`, carrying the sha256 of its
source text. Edges are recorded facts only: `defines` (module to its top-level names), `imports`
(module to repository module it names) and `calls` (function to a function it names by a plain
call, resolved within its own module or through a repository import). Nothing is inferred from a
name alone, and output is sorted, so the same bytes always encode to the same graph.

proves: the graph holds exactly the declared nodes and recorded edges of the encoded Python files,
        and a file that does not parse is recorded under `errors`, never silently dropped
does_not_prove: that any invariant holds, or that a call target runs — only what the source says
closed_by: stategraph_test.py, which plants a cross-module call, an edit and a syntax error

    python scripts/stategraph.py                 # encode scripts/*.py, print JSON
    python scripts/stategraph.py --summary       # node and edge counts only
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

from atlascore import parsed_python, walked

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 1
MAX_BYTES = 1_000_000  # a larger file is recorded under errors, not parsed


def module_name(rel: str) -> str:
    """Dotted module name for a repository-relative .py path."""
    parts = Path(rel).with_suffix("").parts
    return ".".join(parts)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


Def = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef


def _functions(tree: ast.Module) -> list[tuple[str, Def, str]]:
    """Top-level functions and methods as (qualname, node, kind)."""
    out: list[tuple[str, Def, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((node.name, node, "function"))
        elif isinstance(node, ast.ClassDef):
            out.append((node.name, node, "class"))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append((f"{node.name}.{sub.name}", sub, "method"))
    return out


def _segment(text: str, node: Def) -> str:
    lines = text.splitlines()
    return "\n".join(lines[node.lineno - 1 : node.end_lineno])


def _module_edges(rel: str, tree: ast.Module, by_module: dict[str, str], edges: set[tuple[str, str, str]]) -> None:
    """Record the defines and imports edges of one module's top-level statements."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            edges.add((rel, f"{rel}::{node.name}", "defines"))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for mod_rel in _import_targets(node, rel, by_module):
                edges.add((rel, mod_rel, "imports"))


def _function_nodes(
    rel: str,
    tree: ast.Module,
    text: str,
    nodes: dict[str, dict],
    edges: set[tuple[str, str, str]],
    by_module: dict[str, str],
) -> None:
    """Record each function node and its calls to same-module or imported repository functions."""
    local = {qual for qual, _, _ in _functions(tree)}
    imported = _imported_names(tree, rel, by_module)
    for qual, fn, kind in _functions(tree):
        node_id = f"{rel}::{qual}"
        nodes[node_id] = {"kind": kind, "file": rel, "line": fn.lineno, "sha256": _digest(_segment(text, fn))}
        for sub in walked(fn):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                callee = sub.func.id
                if callee in local:
                    edges.add((node_id, f"{rel}::{callee}", "calls"))
                elif callee in imported:
                    edges.add((node_id, imported[callee], "calls"))


def _imported_names(tree: ast.Module, rel: str, by_module: dict[str, str]) -> dict[str, str]:
    """Local name -> repository node id, for each `from X import name` that resolves in the repository."""
    out: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            mod_rel = _resolve(node, rel, by_module)
            if mod_rel is not None:
                for alias in node.names:
                    out[alias.asname or alias.name] = f"{mod_rel}::{alias.name}"
    return out


def encode(files: dict[str, str]) -> dict:
    """Encode {repo-relative path: source text} into a state graph.

    Deterministic: same input mapping always yields the same dict.
    """
    nodes: dict[str, dict] = {}
    edges: set[tuple[str, str, str]] = set()
    errors: dict[str, str] = {}
    trees: dict[str, ast.Module] = {}
    by_module: dict[str, str] = {}

    for rel in sorted(files):
        text = files[rel]
        if len(text.encode("utf-8")) > MAX_BYTES:
            errors[rel] = "too large"
            continue
        tree = parsed_python(text, rel)
        if tree is None:
            errors[rel] = "does not parse"
            continue
        trees[rel] = tree
        by_module[module_name(rel)] = rel
        if rel.startswith("scripts/"):
            # scripts/ is on sys.path here, so `import beta` names scripts/beta.py
            by_module[module_name(rel.removeprefix("scripts/"))] = rel
        nodes[rel] = {"kind": "module", "file": rel, "line": 1, "sha256": _digest(text)}

    for rel in sorted(trees):
        _module_edges(rel, trees[rel], by_module, edges)
        _function_nodes(rel, trees[rel], files[rel], nodes, edges, by_module)

    return {
        "schema": SCHEMA,
        "nodes": {k: nodes[k] for k in sorted(nodes)},
        "edges": [{"from": a, "to": b, "kind": k} for a, b, k in sorted(edges)],
        "errors": {k: errors[k] for k in sorted(errors)},
    }


def _resolve(node: ast.ImportFrom, rel: str, by_module: dict[str, str]) -> str | None:
    """Repository file a `from X import ...` names, or None when X is outside the repository."""
    if node.level:
        base = Path(rel).parent
        for _ in range(node.level - 1):
            base = base.parent
        mod = ".".join([*base.parts, *(node.module or "").split(".")]).strip(".")
    else:
        mod = node.module or ""
    return by_module.get(mod)


def _import_targets(node: ast.Import | ast.ImportFrom, rel: str, by_module: dict[str, str]) -> list[str]:
    if isinstance(node, ast.Import):
        return [by_module[a.name] for a in node.names if a.name in by_module]
    target = _resolve(node, rel, by_module)
    return [target] if target is not None else []


def load_repo(root: Path = ROOT) -> dict[str, str]:
    """Read scripts/*.py under root as {repo-relative path: text}."""
    files: dict[str, str] = {}
    for path in sorted((root / "scripts").glob("*.py")):
        files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return files


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Print the deterministic state graph of scripts/*.py as JSON.")
    parser.add_argument("--summary", action="store_true", help="print node and edge counts only")
    args = parser.parse_args(argv)
    graph = encode(load_repo())
    if args.summary:
        print(
            json.dumps(
                {"nodes": len(graph["nodes"]), "edges": len(graph["edges"]), "errors": len(graph["errors"])},
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(graph, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
