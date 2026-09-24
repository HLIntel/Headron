#!/usr/bin/env python3
"""astshape — structural duplicates and code blobs, by AST rather than by text.

WHY BY AST AND NOT BY TEXT. Two functions can share no characters and be structurally identical:
rename the variables, reflow the lines, swap the docstring, and a text-based duplicate scanner sees
nothing. A generator — human or model — repeats a *shape* far more often than it repeats a string,
because the shape is what it learned. So this parses each function, ERASES every name, docstring
and literal value, and hashes what is left: control flow, nesting, and the order of operations.
Identical hashes are the same function written twice.

WHAT IT MEASURES, all three declared in atlas.yaml/code_shape so the numbers are not buried here:
  - DUPLICATE STRUCTURES — two functions with one canonical hash, above a minimum size so that
    two three-line guards are not reported as a finding. A cap of 0 means: import it, do not
    rewrite it.
  - BLOBS — a function longer than the declared line cap. The cap is a ratchet: it may only fall.
  - NESTING — depth beyond the declared maximum, which is where a reader loses the invariant.

SCOPE, AND IT IS NARROW ON PURPOSE: Python only, because the harness is the only code this
repository owns. The language packs declare their own authority — `ruff` here, `clippy` there —
and this instrument does not pretend to judge them. Its blind spot is closed by each pack's own
formatter and linter, named in its manifest.

  python scripts/astshape.py            # a table, and an exit code
  python scripts/astshape.py --json     # the same as a record
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlascore import atlas, rel  # noqa: E402


def canonical(node: ast.AST) -> str:
    """The structure of `node` with every name, literal and docstring erased.

    A name is replaced by its KIND (`load`, `store`, `attr`, `call`), not by a serial number, so
    renaming a variable cannot change the hash and neither can reordering unrelated parameters.
    """
    parts: list[str] = [type(node).__name__]
    for field, value in ast.iter_fields(node):
        if field in {"id", "arg", "attr", "name", "module", "asname"}:
            parts.append(f"{field}=·")            # a name is a rendering of intent, not structure
        elif isinstance(value, ast.AST):
            parts.append(f"{field}({canonical(value)})")
        elif isinstance(value, list):
            inner = [canonical(item) for item in value if isinstance(item, ast.AST)]
            parts.append(f"{field}[{','.join(inner)}]")
        elif isinstance(value, (str, bytes)):
            parts.append(f"{field}=<{type(value).__name__}>")   # a literal's VALUE is not structure
        elif value is not None and not isinstance(value, ast.AST):
            parts.append(f"{field}=<{type(value).__name__}>")
    return "|".join(parts)


def strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def depth(node: ast.AST, level: int = 0) -> int:
    nesting = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)
    deepest = level
    for child in ast.iter_child_nodes(node):
        step = level + 1 if isinstance(child, nesting) else level
        deepest = max(deepest, depth(child, step))
    return deepest


def functions(path: Path) -> list[dict]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = strip_docstring(list(node.body))
        if not body:
            continue
        shape = "|".join(canonical(statement) for statement in body)
        found.append({
            "file": rel(path), "name": node.name, "line": node.lineno,
            "lines": (node.end_lineno or node.lineno) - node.lineno + 1,
            "nodes": sum(1 for _ in ast.walk(node)),
            "depth": depth(node),
            "hash": hashlib.sha256(shape.encode()).hexdigest()[:12],
        })
    return found


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="astshape.py", description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="emit the findings as a record")
    args = parser.parse_args(argv)

    shape = atlas().get("code_shape") or {}
    max_lines = int(shape.get("max_function_lines", 60))
    max_depth = int(shape.get("max_nesting_depth", 4))
    min_nodes = int(shape.get("min_structural_nodes", 25))
    allowed = int(shape.get("allowed_duplicate_structures", 0))

    scanned = sorted(ROOT.glob("scripts/*.py")) + sorted(ROOT.glob("examples/**/*.py"))
    every: list[dict] = []
    for path in scanned:
        every.extend(functions(path))

    seen: dict[str, list[dict]] = {}
    for item in every:
        if item["nodes"] >= min_nodes:
            seen.setdefault(item["hash"], []).append(item)
    duplicates = [group for group in seen.values() if len(group) > 1]
    blobs = [f for f in every if f["lines"] > max_lines]
    deep = [f for f in every if f["depth"] > max_depth]

    findings = {"duplicate_structures": duplicates, "blobs": blobs, "over_nested": deep}
    if args.json:
        print(json.dumps({"schema": 1, "command": "astshape", "scanned_files": len(scanned),
                          "functions": len(every), "caps": shape, "findings": findings}, indent=2))
        return 1 if duplicates or blobs or deep else 0

    print(f"astshape — {len(every)} functions in {len(scanned)} Python files\n")
    for group in duplicates:
        where = ", ".join(f"{f['file']}:{f['line']} {f['name']}()" for f in group)
        print(f"DUPLICATE  one structure, {len(group)} copies: {where}")
        print("           erase the names and these are the same function — import one, delete the rest")
    for f in sorted(blobs, key=lambda f: -f["lines"]):
        print(f"BLOB       {f['file']}:{f['line']} {f['name']}() is {f['lines']} lines (cap {max_lines})")
    for f in sorted(deep, key=lambda f: -f["depth"]):
        print(f"NESTED     {f['file']}:{f['line']} {f['name']}() nests {f['depth']} deep (cap {max_depth})")

    largest = max(every, key=lambda f: f["lines"])
    deepest = max(every, key=lambda f: f["depth"])
    print(f"\ncaps: {max_lines} lines, depth {max_depth}, {allowed} duplicate structure(s) allowed, "
          f"compared above {min_nodes} AST nodes")
    print(f"worst on this tree: {largest['lines']} lines ({largest['file']}:{largest['line']} "
          f"{largest['name']}), depth {deepest['depth']} ({deepest['file']}:{deepest['line']} "
          f"{deepest['name']})")
    print(f"{len(duplicates)} duplicate structure(s), {len(blobs)} blob(s), {len(deep)} over-nested")
    print("SCOPE: Python only — the harness is the code this repository owns. Each language pack")
    print("       declares its own formatter and linter, and this instrument does not judge them.")
    return 1 if duplicates or blobs or deep else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
