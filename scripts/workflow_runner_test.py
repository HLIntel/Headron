"""Tests for workflow_runner.py.

proves: 4-phase end-to-end workflow execution, gate measurement, and receipt generation
does_not_prove: network-bound external CI runners
closed_by: scripts/workflow_runner_test.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import receipt
from workflow_runner import run_workflow

ROOT = Path(__file__).resolve().parent.parent


def test_workflow_execution() -> None:
    rec, code = run_workflow("Sample task", path="scripts/calculation.py", execute=False, as_json=True)
    assert code == 0
    assert rec["schema"] == 1
    assert rec["command"] == "workflow"
    assert rec["task"] == "Sample task"
    assert rec["path"] == "scripts/calculation.py"
    assert rec["verdict"] == "PASS"
    assert "receipt" in rec
    assert rec["receipt"]["kind"] == "headron.computation_receipt"

    # Verify receipt bytes independently
    findings = receipt.verify_bytes(receipt.canonical(rec["receipt"]))
    assert not findings, f"workflow receipt failed validation: {findings}"


def test_workflow_cli() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "workflow_runner.py"),
            "Automated test workflow",
            "--path",
            "scripts/calculation.py",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, f"workflow runner CLI failed: {proc.stderr}"
    data = json.loads(proc.stdout)
    assert data["command"] == "workflow"
    assert data["verdict"] == "PASS"


def run_cases() -> None:
    test_workflow_execution()
    print("  ok    workflow execution and receipt generation")
    test_workflow_cli()
    print("  ok    workflow runner CLI with --json")


if __name__ == "__main__":
    run_cases()
    print("PASS  workflow_runner_test")
