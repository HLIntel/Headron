#!/usr/bin/env python3
"""Mutation tests for the state-graph encoder.

Each check encodes a planted in-memory repository and asserts one fact of the graph.
Every check must hold; the check count is asserted at the end.

    python scripts/stategraph_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import stategraph  # noqa: E402


def edge(graph: dict, a: str, b: str, kind: str) -> bool:
    return {"from": a, "to": b, "kind": kind} in graph["edges"]


PLANT = {
    "scripts/alpha.py": "from beta import helper\n\ndef run():\n    return helper(1)\n",
    "scripts/beta.py": "def helper(x):\n    return x + 1\n",
}
EDITED = {**PLANT, "scripts/beta.py": "def helper(x):\n    return x + 2\n"}
BROKEN = {**PLANT, "scripts/gamma.py": "def oops(:\n"}
EXTERNAL = {"scripts/delta.py": "import json\n\ndef f():\n    return json.dumps(1)\n"}

g = stategraph.encode(PLANT)
HELPER = "scripts/beta.py::helper"

# (name, kills, holds)
CHECKS: list[tuple[str, str, bool]] = [
    (
        "cross-module call resolves through a from-import",
        "a call edge that drops across modules",
        edge(g, "scripts/alpha.py::run", HELPER, "calls"),
    ),
    (
        "from-import records a module edge",
        "an import that is not recorded",
        edge(g, "scripts/alpha.py", "scripts/beta.py", "imports"),
    ),
    ("module defines its top-level function", "a missing defines edge", edge(g, "scripts/beta.py", HELPER, "defines")),
    ("function node carries its kind", "a node with the wrong kind", g["nodes"][HELPER]["kind"] == "function"),
    (
        "editing a body changes its sha256",
        "a body edit that keeps the same hash",
        g["nodes"][HELPER]["sha256"] != stategraph.encode(EDITED)["nodes"][HELPER]["sha256"],
    ),
    ("same bytes encode to the same graph", "a nondeterministic encoding", stategraph.encode(PLANT) == g),
    (
        "syntax error is recorded and does not stop the encoding",
        "a silent drop of a broken file",
        "scripts/gamma.py" in stategraph.encode(BROKEN)["errors"]
        and "scripts/alpha.py::run" in stategraph.encode(BROKEN)["nodes"],
    ),
    (
        "standard-library import is not a repository edge",
        "an edge to a file outside the repository",
        not [e for e in stategraph.encode(EXTERNAL)["edges"] if e["kind"] == "imports"],
    ),
]


def main() -> int:
    """Run every check, print one line each, and assert the count."""
    for name, _kills, holds in CHECKS:
        assert holds, name
        print(f"  ok    {name}")
    count = len(CHECKS)
    assert count == 8, count
    print(f"{count} cases ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
