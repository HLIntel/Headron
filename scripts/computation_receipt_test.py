"""Planted tests for computation receipts (execution-to-evidence chain).

proves: every computation binds inputs, version, outputs, and verification to a receipt that verifies from bytes
does_not_prove: that the underlying calculation's mathematical assumptions are economically suitable
closed_by: computation_receipt_test.py, running as part of the done set
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import microprogram
import receipt
from calculation import Calculation

ROOT = Path(__file__).resolve().parent.parent


def test_build_and_verify_intact() -> None:
    comp = receipt.build_computation_receipt(
        program="finance.variance",
        version="1",
        inputs={"metric": "arr", "value": 100},
        outputs={"diff": 10},
        status="ok",
        verification={"checks": [{"id": "finance.variance.contract", "state": "PASS"}]},
        evidence_refs=("knowledge.py",),
    )
    assert comp["schema"] == 1
    assert comp["kind"] == "headron.computation_receipt"
    assert comp["program"] == "finance.variance"
    assert comp["version"] == "1"
    assert comp["status"] == "ok"
    assert len(comp["receipt_id"]) == 64
    assert len(comp["input_digest"]) == 64
    assert len(comp["output_digest"]) == 64

    data = receipt.canonical(comp)
    findings = receipt.verify_bytes(data)
    assert not findings, f"expected no findings, got: {findings}"


def test_tamper_detection() -> None:
    comp = receipt.build_computation_receipt(
        program="test.program", version="1", inputs={"x": 1}, outputs={"y": 2}, status="ok"
    )
    # 1. Tampered status
    bad_status = dict(comp)
    bad_status["status"] = "refused"
    findings = receipt.verify_bytes(receipt.canonical(bad_status))
    assert any("receipt_id does not match" in f for f in findings), findings

    # 2. Tampered output
    bad_out = dict(comp)
    bad_out["output_digest"] = "0" * 64
    findings = receipt.verify_bytes(receipt.canonical(bad_out))
    assert any("receipt_id does not match" in f for f in findings), findings

    # 3. Undeclared status with recomputed id
    bad_decl = dict(comp)
    bad_decl["status"] = "invented_status"
    bad_decl["receipt_id"] = receipt.digest({k: v for k, v in bad_decl.items() if k != "receipt_id"})
    findings = receipt.verify_bytes(receipt.canonical(bad_decl))
    assert any("status is outside" in f for f in findings), findings

    # 4. Status ok with null output
    bad_null = dict(comp)
    bad_null["output_digest"] = None
    bad_null["receipt_id"] = receipt.digest({k: v for k, v in bad_null.items() if k != "receipt_id"})
    findings = receipt.verify_bytes(receipt.canonical(bad_null))
    assert any("output_digest is null" in f for f in findings), findings


def test_microprogram_execution_receipt() -> None:
    res = microprogram.run("mind.search", {"query": "proof", "limit": 2})
    assert res.receipt is not None, "microprogram run must produce a receipt"
    findings = receipt.verify_bytes(receipt.canonical(res.receipt))
    assert not findings, f"microprogram receipt failed verification: {findings}"
    assert res.receipt["program"] == "mind.search"
    assert res.receipt["status"] == res.status
    assert res.to_dict().get("receipt") == res.receipt


def test_calculation_receipt() -> None:
    class DummyCalc(Calculation):
        name = "test.dummy"
        version = "1"
        next_step = "fix input"
        operation = staticmethod(lambda ctx: ({"doubled": ctx["val"] * 2}, ("ref1",)))

    calc = DummyCalc()
    res = calc.run({"val": 21})
    assert res.status == "ok"
    assert res.output == {"doubled": 42}
    assert res.receipt is not None
    findings = receipt.verify_bytes(receipt.canonical(res.receipt))
    assert not findings, f"calculation receipt failed verification: {findings}"


def test_cli_verification() -> None:
    comp = receipt.build_computation_receipt(
        program="cli.test", version="1", inputs={"a": 10}, outputs={"b": 20}, status="ok"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        tf.write(receipt.dumps(comp))
        tpath = tf.name

    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "receipt.py"), "verify", tpath],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        assert proc.returncode == 0, f"receipt verify exited {proc.returncode}: {proc.stderr}"
        assert "computation cli.test v1  status ok" in proc.stdout
    finally:
        Path(tpath).unlink(missing_ok=True)


def run_cases() -> None:
    test_build_and_verify_intact()
    print("  ok    computation receipt build and verify intact")
    test_tamper_detection()
    print("  ok    computation receipt tamper detection")
    test_microprogram_execution_receipt()
    print("  ok    microprogram execution produces verifiable receipt")
    test_calculation_receipt()
    print("  ok    calculation execution binds inputs, outputs and receipt")
    test_cli_verification()
    print("  ok    CLI verification of computation receipt")


if __name__ == "__main__":
    run_cases()
    print("PASS  computation_receipt_test")
