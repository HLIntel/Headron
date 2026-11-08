#!/usr/bin/env python3
"""Regression cases for claims and `headron revise`: a refuted belief cannot keep its dependents."""

from __future__ import annotations

import contextlib
import io
import tempfile
from pathlib import Path
from types import ModuleType

INV = "inv:claims_hold_or_name_their_revision"


def _tree(tmp: Path) -> Path:
    """A tree where each ref kind names one real thing."""
    (tmp / "scripts").mkdir()
    (tmp / "scripts" / "mod.py").write_text("LIMIT = 3\n\n\ndef used():\n    return LIMIT\n", encoding="utf-8")
    (tmp / "docs" / "systems").mkdir(parents=True)
    (tmp / "docs" / "systems" / "decisions.yaml").write_text("pick_one:\n  decides: x\n", encoding="utf-8")
    (tmp / "docs" / "systems" / "judgments.yaml").write_text("ask_one:\n  kind: yes_no\n", encoding="utf-8")
    (tmp / "atlas.yaml").write_text(
        "gate_tools:\n  formatter:\n    adopted_by: {ruff: [ruff.toml]}\n", encoding="utf-8"
    )
    (tmp / "style.cfg").write_text("indent = 4\nswitch_case_indent = true\n", encoding="utf-8")
    return tmp


def _claim(**over: object) -> dict:
    spec = {
        "statement": "s",
        "label": "CONFIRMED",
        "evidence": ["file:style.cfg"],
        "provenance": "p",
        "status": "holds",
    }
    return {**spec, **over}


def unit_cases(module: ModuleType) -> None:
    import claims

    with tempfile.TemporaryDirectory() as raw:
        root = _tree(Path(raw))
        good = {
            "base": _claim(
                dependents=[
                    "claim:top",
                    "decision:pick_one",
                    "judgment:ask_one",
                    "symbol:mod.used",
                    "symbol:mod.LIMIT",
                    "atlas:gate_tools/formatter/adopted_by",
                ]
            ),
            "top": _claim(dependents=["file:style.cfg"]),
            "old": _claim(status="refuted", label="INFERRED", superseded_by="base"),
        }
        assert claims.claim_errors(good, root) == [], claims.claim_errors(good, root)
        planted = [
            ({"base": {k: v for k, v in good["base"].items() if k != "provenance"}}, "declares no provenance"),
            ({"base": _claim(label="LIKELY")}, "label 'LIKELY' is not one of"),
            ({"base": _claim(status="maybe")}, "status 'maybe' is not holds or refuted"),
            ({"base": _claim(dependents=["claim:nobody"])}, "claim:nobody names no claim"),
            ({"base": _claim(dependents=["decision:nope"])}, "names no record in docs/systems/decisions.yaml"),
            ({"base": _claim(dependents=["symbol:mod.gone"])}, "names no top-level def"),
            ({"base": _claim(dependents=["symbol:nomod.used"])}, "names no module under scripts/"),
            ({"base": _claim(dependents=["atlas:gate_tools/linter"])}, "'linter' is missing"),
            ({"base": _claim(evidence=["file:absent.txt"])}, "is not a file in the tree"),
            ({"base": _claim(evidence=["url:x"])}, "is not <claim|"),
            (
                {"base": _claim(refuted_if={"file": "style.cfg", "matches": r"switch_case_indent\s*="})},
                "still says it holds",
            ),
            (
                {"base": _claim(status="refuted", superseded_by="top", dependents=["file:style.cfg"]), "top": _claim()},
                "dependents still rest on it",
            ),
            ({"base": _claim(status="refuted", superseded_by="gone")}, "names no holding superseded_by"),
            (
                {
                    "base": _claim(status="refuted", superseded_by="top"),
                    "top": _claim(status="refuted", superseded_by="base"),
                },
                "names no holding superseded_by",
            ),
            ({}, "holds no claims"),
        ]
        for records, needle in planted:
            found = claims.claim_errors(records, root)
            assert any(needle in e for e in found), f"{needle!r} not in {found}"
    module.CASES.append(
        (
            "claims: a missing field, a bad label or status, every unresolved ref kind, a refuted claim "
            "still holding or carrying dependents and a bad successor are refused",
            "a belief no one can check",
        )
    )
    print("  ok    claims: 15 planted records refused, the complete record passes")


def revise_cases(module: ModuleType) -> None:
    import claims

    chain = {
        "root": _claim(dependents=["claim:mid", "file:a"]),
        "mid": _claim(dependents=["claim:leaf", "file:a"]),
        "leaf": _claim(dependents=["symbol:mod.used"]),
        "loop": _claim(dependents=["claim:loop"]),
    }
    assert claims.dependents("root", chain) == ["claim:mid", "file:a", "claim:leaf", "symbol:mod.used"], (
        claims.dependents("root", chain)
    )
    assert claims.dependents("loop", chain) == ["claim:loop"], "a self-loop ends the walk"
    assert claims.resting_on("symbol:mod.used", chain) == ["root", "mid", "leaf"], claims.resting_on(
        "symbol:mod.used", chain
    )
    with tempfile.TemporaryDirectory() as raw:
        root = _tree(Path(raw))
        (root / "docs" / "systems" / "claims.yaml").write_text(
            "was:\n  statement: s\n  label: INFERRED\n  evidence: [file:style.cfg]\n  provenance: p\n  status: refuted\n"
            "  superseded_by: now\n  dependents: [symbol:mod.used]\n"
            "now:\n  statement: s\n  label: CONFIRMED\n  evidence: [file:style.cfg]\n  provenance: p\n  status: holds\n",
            encoding="utf-8",
        )
        with contextlib.redirect_stdout(io.StringIO()) as out:
            codes = [
                claims.revise("was", None, False, root),
                claims.revise("now", None, False, root),
                claims.revise("ghost", None, False, root),
                claims.revise(None, None, False, root),
                claims.revise(None, "symbol:mod.used", True, root),
            ]
    assert codes == [1, 0, 2, 1, 0], codes
    assert "revise: symbol:mod.used" in out.getvalue() and '"rests_on": ["was"]' in out.getvalue(), out.getvalue()
    module.CASES.append(
        (
            "revise: dependents through claim chains; exit 1 while a refuted claim carries one, 2 unknown",
            "a refuted belief whose dependents nobody is told to revise",
        )
    )
    print("  ok    revise: transitive dependents, self-loop ends, exit 1 refuted-with-dependents, 2 unknown")


def chain_mutation_case(module: ModuleType) -> None:
    """Drop the chain edge in `dependents`: the transitive walk must see the gap."""
    import importlib

    import claims

    chain = {"root": _claim(dependents=["claim:mid"]), "mid": _claim(dependents=["symbol:mod.used"])}
    edge = 'if kind == "claim" and child not in seen:'
    with module.mutated("scripts/claims.py", lambda s: s.replace(edge, "if False:", 1)):
        walked = importlib.reload(claims).dependents("root", chain)
    importlib.reload(claims)
    if "symbol:mod.used" in walked:
        raise SystemExit(f"FAIL the mutant without the chain edge still walked to the leaf: {walked}")
    assert claims.dependents("root", chain) == ["claim:mid", "symbol:mod.used"]
    module.CASES.append(
        (
            "claims mutation: drop the claim-chain edge and the transitive dependent is lost",
            "a revise that names only direct dependents",
        )
    )
    print("  ok    claims mutation: the dropped chain edge is killed")


def plant_cases(module: ModuleType) -> None:
    """Each defect planted into the live registry trips the invariant."""
    registry = "docs/systems/claims.yaml"
    planted = [
        (
            "  status: refuted\n",
            "  status: holds\n",
            "a claim the .editorconfig refutes cannot be marked holds",
            "still says it holds",
        ),
        (
            "  superseded_by: editorconfig_adopts_only_what_it_names\n",
            "  superseded_by: editorconfig_adopts_only_what_it_names\n  dependents: [symbol:gateplace.unadopted]\n",
            "a refuted claim cannot keep a dependent",
            "dependents still rest on it",
        ),
        (
            "symbol:gateplace.unadopted]",
            "symbol:gateplace.unadopt]",
            "a claim naming a gone symbol is refused",
            "names no top-level",
        ),
        ("  label: INFERRED\n", "  label: LIKELY\n", "a claim with an unknown label is refused", "is not one of"),
    ]
    for current, plant, name, needle in planted:
        with module.mutated(registry, lambda s, c=current, p=plant: s.replace(c, p, 1)):
            module.case(name, "a belief a gate rests on, left unchecked", expect_fail=True, needle=needle, by=INV)


def run(module: ModuleType) -> None:
    for step in (unit_cases, revise_cases, chain_mutation_case, plant_cases):
        step(module)
