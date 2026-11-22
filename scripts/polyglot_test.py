"""Tests for Headron polyglot capability resolver and boundary detector."""

from __future__ import annotations

import tempfile
from pathlib import Path

from capability_catalog import (
    COMPILE_OR_TYPECHECK,
    EXECUTE_TESTS,
    IDENTIFY_LANGUAGE,
    PRODUCE_EVIDENCE,
    get_capability,
    is_valid_capability,
    list_capabilities,
)
from polyglot import capabilities, explain, inspect
from polyglot_boundary import detect_cross_language_contracts


def test_capability_catalog_completeness():
    caps = list_capabilities()
    assert len(caps) >= 12
    for cap in caps:
        assert is_valid_capability(cap.capability)
        assert cap.contract_version == 1
        assert len(cap.name) > 0
        assert cap.result_schema.startswith("headron.")


def test_capability_lookup():
    cap = get_capability(IDENTIFY_LANGUAGE)
    assert cap is not None
    assert cap.name == "language.identify"
    assert "file_path" in cap.requires


def test_polyglot_inspect_temp_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create python and typescript boundaries
        (root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
        (root / "web").mkdir()
        (root / "web/package.json").write_text('{"name": "web"}', encoding="utf-8")

        fp = inspect(root)
        assert fp["schema"] == 1
        assert fp["kind"] == "headron.polyglot"
        assert "python" in fp["languages"]
        assert "typescript" in fp["languages"]
        assert len(fp["boundaries"]) == 2
        assert IDENTIFY_LANGUAGE in fp["capabilities_available"]
        assert PRODUCE_EVIDENCE in fp["capabilities_available"]


def test_cross_language_boundary_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Create an openapi schema and a sql migration
        (root / "api").mkdir()
        (root / "api/openapi.json").write_text('{"openapi": "3.0.0"}', encoding="utf-8")
        (root / "db/migrations").mkdir(parents=True)
        (root / "db/migrations/001_init.sql").write_text("CREATE TABLE users (id INT);", encoding="utf-8")

        contracts = detect_cross_language_contracts(root)
        types = [c.contract_type for c in contracts]
        assert "api_schema" in types
        assert "database_migration" in types


def test_deterministic_explanation():
    fp = {
        "capabilities_available": [IDENTIFY_LANGUAGE, PRODUCE_EVIDENCE],
        "capabilities_unavailable": [COMPILE_OR_TYPECHECK],
    }
    exp_avail = explain(fp, IDENTIFY_LANGUAGE)
    assert exp_avail["status"] == "available"
    assert "language.identify" in exp_avail["name"]

    exp_unavail = explain(fp, COMPILE_OR_TYPECHECK)
    assert exp_unavail["status"] == "unavailable"
    assert "prerequisites_needed" in exp_unavail


def test_planted_defect_missing_tool_unavailable():
    """Verify that absent tools never produce false positive availability."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        caps_map = capabilities(root)
        # In an empty directory with no manifests, compile and test are unavailable
        assert caps_map[EXECUTE_TESTS]["status"] == "unavailable"
        assert caps_map[COMPILE_OR_TYPECHECK]["status"] == "unavailable"


def main() -> int:
    cases = (
        test_capability_catalog_completeness,
        test_capability_lookup,
        test_polyglot_inspect_temp_repo,
        test_cross_language_boundary_detection,
        test_deterministic_explanation,
        test_planted_defect_missing_tool_unavailable,
    )
    for fn in cases:
        fn()
    print(f"polyglot_test: {len(cases)} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
