"""Tests for Headron Help unified query dispatcher."""

from __future__ import annotations

import tempfile
from pathlib import Path

from help_dispatch import dispatch_help


def test_empty_query_returns_suggestions():
    res = dispatch_help("", page="gates")
    assert res["status"] == "suggested_questions"
    assert len(res["questions"]) > 0


def test_language_query_resolution():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[project]\nname='polyglot'\n", encoding="utf-8")

        res = dispatch_help("what programming languages are used in this project?", project_root=root)
        assert res["status"] == "resolved"
        assert res["authorized"] is True
        assert res["capability"] in (100, 110)
        assert "polyglot_fingerprint" in res
        assert "RESOLVED" in res["explanation"]


def test_unauthorized_execution_query():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # compile_or_typecheck (200) is denied on trust plan
        res = dispatch_help("compile and typecheck this codebase", project_root=root, plan="trust")
        assert res["status"] == "denied"
        assert res["authorized"] is False
        assert "DENIED" in res["explanation"]


def test_credential_redaction_in_help_pipeline():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        secret_query = "check " + "gh" + "p_" + "A" * 36 + " in python boundary"
        res = dispatch_help(secret_query, project_root=root)
        assert res["redactions_applied"] >= 1
        assert "ghp_" not in res["query"]


def main() -> int:
    suite = [
        test_empty_query_returns_suggestions,
        test_language_query_resolution,
        test_unauthorized_execution_query,
        test_credential_redaction_in_help_pipeline,
    ]
    idx = 0
    while idx < len(suite):
        suite[idx]()
        idx += 1
    print("help_dispatch_test: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
