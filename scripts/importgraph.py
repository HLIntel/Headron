#!/usr/bin/env python3
"""One reading of what a Python module imports, and the module map drawn from that reading.

Eight instruments each wrote the same two-branch loop over `ast.Import` and `ast.ImportFrom`, and they
disagreed by accident about relative imports. They read one statement through `statement_imports` now,
and a caller that counts a relative import says so where it asks.

proves: the names one statement imports, the sibling modules each module under scripts/ imports, and a
  map of them generated into docs/MODULES.md and docs/MODULES-LEAVES.md, so the map cannot disagree with the code
does_not_prove: reach that is not an import statement: a script started as a subprocess, a string handed
  to importlib, or an entry point declared in pyproject.toml. orphans.py reads those for its own question
closed_by: importgraph_test.py, which plants imports in a scratch tree and asserts the edges; the generated
  block check, which refuses a map page that no longer matches the source
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from atlascore import ROOT, parsed_python, walked

HUB_IMPORTERS = 8  # a module this many others import is drawn in the diagram
SHARED_IMPORTERS = 2  # below this a module is a leaf: docs/MODULES-LEAVES.md, so neither page outgrows the note cap
PURPOSE_CHARS = 110
TESTS_SHOWN = 2
UNIVERSAL = "atlascore"  # nearly every module imports it, so a row or an arrow for it says nothing
NETWORK_IMPORTS = (
    "urllib.request",
    "http.client",
    "socket",
    "ssl",
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
    "ftplib",
    "smtplib",
)


def statement_imports(node: ast.AST, *, relative: bool = False) -> list[str]:
    """The dotted names one statement imports, empty for any other node.

    A `from .x import y` counts only when the caller asks: a relative name is not an installed package and
    is not a sibling under scripts/, unless the caller is looking for exactly that.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and (relative or not node.level):
        return [node.module]
    return []


def imported_names(tree: ast.AST, *, relative: bool = False) -> set[str]:
    """Every dotted name imported anywhere under `tree`, lazy imports inside a function included."""
    return {name for node in walked(tree) for name in statement_imports(node, relative=relative)}


def network_libraries(tree: ast.AST) -> tuple[str, ...]:
    """The network libraries imported anywhere under `tree`, a relative name of the same spelling included:
    this question errs toward reporting."""
    names = imported_names(tree, relative=True)
    return tuple(sorted(n for n in names if any(n == m or n.startswith(m + ".") for m in NETWORK_IMPORTS)))


def sibling_graph(root: Path = ROOT) -> dict[str, set[str]]:
    """Each module under scripts/ mapped to the sibling modules it imports. A file that does not parse has
    no edges here; parse_errors refuses that file before anything reads this map."""
    sources = sorted((root / "scripts").glob("*.py"))
    stems = {path.stem for path in sources}
    graph: dict[str, set[str]] = {}
    for path in sources:
        tree = parsed_python(path.read_text(encoding="utf-8"), str(path))
        names = imported_names(tree) if tree is not None else set()
        graph[path.stem] = ({name.split(".")[0] for name in names} & stems) - {path.stem}
    return graph


def _is_test(name: str) -> bool:
    return name.endswith("_test")


def _purpose(path: Path) -> str:
    """The first sentence of a module's docstring, cut to fit one table cell."""
    tree = parsed_python(path.read_text(encoding="utf-8"), str(path))
    doc = (ast.get_docstring(tree) or "") if tree is not None else ""
    first = " ".join(doc.split("\n\n")[0].split()).split(". ")[0].rstrip(".")
    if len(first) > PURPOSE_CHARS:
        first = first[:PURPOSE_CHARS].rsplit(" ", 1)[0] + "…"
    return first.replace("|", "\\|")


def _mermaid_id(name: str) -> str:
    return "m_" + name


def _diagram(users: dict[str, set[str]], graph: dict[str, set[str]]) -> str:
    """The hubs and the imports between them: the part of the graph a reader can hold in their head."""
    hubs = sorted(name for name, who in users.items() if len(who) >= HUB_IMPORTERS and name != UNIVERSAL)
    lines = ["```mermaid", "flowchart LR"]
    lines += [f'  {_mermaid_id(name)}["{name} ({len(users[name])})"]' for name in hubs]
    lines += [
        f"  {_mermaid_id(name)} --> {_mermaid_id(target)}"
        for name in hubs
        for target in sorted(graph[name] & set(hubs))
    ]
    return "\n".join([*lines, "```"])


def _table(names: Iterable[str], users: dict[str, set[str]], graph: dict[str, set[str]], root: Path) -> list[str]:
    """One row per module, most used first; `tested by` comes from what the test modules really import."""
    rows = ["| module | what it is | used by | imports | tested by |", "|---|---|---:|---|---|"]
    for name in sorted(names, key=lambda name: (-len(users[name]), name)):
        uses = sorted(target for target in graph[name] if not _is_test(target) and target != UNIVERSAL)
        tests = sorted(test for test, targets in graph.items() if _is_test(test) and name in targets)
        tested = ", ".join(f"[{test}](../scripts/{test}.py)" for test in tests[:TESTS_SHOWN])
        tested += f" +{len(tests) - TESTS_SHOWN}" if len(tests) > TESTS_SHOWN else ""
        rows.append(
            f"| [{name}](../scripts/{name}.py) | {_purpose(root / 'scripts' / f'{name}.py')} "
            f"| {len(users[name])} | {', '.join(uses)} | {tested} |"
        )
    return rows


def _measured(root: Path) -> tuple[dict[str, set[str]], dict[str, set[str]], list[str], list[str]]:
    """The graph, who uses each module, and the shipped modules split into shared and leaves."""
    graph = sibling_graph(root)
    users: dict[str, set[str]] = {name: set() for name in graph}
    for name, targets in graph.items():
        for target in targets:
            if not _is_test(name):
                users[target].add(name)
    shipped = [name for name in graph if not _is_test(name)]
    shared = [name for name in shipped if len(users[name]) >= SHARED_IMPORTERS]
    return graph, users, shared, [name for name in shipped if name not in shared]


def map_block(root: Path = ROOT) -> str:
    """docs/MODULES.md: the hub diagram and one row per shared module, derived from the imports."""
    graph, users, shared, leaves = _measured(root)
    edges = sum(len(graph[name]) for name in (*shared, *leaves))
    return "\n".join(
        [
            f"{len(shared) + len(leaves)} modules and {edges} imports between them, read from the source; "
            f"{len(graph) - len(shared) - len(leaves)} test modules are left out of the rows. In the diagram an "
            f"arrow is an import and the number is how many modules use that hub. `{UNIVERSAL}` is left out of "
            f"the diagram and the imports column, because {len(users[UNIVERSAL])} modules use it. These "
            f"{len(shared)} rows are the modules at least {SHARED_IMPORTERS} others use; the other {len(leaves)}, "
            f"entry points and single-use helpers, are in [MODULES-LEAVES.md](MODULES-LEAVES.md).",
            "",
            _diagram(users, graph),
            "",
            *_table(shared, users, graph, root),
        ]
    )


def leaves_block(root: Path = ROOT) -> str:
    """docs/MODULES-LEAVES.md: the modules fewer than SHARED_IMPORTERS others use, entry points first."""
    graph, users, _shared, leaves = _measured(root)
    return "\n".join(
        [
            f"{len(leaves)} modules that at most one other module imports: {sum(not users[n] for n in leaves)} "
            f"entry points that nothing imports, and single-use helpers. The shared ones and the diagram are in "
            f"[MODULES.md](MODULES.md).",
            "",
            *_table(leaves, users, graph, root),
        ]
    )
