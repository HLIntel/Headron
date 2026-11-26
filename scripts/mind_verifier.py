"""Optional entitlement verification for customer-controlled Mind execution, and the Action's key activation."""

import argparse
import base64
import hashlib
import http.client
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPMessage
from pathlib import Path
from typing import IO, Any

import receipt
from resilience import wait_until

HOSTED = "https://headron.tech/api/mind"
SITE_ORIGIN = "https://headron.tech"
# The service answers a key with one of these; any other pairing of status and body is not an answer.
KEY_STATES = {200: "active", 401: "invalid key", 402: "no active plan"}
CLASSIFY_BATCH = 400  # paths per classifier call, well under the argument-length limit
PLAN_BATCH = 8  # classes per hosted plan request: the service refuses a longer list
NAME = re.compile(r"[A-Za-z0-9_.-]{1,128}")
COMMIT = re.compile(r"[0-9a-f]{40,64}")
UNREACHABLE = (OSError, http.client.HTTPException)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so an API key cannot be forwarded to another endpoint."""

    def redirect_request(
        self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage, newurl: str
    ):
        return None


def hosted_config() -> tuple[str | None, str | None]:
    """Return (url, token_or_key) for hosted Mind REST API if configured, else (None, None).

    Supports short-lived session tokens (HEADRON_MIND_TOKEN) or legacy keys (HEADRON_MIND_KEY).
    """
    url = os.environ.get("HEADRON_MIND_URL")
    key = os.environ.get("HEADRON_MIND_TOKEN") or os.environ.get("HEADRON_MIND_KEY")
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


def _post(url: str, key: str, body: bytes, limit: int = 4096) -> tuple[int, dict[str, Any] | None]:
    """POST with the key as a bearer token: (HTTP status, JSON object or None). Raises when nothing answers."""
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    if body:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=5) as response:
            status, raw = response.status, response.read(limit + 1)
    except urllib.error.HTTPError as error:
        with error:
            status, raw = error.code, error.read(limit + 1)
    if len(raw) > limit:
        return status, None
    try:
        parsed = json.loads(raw)
    except ValueError:
        return status, None
    return status, parsed if isinstance(parsed, dict) else None


def key_state(url: str, key: str) -> str:
    """active, invalid key, no active plan, or unavailable: this module's words, never the provider's."""
    if not key or url_refusal(url):
        return "unavailable"
    try:
        status, result = _post(url, key, b"")
    except (*UNREACHABLE, ValueError, TypeError):
        return "unavailable"
    state = KEY_STATES.get(status)
    return state if state and result is not None and result.get("status") == state else "unavailable"


def verify_key() -> None:
    """When configured, ask the entitlement service before executing a Mind tool."""
    url = os.environ.get("HEADRON_MIND_VERIFIER_URL", "").strip()
    key = (os.environ.get("HEADRON_MIND_TOKEN") or os.environ.get("HEADRON_MIND_KEY") or "").strip()
    if url and key_state(url, key) != "active":
        # Neither credentials, endpoint details, nor provider response bodies belong in MCP errors.
        raise ValueError("Mind key verification failed or is unavailable")


def hosted_plan(base: str, key: str, classes: list[str], risk_modifiers: list[str]) -> dict[str, Any]:
    """The gates hosted Mind requires for these declared classes, asked in ONE request.

    A refusal names the classes and the HTTP status only. An answer for other classes than the ones asked is refused."""
    body: dict[str, Any] = {"change_classes": classes}
    if risk_modifiers:
        body["risk_modifiers"] = risk_modifiers
    try:
        status, result = _post(f"{base}/plan", key, json.dumps(body).encode(), 65536)
    except UNREACHABLE:
        raise ValueError("hosted Mind plan is unavailable") from None
    gates = result.get("required_gates") if result else None
    revision = result.get("policy_revision") if result else None
    if (
        status != 200
        or result is None
        or result.get("change_classes") != classes
        or not isinstance(gates, list)
        or not all(isinstance(gate, str) and NAME.fullmatch(gate) for gate in gates)
        or not isinstance(revision, str)
        or not NAME.fullmatch(revision)
    ):
        raise ValueError(f"hosted Mind refused the plan for {', '.join(classes)} (HTTP {status})")
    return {"required_gates": gates, "policy_revision": revision}


def hosted_gates(base: str, key: str, classes: list[str], risk_modifiers: list[str]) -> tuple[list[str], list[str]]:
    """Every class planned in as few requests as the service takes: (gates in first-seen order, revisions seen)."""
    gates: list[str] = []
    revisions: list[str] = []
    for start in range(0, len(classes), PLAN_BATCH):
        result = hosted_plan(base, key, classes[start : start + PLAN_BATCH], risk_modifiers)
        gates += [gate for gate in result["required_gates"] if gate not in gates]
        if result["policy_revision"] not in revisions:
            revisions.append(result["policy_revision"])
    return gates, revisions


def _run(argv: list[str]) -> str | None:
    """stdout of a child process that is never handed the key, or None when it did not succeed."""
    env = {name: value for name, value in os.environ.items() if not name.startswith("HEADRON_MIND_")}
    try:
        done = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


def changed_files(event_path: str) -> list[str] | None:
    """Paths that differ between the event's base commit and HEAD, or None when that cannot be told."""
    try:
        with open(event_path, encoding="utf-8") as handle:
            event = json.load(handle)
        base = ((event.get("pull_request") or {}).get("base") or {}).get("sha") or event.get("before")
    except (OSError, ValueError, AttributeError):
        return None
    # A NEW BRANCH PUSHES AN ALL-ZERO `before`: THERE IS NO BASE, AND AN EMPTY LIST WOULD READ AS "NOTHING CHANGED".
    if not isinstance(base, str) or not COMMIT.fullmatch(base) or not base.strip("0"):
        return None
    diff = ["git", "diff", "--name-only", "-z", base, "HEAD", "--"]
    out = _run(diff)
    if out is None and _run(["git", "fetch", "--no-tags", "--depth=1", "origin", base]) is not None:
        out = _run(diff)  # a depth-1 checkout does not hold the base commit until it is fetched
    return None if out is None else [path for path in out.split("\0") if path]


def local_classes(files: list[str]) -> list[str] | None:
    """Change classes the installed headron infers for the files: [] when it names none, None when it failed."""
    found: list[str] = []
    for start in range(0, len(files), CLASSIFY_BATCH):
        out = _run(["headron", "mind", "--classify", "--json", "--", *files[start : start + CLASSIFY_BATCH]])
        try:
            result = json.loads(out or "")
        except ValueError:
            return None
        if not isinstance(result, dict) or not isinstance(result.get("category"), str):
            return None
        if result.get("unknown"):
            continue
        names = result.get("classes") or [result["category"]]
        if not isinstance(names, list) or not all(isinstance(name, str) and NAME.fullmatch(name) for name in names):
            return None
        found += [name for name in names if name not in found]
    return found


def _report(args: argparse.Namespace, status: str, classes: list[str], gates: list[str], revisions: list[str]) -> None:
    """One result, three readers: the log, the step outputs, and the job summary."""
    outputs = {
        "mind-status": status,
        "change-classes": ",".join(classes),
        "required-gates": ",".join(gates),
        "policy-revision": ",".join(revisions),
    }
    print(f"Hosted Mind: {status}")
    if args.output:
        with open(args.output, "a", encoding="utf-8") as handle:
            handle.writelines(f"{name}={value}\n" for name, value in outputs.items())
    if status != "active":
        return
    plan = [
        f"- Change classes: {', '.join(classes) or 'none inferred'}",
        f"- Required gates: {', '.join(gates) or 'none'}",
        f"- Policy revision: {', '.join(revisions) or 'none'}",
    ]
    print("\n".join(plan))
    if args.summary:
        scope = "The plan lists the gates for the inferred classes. This step does not run them."
        with open(args.summary, "a", encoding="utf-8") as handle:
            handle.write("\n".join(["### Hosted Mind plan", "", *plan, "", scope, ""]))


def _activate(args: argparse.Namespace) -> int:
    key = (os.environ.get("HEADRON_MIND_TOKEN") or os.environ.get("HEADRON_MIND_KEY") or "").strip()
    if not key:
        _report(args, "inactive", [], [], [])
        return 0
    base = args.url.strip().rstrip("/")
    refusal = url_refusal(base)
    if refusal:
        print(f"mind-url {refusal}", file=sys.stderr)
        return 1
    state = key_state(f"{base}/verify", key)
    if state != "active":
        _report(args, state, [], [], [])
        return 1
    files = [line.strip() for line in args.files.splitlines() if line.strip()] or changed_files(args.event)
    if files is None:
        print("cannot tell which files changed: set mind-files, or check out with fetch-depth: 0", file=sys.stderr)
        return 1
    classes = local_classes(files) if files else []
    if classes is None:
        print("headron could not classify the changed files", file=sys.stderr)
        return 1
    modifiers = [name for name in re.split(r"[\s,]+", args.risk_modifiers) if name]
    try:
        gates, revisions = hosted_gates(base, key, classes, modifiers)
    except ValueError as refused:
        print(str(refused), file=sys.stderr)
        return 1
    _report(args, "active", classes, gates, revisions)
    return 0


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _device_path() -> Path:
    root = os.environ.get("HEADRON_HOME")
    base = Path(root) if root else Path.home() / ".headron"
    return base / "device.json"


def _save_device(record: dict[str, Any]) -> None:
    path = _device_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def _read_text(path: Path) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _generate_p256_key() -> tuple[str, dict[str, str]]:
    """Generate a P-256 keypair via openssl (no pip dependencies); return (private_pem, public_jwk)."""
    with tempfile.TemporaryDirectory(prefix="headron-key-") as tmp:
        key_file = Path(tmp) / "key.pem"
        subprocess.run(
            ["openssl", "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", str(key_file)],
            check=True,
            capture_output=True,
            timeout=15,
        )
        pub_der = subprocess.run(
            ["openssl", "ec", "-in", str(key_file), "-pubout", "-outform", "DER"],
            check=True,
            capture_output=True,
            timeout=15,
        ).stdout
        pem = _read_text(key_file)
    if len(pub_der) < 65 or pub_der[-65] != 0x04:
        raise ValueError("unexpected P-256 SPKI public key encoding")
    point = pub_der[-64:]
    jwk = {"kty": "EC", "crv": "P-256", "x": _b64url(point[:32]), "y": _b64url(point[32:])}
    return pem, jwk


def _der_ecdsa_to_p1363(der: bytes) -> bytes:
    """Convert ASN.1 DER ECDSA (r, s) signature to IEEE P1363 64-byte (r || s) for ES256 JWT."""
    if len(der) < 8 or der[0] != 0x30:
        raise ValueError("invalid DER signature")
    idx = 2 if der[1] < 0x80 else 2 + (der[1] & 0x7F)
    coords = []
    for _ in range(2):
        if der[idx] != 0x02:
            raise ValueError("expected ASN.1 INTEGER")
        length = der[idx + 1]
        raw = der[idx + 2 : idx + 2 + length].lstrip(b"\x00")
        if len(raw) > 32:
            raise ValueError("ECDSA integer exceeds 32 bytes")
        coords.append(raw.rjust(32, b"\x00"))
        idx += 2 + length
    return coords[0] + coords[1]


def _dpop_proof(private_pem: str, jwk: dict[str, str], method: str, url: str, access_token: str | None = None) -> str:
    header = _b64url(json.dumps({"typ": "dpop+jwt", "alg": "ES256", "jwk": jwk}, separators=(",", ":")).encode())
    claims: dict[str, Any] = {
        "jti": secrets.token_hex(16),
        "htm": method.upper(),
        "htu": url.split("?", 1)[0].split("#", 1)[0],
        "iat": int(time.time()),
    }
    if access_token:
        claims["ath"] = _b64url(hashlib.sha256(access_token.encode("ascii")).digest())
    payload = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode("ascii")
    with tempfile.TemporaryDirectory(prefix="headron-dpop-") as tmp:
        key_file = Path(tmp) / "k.pem"
        key_file.write_text(private_pem, encoding="ascii")
        os.chmod(key_file, 0o600)
        der = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", str(key_file)],
            input=signing_input,
            check=True,
            capture_output=True,
            timeout=15,
        ).stdout
    sig = _b64url(_der_ecdsa_to_p1363(der))
    return f"{header}.{payload}.{sig}"


def _json_request(
    url: str,
    payload: dict[str, Any] | None,
    *,
    method: str = "POST",
    headers: dict[str, str] | None = None,
    timeout: int = 15,
) -> tuple[int, dict[str, Any] | None]:
    req_headers = {"Accept": "application/json", **(headers or {})}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as resp:
            status, raw = resp.status, resp.read(65537)
    except urllib.error.HTTPError as err:
        with err:
            status, raw = err.code, err.read(65537)
    if len(raw) > 65536:
        return status, None
    try:
        parsed = json.loads(raw)
    except ValueError:
        return status, None
    return status, parsed if isinstance(parsed, dict) else None


def _ensure_dpop_token(device: dict[str, Any], origin: str) -> dict[str, Any] | None:
    if device.get("access_token") and time.time() < float(device.get("exp") or 0) - 30:
        return device
    token_url = f"{origin}/api/connect/token"
    proof = _dpop_proof(device["private_pem"], device["jwk"], "POST", token_url)
    status, data = _json_request(token_url, {"device_id": device["device_id"]}, headers={"DPoP": proof})
    if status != 200 or not data or not data.get("access_token"):
        return None
    updated = {
        **device,
        "access_token": data["access_token"],
        "exp": int(time.time()) + int(data.get("expires_in") or 900),
    }
    _save_device(updated)
    return updated


def upload_receipt(
    receipt_data: dict[str, Any], *, url: str | None = None, subject: str | None = None
) -> tuple[bool, str]:
    """Upload a verified receipt via paired DPoP device or HEADRON_MIND_KEY / HEADRON_MIND_TOKEN."""
    origin = (url or os.environ.get("HEADRON_MIND_URL") or SITE_ORIGIN).strip().rstrip("/")
    parsed = urllib.parse.urlsplit(origin)
    base_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else origin
    if refusal := url_refusal(base_origin):
        return False, f"upload url {refusal}"
    device_file = _device_path()
    if device_file.is_file():
        try:
            device = json.loads(_read_text(device_file))
        except (OSError, ValueError):
            device = None
        if isinstance(device, dict) and device.get("device_id") and device.get("private_pem") and device.get("jwk"):
            fresh = _ensure_dpop_token(device, base_origin)
            if not fresh:
                return False, "paired device token renewal failed; run `headron` connect again"
            target = f"{base_origin}/api/trust/receipts"
            proof = _dpop_proof(fresh["private_pem"], fresh["jwk"], "POST", target, fresh["access_token"])
            body = {"receipt": receipt_data, **({"subject": subject} if subject else {})}
            status, data = _json_request(
                target, body, headers={"Authorization": f"DPoP {fresh['access_token']}", "DPoP": proof}
            )
            if status == 200 and data:
                kind = "already recorded" if data.get("duplicate") else "recorded"
                return True, f"uploaded via paired device ({kind}: {str(data.get('id') or '')[:12]})"
            err = (data or {}).get("error_description") or (data or {}).get("error") or f"HTTP {status}"
            return False, f"device upload refused: {err}"
    key = (os.environ.get("HEADRON_MIND_TOKEN") or os.environ.get("HEADRON_MIND_KEY") or "").strip()
    if key:
        mcp_url = f"{base_origin}/mcp"
        rpc = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "receipt.upload",
                "arguments": {"receipt": receipt_data, **({"subject": subject} if subject else {})},
            },
        }
        status, data = _json_request(
            mcp_url, rpc, headers={"Authorization": f"Bearer {key}", "Accept": "application/json, text/event-stream"}
        )
        res = (data or {}).get("result") or {}
        if status == 200 and not res.get("isError") and not (data or {}).get("error"):
            return True, f"uploaded via Mind key ({str(receipt_data.get('receipt_id') or '')[:12]})"
        msg = ((res.get("content") or [{}])[0] or {}).get("text") or ((data or {}).get("error") or {}).get("message")
        return False, f"Mind key upload failed: {msg or f'HTTP {status}'}"
    return False, "not configured: pair a device (`mind_verifier.py connect`) or set HEADRON_MIND_KEY"


def finish_verify_receipt(
    receipt_to: Path | None,
    push: bool,
    live_stream: bool,
    rows: list[dict[str, Any]],
    pin: dict[str, Any] | None,
    tree: str,
    tree_root: Path,
    changed: list[str],
) -> dict[str, Any]:
    """Build, optionally write to disk, and optionally push the run's receipt, returning the report binding."""
    rid = None
    if (receipt_to or push) and pin:
        extra = receipt.verify_context(tree_root, rows, changed)
        body = receipt.build(
            rows, base_commit=pin["base_commit"], policy_digest=pin["digest"], input_digest=tree, **extra
        )
        rid = body["receipt_id"]
        if receipt_to is not None:
            receipt_to.write_text(receipt.dumps(body), encoding="utf-8")
        if push:
            ok, msg = upload_receipt(dict(body))
            if live_stream:
                print(f"verify push: {'OK' if ok else 'FAIL'} — {msg}", file=sys.stdout if ok else sys.stderr)
    return {
        "base": pin["base_commit"] if pin else None,
        "policy_digest": pin["digest"] if pin else None,
        "input_digest": tree,
        "receipt_id": rid,
    }


def _connect(args: argparse.Namespace) -> int:
    origin = args.url.strip().rstrip("/")
    if refusal := url_refusal(origin):
        print(f"connect url {refusal}", file=sys.stderr)
        return 1
    pem, jwk = _generate_p256_key()
    name = (args.name or socket.gethostname() or "headron-cli")[:64]
    status, start = _json_request(
        f"{origin}/api/connect/start", {"jwk": jwk, "name": name, "scopes": ["receipt_verification", "mind_api"]}
    )
    if status != 200 or not start or not start.get("device_code"):
        print(f"connect start failed (HTTP {status})", file=sys.stderr)
        return 1
    print(f"Open: {start.get('verification_uri_complete') or start.get('verification_uri')}")
    print(f"Code: {start.get('user_code')}")
    interval = max(1, int(start.get("interval") or 5))
    timeout = max(interval, int(start.get("expires_in") or 300))
    token_url = f"{origin}/api/connect/token"
    outcome: dict[str, Any] = {"code": 1}

    def _poll() -> bool:
        proof = _dpop_proof(pem, jwk, "POST", token_url)
        t_status, tok = _json_request(token_url, {"device_code": start["device_code"]}, headers={"DPoP": proof})
        if t_status == 200 and tok and tok.get("access_token"):
            _save_device(
                {
                    "device_id": tok["device_id"],
                    "url": origin,
                    "access_token": tok["access_token"],
                    "exp": int(time.time()) + int(tok.get("expires_in") or 900),
                    "private_pem": pem,
                    "jwk": jwk,
                }
            )
            print(f"Paired device {tok['device_id']} -> {_device_path()}")
            outcome["code"] = 0
            return True
        err = (tok or {}).get("error")
        if err not in (None, "authorization_pending", "slow_down"):
            print(f"Pairing refused: {err}", file=sys.stderr)
            outcome["code"] = 1
            return True
        return False

    if not wait_until(_poll, timeout=timeout, interval=interval):
        print("Pairing timed out", file=sys.stderr)
    return int(outcome["code"])


def _push(args: argparse.Namespace) -> int:
    path = Path(args.file)
    try:
        data = json.loads(_read_text(path))
    except (OSError, ValueError) as exc:
        print(f"cannot read receipt {path}: {exc}", file=sys.stderr)
        return 1
    ok, msg = upload_receipt(data, url=args.url or None, subject=args.subject or None)
    print(msg, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mind_verifier.py", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    activate = commands.add_parser("activate", help="check HEADRON_MIND_KEY, then plan the changed files' gates")
    activate.add_argument("--url", default=HOSTED, help="hosted Mind base URL")
    activate.add_argument("--files", default="", help="changed files, one per line; empty reads --event")
    activate.add_argument("--risk-modifiers", default="", help="risk modifiers to declare, comma separated")
    activate.add_argument("--event", default="", help="path to the GitHub event payload")
    activate.add_argument("--output", default="", help="path to append step outputs to")
    activate.add_argument("--summary", default="", help="path to append the job summary to")
    connect = commands.add_parser("connect", help="pair this device via RFC 8628 + DPoP with headron.tech")
    connect.add_argument("--url", default=SITE_ORIGIN, help="hosted Headron origin")
    connect.add_argument("--name", default="", help="device label (default hostname)")
    push = commands.add_parser("push", help="upload a receipt JSON file to hosted Headron workspace")
    push.add_argument("file", help="path to verify.json receipt")
    push.add_argument("--url", default="", help="hosted Headron origin override")
    push.add_argument("--subject", default="", help="optional subject label")
    parsed = parser.parse_args(argv)
    if parsed.command == "connect":
        return _connect(parsed)
    if parsed.command == "push":
        return _push(parsed)
    return _activate(parsed)


if __name__ == "__main__":
    raise SystemExit(main())
