"""Tests for polyglot capability negotiation and verification planning."""

from __future__ import annotations

import tempfile
from pathlib import Path

from capability_catalog import EXECUTE_TESTS, FORMAT_CODE
from polyglot_plan import negotiate_capability, plan_cross_language_verification


def test_negotiate_python_capabilities():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")

        res_test = negotiate_capability(EXECUTE_TESTS, root, route="python")
        assert res_test["capability"] == EXECUTE_TESTS
        assert res_test["route"] == "python"
        assert res_test["status"] in ("ready", "unavailable")

        res_fmt = negotiate_capability(FORMAT_CODE, root, route="python")
        assert res_fmt["capability"] == FORMAT_CODE
        assert "ruff" in res_fmt.get("selected_tool", "") or res_fmt["status"] == "unavailable"


def test_negotiate_unsupported_route():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        res = negotiate_capability(9999, root, route="brainfuck")
        assert res["status"] == "unsupported"
        assert res["selected_tool"] is None


def test_plan_single_file_verification():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        f = root / "src" / "main.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("print(1)\n", encoding="utf-8")

        plan = plan_cross_language_verification(f, root)
        assert plan["is_cross_language"] is False
        assert len(plan["plan_steps"]) == 2
        assert plan["plan_steps"][0]["action"] == "compile_or_typecheck"


def test_plan_cross_language_verification():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        proto = root / "proto" / "service.proto"
        proto.parent.mkdir(parents=True, exist_ok=True)
        proto.write_text("syntax = 'proto3'; service S {}", encoding="utf-8")

        plan = plan_cross_language_verification(proto, root)
        assert plan["is_cross_language"] is True
        assert len(plan["plan_steps"]) == 3
        actions = [s["action"] for s in plan["plan_steps"]]
        assert "validate_contract_schemas" in actions
        assert "typecheck_producers_and_consumers" in actions


def main() -> int:
    cases = (
        test_negotiate_python_capabilities,
        test_negotiate_unsupported_route,
        test_plan_single_file_verification,
        test_plan_cross_language_verification,
    )
    for c in cases:
        c()
    print("polyglot_plan_test: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
