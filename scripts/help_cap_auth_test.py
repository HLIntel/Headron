"""Tests for capability authorization, idempotency, and location selection."""

from __future__ import annotations

from capability_catalog import COMPILE_OR_TYPECHECK, EXECUTE_TESTS, EXPLAIN_RESULT, IDENTIFY_LANGUAGE
from help_cap_auth import authorize_capability, compute_idempotency_token, select_execution_location


def test_authorization_matrix():
    # Trust plan permits language identification and explanations
    a_trust = authorize_capability(IDENTIFY_LANGUAGE, plan="trust", runtime="browser")
    assert a_trust["authorized"] is True

    # Trust plan refuses execution (compilation)
    a_compile_trust = authorize_capability(COMPILE_OR_TYPECHECK, plan="trust", runtime="local_driver")
    assert a_compile_trust["authorized"] is False
    assert "requires Pro or Team" in a_compile_trust["reason"]

    # Pro plan with local driver permits compilation
    a_compile_pro = authorize_capability(COMPILE_OR_TYPECHECK, plan="pro", runtime="local_driver")
    assert a_compile_pro["authorized"] is True


def test_browser_execution_restriction():
    # Browser runtime cannot directly execute tests even on Pro
    a_browser_tests = authorize_capability(EXECUTE_TESTS, plan="pro", runtime="browser")
    assert a_browser_tests["authorized"] is False
    assert "authorized local or hosted driver" in a_browser_tests["reason"]


def test_idempotency_tokens():
    args1 = {"file": "main.go", "flags": ["-v"]}
    args2 = {"flags": ["-v"], "file": "main.go"}  # key order difference
    token1 = compute_idempotency_token(EXECUTE_TESTS, args1, context_digest="abc")
    token2 = compute_idempotency_token(EXECUTE_TESTS, args2, context_digest="abc")
    assert token1 == token2
    assert len(token1) == 64


def test_location_selection():
    loc_inspect = select_execution_location(EXPLAIN_RESULT, ["browser", "local_driver"])
    assert loc_inspect == "browser"

    loc_test = select_execution_location(EXECUTE_TESTS, ["browser", "local_driver"])
    assert loc_test == "local_driver"


def main() -> int:
    cases = (
        test_authorization_matrix,
        test_browser_execution_restriction,
        test_idempotency_tokens,
        test_location_selection,
    )
    for c in cases:
        c()
    print(f"cap_auth_test: {len(cases)} cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
