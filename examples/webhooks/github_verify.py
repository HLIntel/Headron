"""Minimal GitHub webhook HMAC-SHA256 verification."""

import hashlib
import hmac


def verify_github_signature(raw_body: bytes, secret: bytes, header: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret, raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header)


# Verify the raw body before parsing JSON or doing expensive work.