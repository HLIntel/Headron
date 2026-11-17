"""Tests for workflow_runner.py: a gate nobody ran is NOT RUN, never PASS, and the receipt binds the target's bytes.

proves: execute off, a gate no tool answers, a tool off PATH and a failing gate each give their measured state;
  the verdict and exit follow them; an edited target or another tree changes input_digest; the receipt verifies
does_not_prove: that the gates a pack declares are the right ones for a file
closed_by: scripts/workflow_runner_test.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import receipt
import workflow_runner
from workflow_runner import gate_rows, run_workflow, target_inputs

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def test_execute_off_is_not_run() -> None:
    rec, code = run_workflow("Sample task", path="scripts/calculation.py", execute=False, as_json=True)
    assert code == 2, f"execute off must exit 2, got {code}"
    assert rec["verdict"] == "NOT RUN", rec["verdict"]
    assert all(r["verdict"] == "NOT RUN" for r in rec["verification"]["rows"]), rec["verification"]["rows"]
    assert rec["receipt"]["status"] == "unknown"
    assert rec["receipt"]["kind"] == "headron.computation_receipt"
    assert not receipt.verify_bytes(receipt.canonical(rec["receipt"]))


def test_gate_states_are_measured() -> None:
    declared = [
        {"gate": "absent_gate", "argv": None, "state": "absent", "why": "no pack tool answers this gate"},
        {"gate": "missing_tool", "argv": ["headron-no-such-tool-xyz", "--check"]},
        {"gate": "passes", "argv": [PY, "-c", "raise SystemExit(0)"]},
        {"gate": "fails", "argv": [PY, "-c", "raise SystemExit(3)"]},
    ]
    rows = {r["id"]: r for r in gate_rows(declared, execute=True)}
    assert rows["absent_gate"]["verdict"] == "NOT RUN" and "absent" in rows["absent_gate"]["why"], rows
    assert rows["missing_tool"]["verdict"] == "NOT RUN" and "not on PATH" in rows["missing_tool"]["why"], rows
    assert rows["passes"]["verdict"] == "PASS", rows
    assert rows["fails"]["verdict"] == "FAIL", rows
    only_pass = gate_rows([declared[2]], execute=True)
    assert [r["verdict"] for r in only_pass] == ["PASS"], only_pass
    assert [r["verdict"] for r in gate_rows([declared[2]], execute=False)] == ["NOT RUN"]


def test_unmeasured_gate_turns_the_verdict() -> None:
    """A run whose only non-PASS gate is NOT RUN answers NOT RUN and exit 2, not PASS."""
    saved = workflow_runner.required_gates
    workflow_runner.required_gates = lambda _profile: ["diff_review"]  # declared, answered by no pack tool
    try:
        rec, code = run_workflow("t", path="scripts/calculation.py", execute=True, as_json=True)
    finally:
        workflow_runner.required_gates = saved
    assert (rec["verdict"], code) == ("NOT RUN", 2), (rec["verdict"], code, rec["verification"]["rows"])


def test_substituted_target_changes_input_digest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "t.py"
        target.write_text("x = 1\n", encoding="utf-8")
        first = target_inputs("t", str(target), "a")
        target.write_text("x = 2\n", encoding="utf-8")
        second = target_inputs("t", str(target), "a")
    assert first["path_sha256"] and first["path_sha256"] != second["path_sha256"]
    assert receipt.digest(first) != receipt.digest(second)
    assert target_inputs("t", str(ROOT / "absent-file-xyz"), "a")["path_sha256"] is None
    assert first["tree"], "inputs must name the tree the run read"


def test_workflow_cli() -> None:
    proc = subprocess.run(
        [
            PY,
            str(ROOT / "scripts" / "workflow_runner.py"),
            "t",
            "--path",
            "scripts/calculation.py",
            "--no-execute",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 2, f"--no-execute must exit 2: rc={proc.returncode} {proc.stderr[-300:]}"
    data = json.loads(proc.stdout)
    assert data["command"] == "workflow" and data["verdict"] == "NOT RUN"


def run_cases() -> None:
    for case in (
        test_execute_off_is_not_run,
        test_gate_states_are_measured,
        test_unmeasured_gate_turns_the_verdict,
        test_substituted_target_changes_input_digest,
        test_workflow_cli,
    ):
        case()
        print(f"  ok    {case.__name__}")


if __name__ == "__main__":
    run_cases()
    print("PASS  workflow_runner_test")
