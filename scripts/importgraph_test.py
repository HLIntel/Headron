#!/usr/bin/env python3
"""importgraph: one statement's imports, the edges of a planted tree, and a map that refuses to drift."""

from __future__ import annotations

import ast
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import atlas
import atlasgen
import importgraph


def _tree(root: Path, **modules: str) -> Path:
    (root / "scripts").mkdir()
    for name, source in modules.items():
        (root / "scripts" / f"{name}.py").write_text(source, encoding="utf-8")
    return root


def statement_case() -> None:
    tree = ast.parse("import a.b, c\nfrom d.e import f\nfrom .g import h\nfrom . import i\nx = 1\n")
    plain = [importgraph.statement_imports(node) for node in tree.body]
    if plain != [["a.b", "c"], ["d.e"], [], [], []]:
        raise SystemExit(f"FAIL one statement read wrong: {plain}")
    relative = [importgraph.statement_imports(node, relative=True) for node in tree.body]
    if relative != [["a.b", "c"], ["d.e"], ["g"], [], []]:
        raise SystemExit(f"FAIL a relative import asked for and read wrong: {relative}")
    print("  ok    a relative import counts only when the caller asks")


def lazy_case() -> None:
    tree = ast.parse("def f():\n    import lazy\n    from .near import x\n")
    if importgraph.imported_names(tree) != {"lazy"}:
        raise SystemExit(f"FAIL a lazy import was missed: {importgraph.imported_names(tree)}")
    if importgraph.imported_names(tree, relative=True) != {"lazy", "near"}:
        raise SystemExit("FAIL relative=True did not reach a lazy relative import")
    print("  ok    an import inside a function is read")


def network_case() -> None:
    tree = ast.parse("import urllib.request\nimport urllib.parse\nimport socketserver\nfrom .socket import x\n")
    if importgraph.network_libraries(tree) != ("socket", "urllib.request"):
        raise SystemExit(f"FAIL network reading wrong: {importgraph.network_libraries(tree)}")
    print("  ok    a network library is named exactly, and a lookalike is not")


def edges_case(directory: Path) -> None:
    root = _tree(
        directory,
        a="import b\nimport os\nimport a\nfrom .c import x\ndef f():\n    from d.sub import y\n",
        b="",
        c="",
        d="",
        broken="def (:\n",
    )
    graph = importgraph.sibling_graph(root)
    if graph["a"] != {"b", "d"}:
        raise SystemExit(f"FAIL edges of a planted module: {graph['a']}")
    if graph["broken"] != set():
        raise SystemExit(f"FAIL an unparsed file grew edges: {graph['broken']}")
    print("  ok    edges are siblings only: no self, no standard library, no relative name")


def map_case(directory: Path) -> None:
    root = _tree(
        directory,
        hub='"""The hub. More after it."""\n',
        one="import hub\n",
        two="import hub\nimport leaf\n",
        leaf="",
        hub_test="import hub\n",
        atlascore="",
    )
    shared, leaves = importgraph.map_block(root), importgraph.leaves_block(root)
    row = next((line for line in shared.splitlines() if line.startswith("| [hub]")), "")
    if "| The hub | 2 |" not in row or "[hub_test](../scripts/hub_test.py)" not in row:
        raise SystemExit(f"FAIL the hub row is not what the imports say: {row!r}")
    if "| [one]" in shared or "| [one]" not in leaves or "| [hub]" in leaves:
        raise SystemExit("FAIL a module landed on the wrong page")
    if any(line.startswith("| [hub_test]") for line in (shared + "\n" + leaves).splitlines()):
        raise SystemExit("FAIL a test module got a row")
    (root / "scripts" / "one.py").write_text("import hub\nimport two\n", encoding="utf-8")
    if importgraph.leaves_block(root) == leaves:
        raise SystemExit("FAIL a new import did not change the map")
    print("  ok    a row is read from the imports, and a new import changes it")


def drift_case() -> None:
    names = ("module-map", "module-leaves")
    blocks = {name: atlasgen.BLOCKS[name] for name in names}
    generator = ModuleType("planted_generator")
    vars(generator).update(BLOCKS=blocks, rendered=atlasgen.rendered, GENERATED_FILES={}, document_errors=list)
    if atlas.generated_errors(generator)[0]:
        raise SystemExit(f"FAIL the map pages are stale before any plant: {atlas.generated_errors(generator)[0]}")
    for function, name in (("map_block", names[0]), ("leaves_block", names[1])):
        real = getattr(importgraph, function)
        with mock.patch.object(importgraph, function, lambda real=real: real() + "\n| planted |"):
            errors = atlas.generated_errors(generator)[0]
        if not any(name in error for error in errors):
            raise SystemExit(f"FAIL a code change the {name} page does not show was not refused: {errors}")
    print("  ok    a map page that no longer matches the source is refused")


def run(module: ModuleType | None) -> None:
    statement_case()
    lazy_case()
    network_case()
    for scratch_case in (edges_case, map_case):
        with tempfile.TemporaryDirectory(prefix="importgraph-") as directory:
            scratch_case(Path(directory))
    drift_case()


if __name__ == "__main__":
    run(None)
