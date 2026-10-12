#!/usr/bin/env python3
"""Planted cases for the secret and workflow gates (3.54.0): each declared gate refuses a planted defect.

The argv is read from verification_policy/done_set and run by verify.run_gate in a scratch tree, so a gate
dropped or weakened in the declaration fails here. A machine without the program prints SKIP: verify reads
the same absence as NOT RUN, never PASS.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import verify
from atlascore import atlas

CLEAN = (
    "name: ok\non: push\npermissions: {}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n"
)
INJECT = CLEAN.replace("echo hi", "echo ${{ github.event.issue.title }}")
SYNTAX = CLEAN.replace("runs-on: ubuntu-latest", "runs-onn: ubuntu-latest")
SECRET = "token = " + "ghp_" + "aB3dE5fG7hJ9kL1mN3pQ5rS7tU9vW1xY3zA5"  # assembled: this file must scan clean itself


def _gate(gate_id: str) -> dict:
    rows = [g for g in (atlas().get("verification_policy") or {}).get("done_set") or [] if g["id"] == gate_id]
    if len(rows) != 1:
        raise SystemExit(f"FAIL done_set declares {len(rows)} '{gate_id}' gate(s), not one")
    return rows[0]


def _verdict(gate_id: str, files: dict[str, str]) -> str:
    with tempfile.TemporaryDirectory() as scratch:
        (Path(scratch) / ".git").mkdir()  # actionlint finds its project by the repository root
        for rel, text in files.items():
            (Path(scratch) / rel).parent.mkdir(parents=True, exist_ok=True)
            (Path(scratch) / rel).write_text(text, encoding="utf-8")
        return verify.run_gate(_gate(gate_id), cwd=Path(scratch))["verdict"]


def run(module) -> None:
    flow = ".github/workflows/w.yml"
    for gate_id, clean, planted in (
        ("secret_scan", {"a.txt": "nothing here\n"}, {"a.txt": SECRET + "\n"}),
        ("workflow_lint", {flow: CLEAN}, {flow: SYNTAX}),
        ("workflow_audit", {flow: CLEAN}, {flow: INJECT}),
    ):
        good, bad = _verdict(gate_id, clean), _verdict(gate_id, planted)
        if "NOT RUN" in (good, bad):
            print(f"  SKIP  {gate_id}: its program is not installed here (verify reads NOT RUN)")
        elif (good, bad) != ("PASS", "FAIL"):
            raise SystemExit(f"FAIL {gate_id}: a clean tree read {good} and a planted defect read {bad}")
        module.CASES.append(
            (
                f"{gate_id} passes a clean scratch tree and refuses a planted defect",
                "a gate that is declared but passes whatever it is given",
            )
        )
    print("  ok    secret and workflow gates: clean passes, planted refused")
