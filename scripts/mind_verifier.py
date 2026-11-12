"""Optional entitlement verification for customer-controlled Mind execution, and the Action's key activation."""

import argparse
import http.client
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPMessage
from typing import IO, Any

HOSTED = "https://headron.tech/api/mind"
# The service answers a key with one of these; any other pairing of status and body is not an answer.
KEY_STATES = {200: "active", 401: "invalid key", 402: "no active plan"}
CLASSIFY_BATCH = 400  # paths per classifier call, well under the argument-length limit
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
    if url and key_state(url, os.environ.get("HEADRON_MIND_KEY", "").strip()) != "active":
        # Neither credentials, endpoint details, nor provider response bodies belong in MCP errors.
        raise ValueError("Mind key verification failed or is unavailable")


def hosted_plan(base: str, key: str, change_class: str, risk_modifiers: list[str]) -> dict[str, Any]:
    """The gates hosted Mind requires for one declared class. A refusal names the class and the HTTP status only."""
    body: dict[str, Any] = {"change_class": change_class}
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
        or not isinstance(gates, list)
        or not all(isinstance(gate, str) and NAME.fullmatch(gate) for gate in gates)
        or not isinstance(revision, str)
        or not NAME.fullmatch(revision)
    ):
        raise ValueError(f"hosted Mind refused the plan for {change_class} (HTTP {status})")
    return {"required_gates": gates, "policy_revision": revision}


def hosted_gates(base: str, key: str, classes: list[str], risk_modifiers: list[str]) -> tuple[list[str], list[str]]:
    """Every class planned once: (gates in first-seen order, policy revisions seen)."""
    gates: list[str] = []
    revisions: list[str] = []
    for change_class in classes:
        result = hosted_plan(base, key, change_class, risk_modifiers)
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
    key = os.environ.get("HEADRON_MIND_KEY", "").strip()
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
    return _activate(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
