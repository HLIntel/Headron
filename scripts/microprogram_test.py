#!/usr/bin/env python3
"""Planted cases: the microprogram contract refuses an undeclared status, never raises, and each wrapper
answers its own refusal with a declared status."""

from __future__ import annotations

import contextlib
import io
from types import ModuleType
from unittest import mock


def result_contract_cases(module: ModuleType) -> None:
    """A MicroResult is the contract itself: construction refuses what the contract does not declare."""
    import microprogram

    for status, confidence in (("maybe", None), ("OK", None), ("ok", 1.5)):
        bad = {"status": status, "confidence": confidence}
        try:
            microprogram.MicroResult("p", "1", status, confidence=confidence)
        except ValueError:
            continue
        raise SystemExit(
            f"FAIL micro result: {bad} was admitted; the contract declares {sorted(microprogram.STATUSES)}"
        )
    held = microprogram.MicroResult("p", "1", "ok", confidence=None, evidence_refs=["a.py"])  # pyright: ignore[reportArgumentType] - a list must be frozen
    if held.evidence_refs != ("a.py",) or not held.actionable:
        raise SystemExit(f"FAIL micro result: evidence {held.evidence_refs!r} not frozen, or ok not actionable")
    if any(microprogram.MicroResult("p", "1", status).actionable for status in set(microprogram.STATUSES) - {"ok"}):
        raise SystemExit("FAIL micro result: a status other than ok reads actionable, so a refusal could be acted on")
    module.CASES.append(
        (
            "a MicroResult with an undeclared status or a confidence outside [0, 1] is refused at construction",
            "a status nobody declared, so a caller cannot tell a refusal from a pass",
        )
    )
    print("  ok    micro result refuses an undeclared status")


def run_never_raises_cases(module: ModuleType) -> None:
    """run() is the one door: an unknown name is refused and a raising program is status error, never an exception."""
    import microprogram

    missing = microprogram.run("no.such.program")
    if missing.status != "refused" or "no.such.program" not in missing.evidence_refs[0]:
        raise SystemExit(f"FAIL micro run: an unknown program answered {missing.to_dict()}")

    class Boom:
        name, version = "boom", "1"

        def run(self, context: object) -> microprogram.MicroResult:
            raise RuntimeError("planted")

    with mock.patch.dict(microprogram.REGISTRY, {"boom": Boom()}):
        try:
            raised = microprogram.run("boom")
        except RuntimeError as error:
            raise SystemExit(f"FAIL micro run: a raising program raised through run(): {error!r}") from None
    if raised.status != "error" or raised.evidence_refs != ("RuntimeError: planted",) or raised.output is not None:
        raise SystemExit(f"FAIL micro run: a raising program answered {raised.to_dict()}")
    module.CASES.append(
        (
            "run() refuses an unknown program and turns a raising one into status error naming the exception",
            "a step that raised through the caller, or an unknown name read as a KeyError crash",
        )
    )
    print("  ok    micro run never raises")


def wrapper_cases(module: ModuleType) -> None:
    """Each wrapper calls the existing function and maps its own failure to a declared status."""
    import graph
    import microprogram

    unclassified = microprogram.run("classify", {"files": []})
    classified = microprogram.run("classify", {"files": ["scripts/mind.py"]})
    if unclassified.status != "unknown" or classified.status != "ok" or classified.output["category"] == "unknown":
        raise SystemExit(f"FAIL micro classify: empty {unclassified.status}, mind.py {classified.to_dict()}")

    empty = microprogram.run("search", {"query": "  "})
    with mock.patch("mind.search", return_value=[{"path": "scripts/graph.py"}]) as search:
        found = microprogram.run("search", {"query": "edge domain"})
    if empty.status != "refused" or found.status != "ok" or found.evidence_refs != ("scripts/graph.py",):
        raise SystemExit(f"FAIL micro search: blank {empty.status}, query {found.to_dict()}")
    if search.call_args.args != ("edge domain",):
        raise SystemExit(f"FAIL micro search: mind.search was called with {search.call_args}")

    bad = graph.Graph()
    bad.add_node(graph.Node("claim:x", graph.NodeType.CLAIM))
    bad.add_node(graph.Node("f.py", graph.NodeType.FILE))
    bad.add_edge(graph.Edge("claim:x", "f.py", graph.EdgeType.RESTS_ON))
    bad.add_edge(graph.Edge("f.py", "gone", graph.EdgeType.RESTS_ON))
    refused = microprogram.run("graph.edges", {"graph": bad})
    clean = microprogram.run("graph.edges", {"graph": graph.Graph()})
    if refused.status != "refused" or len(refused.evidence_refs) != 2 or clean.status != "ok":
        raise SystemExit(f"FAIL micro graph.edges: planted {refused.to_dict()}, empty {clean.status}")
    if set(microprogram.REGISTRY) != {"classify", "search", "graph.edges"}:
        raise SystemExit(f"FAIL micro registry: {sorted(microprogram.REGISTRY)} has a program no case here plants")
    module.CASES.append(
        (
            "classify, search and graph.edges map an unclassifiable change, a blank query and a bad edge to unknown, refused, refused",
            "a wrapper that reports ok over the wrapped function's own refusal",
        )
    )
    print("  ok    micro wrappers keep the wrapped refusal")


def cli_cases(module: ModuleType) -> None:
    """`headron mind --micro` exits 0 only for an actionable answer."""
    import mind

    codes = {}
    for name in ("list", "no.such.program"):
        with contextlib.redirect_stdout(io.StringIO()):
            codes[name] = mind.main(["--micro", name, "--json"])
    if codes != {"list": 0, "no.such.program": 1}:
        raise SystemExit(f"FAIL micro cli: exit codes {codes}")
    module.CASES.append(
        (
            "`headron mind --micro` exits 0 for list and 1 for a refused program",
            "a refusal that exits 0 to a caller reading only the code",
        )
    )
    print("  ok    micro cli fails closed")


def run(module: ModuleType) -> None:
    for cases in (result_contract_cases, run_never_raises_cases, wrapper_cases, cli_cases):
        cases(module)
