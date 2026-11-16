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
    if set(microprogram.REGISTRY) != {"classify", "search", "graph.edges", "context.credit"}:
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


def credit_cases(module: ModuleType) -> None:
    """context.credit scores each item by the verdict it changed, refuses an unpaired item, and reads an
    errored run as unknown, never as unsolved."""
    import json
    import os
    import tempfile
    from pathlib import Path

    import microprogram

    def runs(*solved: bool, error_seed: int | None = None) -> list[dict]:
        return [{"seed": s, "solved": v, "agent_error": s == error_seed} for s, v in enumerate(solved)]

    full = runs(True, True, False)
    without = {
        "helps.py": runs(False, False, False),
        "noise.py": runs(True, True, False),
        "hurts.py": runs(True, True, True),
    }
    scored = microprogram.run("context.credit", {"shape": "bugfix:py", "full": full, "without": without})
    credits = scored.output or {}
    want = {"helps.py": (2, 0, 2 / 3), "noise.py": (0, 0, 0.0), "hurts.py": (0, 1, -1 / 3)}
    got = {item: (row["helped"], row["hurt"], row["credit"]) for item, row in credits.items()}
    if scored.status != "ok" or got != want or credits["noise.py"]["p"] != 1.0:
        raise SystemExit(f"FAIL micro credit: planted helped/hurt/credit {want}, got {scored.status} {got}")
    if [round(microprogram.mcnemar_exact(*bc), 4) for bc in ((6, 0), (5, 0), (2, 2))] != [0.0312, 0.0625, 1.0]:
        raise SystemExit("FAIL micro credit: exact McNemar p is not 2*sum C(n,i)/2^n over the discordant pairs")

    # The trap: agentbench scores a timeout solved=False; read as a verdict it credits the removed item +1.
    outage = {"helps.py": runs(False, True, False, error_seed=0)}
    errored = microprogram.run("context.credit", {"shape": "bugfix:py", "full": full, "without": outage})
    if errored.status != "unknown" or errored.output is not None or "helps.py seed 0" not in errored.evidence_refs[0]:
        raise SystemExit(f"FAIL micro credit: an errored run answered {errored.to_dict()}, not unknown")
    for bad in ({"helps.py": runs(False, False)}, {"helps.py": [*runs(False, False, False), runs(True)[0]]}, {}):
        unpaired = microprogram.run("context.credit", {"shape": "bugfix:py", "full": full, "without": bad})
        if unpaired.status != "refused":
            raise SystemExit(f"FAIL micro credit: unpaired runs {bad} answered {unpaired.status}, not refused")

    with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"HEADRON_HOME": home}):
        store = Path(home) / "context-credit.jsonl"
        context = {"shape": "bugfix:py", "full": full, "without": without, "record": True}
        microprogram.run("context.credit", context)
        first = store.read_bytes()
        microprogram.run("context.credit", context)
        lines = store.read_text(encoding="utf-8").splitlines()
        if len(lines) != 6 or not store.read_bytes().startswith(first) or json.loads(lines[0])["shape"] != "bugfix:py":
            raise SystemExit(f"FAIL micro credit: the log is not append-only, {len(lines)} lines after two records")
    module.CASES.append(
        (
            "context.credit scores helped/hurt per item, refuses an unpaired item, reads an errored run as unknown, appends only",
            "an outage credited to the removed item, or a credit log rewritten over earlier measurements",
        )
    )
    print("  ok    micro context.credit scores the verdict an item changed")


def run(module: ModuleType) -> None:
    result_contract_cases(module)
    run_never_raises_cases(module)
    wrapper_cases(module)
    cli_cases(module)
    credit_cases(module)
