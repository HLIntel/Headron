#!/usr/bin/env python3
"""Planted cases: verify's runner reads a gate's output bounded, and an exit declared undecided is NOT RUN."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path
from shutil import rmtree
from threading import Event


def undecided_case(module) -> None:
    """pytest's exit 5 (no tests collected) was a FAIL here and a SKIP in enforce.py: one rule, two verdicts."""
    import verify

    with tempfile.TemporaryDirectory() as scratch:
        # A STAND-IN, NOT pytest: CI installs only the lock, so the case plants the program and its exit.
        stand_in = Path(scratch) / "pytest"
        stand_in.write_text("#!/bin/sh\necho 'no tests ran in 0.00s'\nexit 5\n", encoding="utf-8")
        stand_in.chmod(0o755)
        gate = {"id": "u", "argv": [str(stand_in), "-q"]}
        row = verify.run_gate(gate, Path(scratch))
        if row["verdict"] != "NOT RUN" or "decided nothing" not in row["why"] or row.get("exit") != 5:
            raise SystemExit(f"FAIL verify read pytest's no-tests exit as {row['verdict']}: {row.get('why')!r}")
        real = verify.undecided_exit
        verify.undecided_exit = lambda tool, code: ""
        try:
            planted = verify.run_gate(gate, Path(scratch))
        finally:
            verify.undecided_exit = real
    if planted["verdict"] != "FAIL":
        raise SystemExit("FAIL the undecided case did not notice a runner that ignores enforcement/undecided_exits")
    if verify.verdict_code([row]) != 2:
        raise SystemExit("FAIL an undecided gate did not hold verify at exit 2 (incomplete is not done)")
    module.CASES.append(
        (
            "a gate exit declared undecided is NOT RUN in verify, as it is in enforce",
            "a consumer with no tests yet reading FAIL, blamed on a change that decided nothing",
        )
    )
    print("  ok    pytest's no-tests exit is NOT RUN in verify, as in enforce")


def bounded_case(module) -> None:
    """A gate printing past HEAD_BYTES + TAIL_BYTES is read as head and tail; its byte count is still true."""
    import verify

    flood = "import sys; sys.stdout.write('SCOPE head\\n' + 'x' * 999 + '\\n'); [print('y' * 99) for _ in range(9000)]; print('FAIL the tail'); raise SystemExit(1)"
    row = verify.run_gate({"id": "f", "argv": ["python", "-c", flood]})
    if row["verdict"] != "FAIL" or "the tail" not in row["why"] or row["output_bytes"] < 900_000:
        raise SystemExit(
            f"FAIL a flooding gate was misread: {row['verdict']} {row.get('why')!r} {row.get('output_bytes')}"
        )
    _, read, size = verify._bounded_run([sys.executable, "-c", flood], Path.cwd())
    if len(read) > verify.HEAD_BYTES + verify.TAIL_BYTES + 200 or size < 900_000:
        raise SystemExit(f"FAIL verify held {len(read)} of {size} bytes of a flooding gate, not a head and a tail")
    if "SCOPE head" not in row["self_report"]:
        raise SystemExit("FAIL the head of a flooding gate's output, where its self-report is, was dropped")
    module.CASES.append(
        (
            "a gate's output is read as a bounded head and tail, its verdict line and self-report kept",
            "a looping gate's output held whole in memory until the machine kills the run",
        )
    )
    print("  ok    a flooding gate is read bounded: head, tail and true byte count")


def concurrency_case(module) -> None:
    """Readers overlap, while a mutator begins only after the last reader exits."""
    import verify

    readers = [
        {"id": "reader-a", "argv": ["python", "-c", ""], "mutates": False},
        {"id": "reader-b", "argv": ["python", "-c", ""], "mutates": False},
    ]
    mutator = {"id": "plant", "argv": ["python", "-c", ""], "mutates": True}
    events: list[tuple[str, float]] = []
    real = verify.run_gate

    def planted(gate, cwd, env=None):
        events.append((f"start:{gate['id']}", time.monotonic()))
        Event().wait(0.05)
        events.append((f"end:{gate['id']}", time.monotonic()))
        return {"id": gate["id"], "verdict": "PASS", "argv": gate["argv"]}

    verify.run_gate = planted
    try:
        rows = verify.run_declared_gates([*readers, mutator], Path.cwd(), jobs=2)
    finally:
        verify.run_gate = real
    moments = dict(events)
    if moments["start:reader-a"] >= moments["end:reader-b"] or moments["start:reader-b"] >= moments["end:reader-a"]:
        raise SystemExit("FAIL read-only gates did not overlap")
    if moments["start:plant"] < max(moments["end:reader-a"], moments["end:reader-b"]):
        raise SystemExit("FAIL mutating gate began before all read-only gates ended")
    if [row["id"] for row in rows] != ["reader-a", "reader-b", "plant"]:
        raise SystemExit("FAIL concurrent gates lost declared result order")
    module.CASES.append(
        (
            "read-only verification gates overlap, while mutating gates wait and results retain declaration order",
            "a planted suite reads a concurrently-mutated tree or a parallel runner scrambles gate attribution",
        )
    )
    print("  ok    read-only gates overlap; the mutating gate waits and result order is stable")


def artifact_gate_home_case(module) -> None:
    """A per-artifact gate id is a record key, not a temporary-directory name."""
    import verify

    environment = verify._gate_env("0-compiler_or_typechecker:scripts/atlas.py")
    home = Path(environment["THEA_HOME"])
    try:
        if not home.is_dir() or ":" in home.name or "/" in home.name:
            raise SystemExit(f"FAIL a per-artifact gate made an invalid private home: {home}")
    finally:
        rmtree(home, ignore_errors=True)
    module.CASES.append(
        (
            "a per-artifact gate id becomes a portable private verifier home",
            "a changed-file verification aborting before a gate can report its verdict on macOS",
        )
    )
    print("  ok    a per-artifact gate id makes a portable private verifier home")


def run(module) -> None:
    undecided_case(module)
    bounded_case(module)
    concurrency_case(module)
    artifact_gate_home_case(module)
