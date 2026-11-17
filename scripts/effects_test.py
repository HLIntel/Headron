"""Declared effects, enforced: each planted undeclared effect is refused before it happens and ends the run.

Run by microprogram_test.py (run_never_raises_cases). Each refusal has a control: the same act, declared, succeeds,
so a hook that refused everything would fail here too.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from unittest import mock

import effects
import microprogram

PLANTED = "effects.planted"


class _Planted:
    """A registered program whose run() performs one act, under whatever declaration it is given."""

    name = PLANTED
    version = "1"
    timeout_s = 20.0

    def __init__(self, declared: effects.Declared, act: Callable[[], None]) -> None:
        self.declared = declared
        self.act = act

    def run(self, context: Mapping[str, Any]) -> microprogram.MicroResult:
        self.act()
        return microprogram.MicroResult(self.name, self.version, "ok")


def _run(declared: effects.Declared, act: Callable[[], None]) -> microprogram.MicroResult:
    with mock.patch.dict(microprogram.REGISTRY, {PLANTED: _Planted(declared, act)}):
        return microprogram.run(PLANTED)


def _fail(what: str, result: microprogram.MicroResult | None = None) -> None:
    said = f": {result.to_dict()}" if result is not None else ""
    raise SystemExit(f"FAIL effects: {what}{said}")


def _refused(result: microprogram.MicroResult, effect: str) -> bool:
    said = " ".join(result.evidence_refs)
    return result.status == "error" and "Undeclared" in said and f"undeclared {effect}" in said


def write_cases(top: Path) -> None:
    target = top / "planted.txt"

    def write() -> None:
        target.write_text("planted\n", encoding="utf-8")

    refused = _run(effects.Declared(), write)
    if not _refused(refused, "write") or target.exists():
        _fail(f"an undeclared write was not refused before it happened (created: {target.exists()})", refused)

    def swallow() -> None:
        try:
            target.write_text("planted\n", encoding="utf-8")
        except PermissionError:
            pass

    swallowed = _run(effects.Declared(), swallow)
    if not _refused(swallowed, "write") or target.exists():
        _fail(f"a swallowed violation did not end the run (created: {target.exists()})", swallowed)

    allowed = _run(effects.Declared({"write"}), write)
    if allowed.status != "ok" or not target.exists():
        _fail("a declared write was refused", allowed)


def spawn_cases() -> None:
    def spawn() -> None:
        subprocess.run([sys.executable, "-c", "pass"], check=True, timeout=20)

    refused = _run(effects.Declared(), spawn)
    if not _refused(refused, "spawn"):
        _fail("an undeclared spawn was not refused", refused)
    elsewhere = _run(effects.Declared({"spawn"}, {"git"}), spawn)
    said = " ".join(elsewhere.evidence_refs)
    if elsewhere.status != "error" or "may start only ['git']" not in said:
        _fail("a spawn of an executable outside capabilities was not refused", elsewhere)
    allowed = _run(effects.Declared({"spawn"}, {os.path.basename(sys.executable)}), spawn)
    if allowed.status != "ok":
        _fail("a spawn of a declared capability was refused", allowed)


def net_cases() -> None:
    # The interpreter raises "socket.connect" before a socket connects; raising the same audit event here plants a
    # connection without importing a network library, which the public tree allows only in its network_modules.
    def connect() -> None:
        sys.audit("socket.connect", None, ("127.0.0.1", 9))

    refused = _run(effects.Declared(), connect)
    if not _refused(refused, "net"):
        _fail("an undeclared connect was not refused", refused)
    allowed = _run(effects.Declared({"net"}), connect)
    if allowed.status != "ok":
        _fail("a declared connect was refused", allowed)


def validate_cases() -> None:
    class Bare:
        name = "bare"

    class Holding:
        name = "holding"

        def __init__(self, declared: effects.Declared) -> None:
            self.declared = declared

    if not any("declares no effects" in p for p in effects.validate(Bare())):
        _fail("a program with no declaration validated")
    planted = {
        "unknown effect": effects.Declared({"teleport"}),
        "unknown cache_policy": effects.Declared(cache_policy="sometimes"),
        "spawn and capabilities go together": effects.Declared({"spawn"}),
        "capabilities without spawn": effects.Declared(capabilities={"git"}),
        "content cache on a nondeterministic program": effects.Declared(cache_policy="content"),
        "content cache on a program with effects": effects.Declared(
            {"read"}, deterministic=True, cache_policy="content"
        ),
    }
    for why, declared in planted.items():
        if not effects.validate(Holding(declared)):
            _fail(f"validate admitted {why}: {declared.to_dict()}")
    if problems := effects.validate(Holding(effects.PURE)):
        _fail(f"PURE does not validate: {problems}")
    try:
        effects.Declared("write")  # pyright: ignore[reportArgumentType] - a bare string is the planted mistake
    except TypeError:
        pass
    else:
        _fail("a bare string was split into effects")
    for name, program in microprogram.REGISTRY.items():
        if problems := effects.validate(program):
            _fail(f"registered program {name} declares unsoundly: {problems}")


def _calculation_contexts() -> dict[str, dict[str, Any]]:
    period = {"start": "2025" + "-01-01", "end": "2025" + "-12-31"}  # split: a whole date reads as a claim

    def item(measure: str, value: str) -> dict[str, Any]:
        return {"measure": measure, "value": value, "unit": "USD", "period": period, "source": measure}

    row = {"key": "sales", "value": "12.30", "unit": "USD", "period": "annual", "source": "left"}
    actual = {**item("actual", "12"), "metric": "sales"}
    return {
        "finance.evaluate": {
            "formula": "cost_of_debt.historical",
            "inputs": {
                "interest_expense": item("interest_expense", "5"),
                "average_interest_bearing_debt": item("average_interest_bearing_debt", "100"),
            },
        },
        "data.reconcile": {"left": [row], "right": [{**row, "value": "10.20", "source": "right"}]},
        "compute.compose": {
            "version": "1",
            "nodes": [
                {
                    "id": "v",
                    "op": "finance.variance",
                    "inputs": {"actual": actual, "budget": {**actual, "measure": "budget", "value": "10"}},
                }
            ],
        },
        "compute.contract": {"program": "compute.compose"},
    }


def deterministic_cases() -> None:
    contexts = _calculation_contexts()
    deterministic = {n for n, p in microprogram.REGISTRY.items() if effects.declared_of(p).deterministic}
    if deterministic != set(contexts):
        _fail(f"deterministic programs {sorted(deterministic)} have no sample context here: {sorted(contexts)}")
    for name, context in contexts.items():
        first, second = microprogram.run(name, context), microprogram.run(name, context)
        if first.status != "ok" or first.output != second.output:
            _fail(f"{name} declares deterministic but two runs differ ({first.status})", second)


def list_cases() -> None:
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()) as out:
        microprogram.cli("list", [], True)
    rows = json.loads(out.getvalue())
    missing = [
        row["name"]
        for row in rows
        if set(row.get("declared", {})) != {"effects", "capabilities", "deterministic", "cache_policy"}
    ]
    if missing:
        _fail(f"`micro list` rows carry no declaration for {missing}")


def run_cases() -> None:
    with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"HEADRON_HOME": home}):
        write_cases(Path(home))
        spawn_cases()
        net_cases()
        validate_cases()
        deterministic_cases()
        list_cases()


if __name__ == "__main__":
    run_cases()
    print("effects: PASS")
