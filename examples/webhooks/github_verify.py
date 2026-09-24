"""Minimal GitHub webhook HMAC-SHA256 verification."""

import hashlib
import hmac


def verify_github_signature(raw_body: bytes, secret: bytes, header: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret, raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header)


# Verify the raw body before parsing JSON or doing expensive work.

if __name__ == "__main__":
    # A VERIFIER WITH NO TEST IS A CLAIM. Each case below is a way this function is got wrong in
    # production: comparing after parsing, comparing with ==, or accepting a header shape it never
    # checked.
    body = b'{"zen":"Non-blocking is better than blocking."}'
    secret = b"a-test-secret-never-a-real-one"
    good = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()

    assert verify_github_signature(body, secret, good), "a correct signature must verify"
    assert not verify_github_signature(body + b" ", secret, good), "a changed body must not verify"
    assert not verify_github_signature(body, b"wrong-secret", good), "a wrong secret must not verify"
    assert not verify_github_signature(body, secret, good[:-1]), "a truncated digest must not verify"
    assert not verify_github_signature(body, secret, good.replace("sha256=", "")), \
        "a header with no algorithm prefix must not verify"
    print("github_verify: 5 assertions held — body, secret, digest and prefix all decide the verdict")
