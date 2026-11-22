"""Headron Help sensitive result redactor (contract v1).

Scrubs API keys, bearer tokens, private keys, passwords, and sensitive credentials
from strings and structured records before rendering in Help or serializing receipts.
"""

from __future__ import annotations

import re
from typing import Any

# Compiled regex patterns for credential shapes
_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{16,}", re.ASCII),
    re.compile(r"(?i)(api[_\-]?key\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]{16,}['\"]?", re.ASCII),
    re.compile(r"(?i)(password\s*[:=]\s*['\"]?)[^\s'\"]{6,}['\"]?", re.ASCII),
    re.compile(r"(?i)(secret\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]{16,}['\"]?", re.ASCII),
    re.compile(r"ghp_[a-zA-Z0-9]{36}", re.ASCII),  # GitHub personal access token
    re.compile(r"gho_[a-zA-Z0-9]{36}", re.ASCII),  # GitHub OAuth access token
    re.compile(r"glpat-[a-zA-Z0-9_\-]{20,}", re.ASCII),  # GitLab personal access token
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC )?PRIVATE KEY-----"),
)


def redact_text(text: str) -> str:
    """Scrub credential and token occurrences from text."""
    if not text:
        return ""
    result = text
    for pattern in _PATTERNS:
        result = pattern.sub(r"\1[REDACTED]" if pattern.groups > 0 else "[REDACTED]", result)
    return result


def redact_record(record: Any) -> Any:
    """Recursively scrub sensitive keys and credential patterns in nested structures."""
    if isinstance(record, str):
        return redact_text(record)
    if isinstance(record, dict):
        scrubbed: dict[str, Any] = {}
        for k, v in record.items():
            key_lower = str(k).lower()
            if any(s in key_lower for s in ("secret", "token", "password", "auth", "private_key")):
                scrubbed[k] = "[REDACTED]"
            else:
                scrubbed[k] = redact_record(v)
        return scrubbed
    if isinstance(record, list):
        return [redact_record(item) for item in record]
    return record
