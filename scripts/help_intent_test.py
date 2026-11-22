"""Tests for Headron Help model-free intent compiler and sensitive redactor."""

from __future__ import annotations

from capability_catalog import ANALYZE_SECURITY, COMPILE_OR_TYPECHECK, EXECUTE_TESTS, FORMAT_CODE, TRACE_BOUNDARY
from help_intent import compile_intent, rank_questions, render_explanation
from help_redact import redact_record, redact_text


def test_intent_compilation_direct():
    r1 = compile_intent("run the pytest test suite")
    assert r1.capability == EXECUTE_TESTS
    assert r1.confidence == "confirmed"

    r2 = compile_intent("typecheck and build typescript code")
    assert r2.capability == COMPILE_OR_TYPECHECK
    assert r2.confidence == "confirmed"

    r3 = compile_intent("run ruff format style check")
    assert r3.capability == FORMAT_CODE
    assert r3.confidence == "confirmed"

    r4 = compile_intent("scan for vulnerabilities and cve security issues")
    assert r4.capability == ANALYZE_SECURITY
    assert r4.confidence == "confirmed"

    r5 = compile_intent("trace openapi and grpc boundaries")
    assert r5.capability == TRACE_BOUNDARY
    assert r5.confidence == "confirmed"


def test_intent_slot_recall():
    slots = {"last_capability": EXECUTE_TESTS, "selected_file": "tests/test_app.py"}
    intent = compile_intent("run it again", slots=slots)
    assert intent.capability == EXECUTE_TESTS
    assert intent.confidence == "confirmed"


def test_page_aware_question_ranking():
    q_overview = rank_questions("overview")
    assert len(q_overview) == 3
    assert any("checks" in q for q in q_overview)

    q_receipt = rank_questions("receipt")
    assert len(q_receipt) == 3
    assert any("signature" in q or "fail" in q for q in q_receipt)

    slots = {"selected_file": "main.go"}
    q_file = rank_questions("overview", slots=slots)
    assert "main.go" in q_file[0]


def test_sensitive_text_redaction():
    fake_pat = "gh" + "p_" + "1" * 36
    fake_key = "abc" + "def" + "0" * 16
    text = f"Authorization: Bearer {fake_pat} and api_key='{fake_key}'"
    redacted = redact_text(text)
    assert "ghp_" not in redacted
    assert fake_key not in redacted
    assert "[REDACTED]" in redacted


def test_sensitive_record_redaction():
    fake_secret = "super" + "secret" + "999"
    fake_tok = "tok" + "_" + "12345" + "abcdef"
    record = {
        "user": "developer",
        "api_secret": fake_secret,
        "nested": {"token": fake_tok, "safe_field": "public_data"},
    }
    scrubbed = redact_record(record)
    assert scrubbed["api_secret"] == "[REDACTED]"
    assert scrubbed["nested"]["token"] == "[REDACTED]"
    assert scrubbed["nested"]["safe_field"] == "public_data"


def test_deterministic_explanation_rendering():
    intent = compile_intent("run tests")
    rendered = render_explanation(intent, "PASS", ["gate: unit_tests passed in 1.2s"])
    assert "tests.execute" in rendered
    assert "PASS" in rendered
    assert "unit_tests passed" in rendered


def main() -> int:
    test_intent_compilation_direct()
    test_intent_slot_recall()
    test_page_aware_question_ranking()
    test_sensitive_text_redaction()
    test_sensitive_record_redaction()
    test_deterministic_explanation_rendering()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
