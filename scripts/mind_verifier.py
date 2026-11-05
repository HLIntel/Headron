"""Optional entitlement verification for customer-controlled Mind execution."""

import http.client
import json
import os
import urllib.parse
import urllib.request
from http.client import HTTPMessage
from typing import IO


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so an API key cannot be forwarded to another endpoint."""

    def redirect_request(
        self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage, newurl: str
    ):
        return None


def hosted_config() -> tuple[str | None, str | None]:
    """Return (url, key) for hosted Mind REST API if configured, else (None, None)."""
    url = os.environ.get("HEADRON_MIND_URL")
    key = os.environ.get("HEADRON_MIND_KEY")
    clean_url = url.strip() if url and url.strip() else None
    clean_key = key.strip() if key and key.strip() else None
    if clean_url and urllib.parse.urlsplit(clean_url).scheme not in ("http", "https"):
        raise ValueError(f"HEADRON_MIND_URL must be http or https, got {clean_url.split(':', 1)[0]!r}")
    return clean_url, clean_key


def url_refusal(url: str) -> str | None:
    """Why a Mind endpoint is not one to send a key to, or None. Plain http only ever reaches this machine."""
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        return "must be an http or https URL without credentials, query, or fragment"
    if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        return "requires https except on loopback"
    return None


def verify_key() -> None:
    """When configured, ask the entitlement service before executing a Mind tool."""
    url = os.environ.get("HEADRON_MIND_VERIFIER_URL", "").strip()
    if not url:
        return
    key = os.environ.get("HEADRON_MIND_KEY", "").strip()
    try:
        if not key or url_refusal(url):
            raise ValueError
        request = urllib.request.Request(
            url, data=b"", headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}, method="POST"
        )
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=5) as response:
            raw = response.read(4097)
            if response.status != 200 or len(raw) > 4096:
                raise ValueError
            result = json.loads(raw)
            if not isinstance(result, dict) or result.get("status") != "active":
                raise ValueError
    except (ValueError, OSError, TypeError, http.client.HTTPException):
        # Neither credentials, endpoint details, nor provider response bodies belong in MCP errors.
        raise ValueError("Mind key verification failed or is unavailable") from None
