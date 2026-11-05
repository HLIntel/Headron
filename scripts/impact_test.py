#!/usr/bin/env python3
"""Planted cases: the test-impact map selects exactly the groups a change reaches, and says NOT RUN without a map."""

from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import types
import zlib
from pathlib import Path
from types import ModuleType


def _selection_error(mod: ModuleType) -> str | None:
    """None when `mod.select` picks the moved and the unrecorded group and leaves the untouched one."""
    real = mod.digest("VERSION")
    data = {"groups": {"kept": {"deps": {"VERSION": real}}, "moved": {"deps": {"VERSION": "0" * 64}}}}
    got = mod.select(("kept", "moved", "new"), data)
    want = {"moved": ["VERSION"], "new": ["no passing record"]}
    return None if got == want else f"select picked {got}, want {want}"


def selection_case(module: ModuleType) -> None:
    import impact

    if err := _selection_error(impact):
        raise SystemExit(f"FAIL {err}")
    module.CASES.append(
        (
            "a dependency whose bytes moved selects its group; an untouched group stays out; an unrecorded one runs",
            "a fast loop that ran no test, or every test, whatever the change reached",
        )
    )
    print("  ok    test-impact: a moved dependency selects its group, an untouched group is not run")


def map_rows_case(module: ModuleType) -> None:
    import impact

    with tempfile.TemporaryDirectory() as scratch:
        store = Path(scratch) / impact.STORE
        none = impact.changed_row(store)
        clean = {"groups": {n: {"deps": {}, "secs": 1} for n in impact.groups()}}
        store.write_text(json.dumps({"schema": impact.SCHEMA, **clean}), encoding="utf-8")
        quiet = impact.changed_row(store)
        # Many groups share the same dependencies, each list longer than zlib's 32 KB window sees back. Real
        # digests, which do not compress alone. They must round-trip exactly, and neither a damaged
        # map nor one that inflates past its bound may be mistaken for a passing record.
        deps = {f"scripts/file_{n}.py": hashlib.sha256(str(n).encode()).hexdigest() for n in range(600)}
        data = {"schema": impact.SCHEMA, "groups": {f"group_{n}": {"deps": deps, "secs": n} for n in range(20)}}
        payload = impact._payload(data)  # noqa: SLF001
        store.write_bytes(payload)
        restored = impact.load(store)
        cap, impact.MAX_STORE_BYTES = impact.MAX_STORE_BYTES, 16
        try:
            inflated = impact.load(store)
        finally:
            impact.MAX_STORE_BYTES = cap
        store.write_bytes(payload[:-1])
        damaged = impact.load(store)
        stream = base64.b64decode(json.loads(payload)["payload"])
        dangling = zlib.compress(
            json.dumps({"schema": impact.SCHEMA, "table": [], "groups": {"g": {"deps": [0]}}}).encode()
        )
        for bad in (
            stream[:-4],
            stream + b"x",
            dangling,
        ):  # the records all decode, so only the stream's end or the table can tell
            store.write_text(
                json.dumps({"schema": impact.COMPRESSED_SCHEMA, "payload": base64.b64encode(bad).decode()})
            )
            damaged = damaged or impact.load(store)
    if none["verdict"] != "NOT RUN" or quiet["verdict"] != "PASS" or quiet.get("calls") != 0:
        raise SystemExit(f"FAIL impact rows: no map gave {none}, an untouched map gave {quiet}")
    if restored != data or damaged is not None or inflated is not None or len(payload) > impact.MAX_STORE_BYTES:
        raise SystemExit("FAIL impact map: compressed records must fit, round-trip and reject corruption")
    module.CASES.append(
        (
            "no test-impact map is NOT RUN; a map nothing moved under passes without running a group",
            "a missing map read as a pass, or a quiet change that paid for the whole suite",
        )
    )
    print("  ok    test-impact: no map is NOT RUN, an untouched map runs nothing")


def recorder_case(module: ModuleType) -> None:
    import impact

    if not impact.start():  # Python 3.11 has no sys.monitoring: the recorder is off, and says so in the name
        module.CASES.append(("the test-impact recorder is off before Python 3.12 (NOT RUN here)", "a silent pass"))
        print("  ok    test-impact: recorder NOT RUN before Python 3.12")
        return
    depth = len(impact._STACK)  # noqa: SLF001
    impact.enter()
    impact.enter()
    impact.digest("VERSION")
    impact.leave("impact_inner", True, 0)
    seen = set(impact._STACK[-1])  # noqa: SLF001 — the nested reach, merged into its parent
    impact.leave("impact_outer", True, 0)
    impact._RECORDS.pop("impact_outer", None)  # noqa: SLF001 — a probe record is never saved
    impact._RECORDS.pop("impact_inner", None)  # noqa: SLF001
    if not {"VERSION", "scripts/impact.py"} <= seen or len(impact._STACK) != depth:  # noqa: SLF001
        raise SystemExit(f"FAIL the recorder saw {sorted(seen)[:6]}; stack {len(impact._STACK)} != {depth}")  # noqa: SLF001
    module.CASES.append(
        (
            "the recorder sees a file a nested group opens and the code it runs, and hands both to its parent",
            "a map built from imports, blind to lazy loads, or a nested group that erased its parent's record",
        )
    )
    print("  ok    test-impact: a nested group's opened file and executed code reach its parent")


def mutant_case(module: ModuleType) -> None:
    """The selection guard is itself mutation-tested: each planted defect in select() must fail it."""
    import impact

    source = Path(impact.__file__).read_text(encoding="utf-8")
    mutants = {
        "an edit never selects": ("if digest(p) != h]", "if digest(p) is None and h]"),
        "an unrecorded group never runs": ('chosen[name] = ["no passing record"]', "pass"),
    }
    for label, (old, new) in mutants.items():
        if old not in source:
            raise SystemExit(f"FAIL mutant anchor {old!r} is gone from impact.py: re-derive the plant")
        mutant = types.ModuleType("impact_mutant")
        mutant.__file__ = impact.__file__
        exec(compile(source.replace(old, new, 1), impact.__file__, "exec"), mutant.__dict__)  # noqa: S102
        if _selection_error(mutant) is None:
            raise SystemExit(f"FAIL the selection guard passed a mutant: {label}")
    module.CASES.append(
        (
            "the selection guard catches both planted mutants of select()",
            "a guard that passes whatever select() returns",
        )
    )
    print("  ok    test-impact: two mutants of select() caught")


def run(module: ModuleType) -> None:
    selection_case(module)
    map_rows_case(module)
    recorder_case(module)
    mutant_case(module)
