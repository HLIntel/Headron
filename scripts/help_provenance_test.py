"""Tests for Headron provenance compiler and freshness evaluator."""

from __future__ import annotations

import tempfile
from pathlib import Path

from help_provenance import build_provenance, digest_file, evaluate_freshness, verify_provenance


def test_provenance_existing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sample = root / "sample.py"
        sample.write_text("print('hello world')\n", encoding="utf-8")

        rec = build_provenance(sample, root=root)
        assert rec["exists"] is True
        assert rec["status"] == "live"
        assert rec["path"] == "sample.py"
        assert len(rec["digest"]) == 64
        assert rec["bytes"] > 0
        assert rec["lines"] == 1


def test_provenance_missing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        missing = root / "missing.py"
        rec = build_provenance(missing, root=root)
        assert rec["exists"] is False
        assert rec["status"] == "unavailable"
        assert rec["digest"] == ""


def test_evaluate_freshness():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "data.json"
        target.write_text('{"val": 1}', encoding="utf-8")
        orig_digest = digest_file(target)

        assert evaluate_freshness(orig_digest, target) == "live"

        # Mutate file
        target.write_text('{"val": 2}', encoding="utf-8")
        assert evaluate_freshness(orig_digest, target) == "stale"


def test_verify_provenance_record():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        f = root / "contract.txt"
        f.write_text("fixed content", encoding="utf-8")
        rec = build_provenance(f, root=root)

        assert verify_provenance(rec, root) is True

        # Tamper with file
        f.write_text("tampered content", encoding="utf-8")
        assert verify_provenance(rec, root) is False


def main() -> int:
    test_provenance_existing_file()
    test_provenance_missing_file()
    test_evaluate_freshness()
    test_verify_provenance_record()
    print("provenance_test: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
