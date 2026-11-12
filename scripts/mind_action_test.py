#!/usr/bin/env python3
"""Planted case: the Action's Mind step stays silent without a key, plans once per class with one, and refuses the rest."""

from __future__ import annotations

import http.server
import json
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from types import ModuleType
from unittest import mock

KEY = "test-private-key"
PLAN = {"required_gates": ["formatter", "unit_tests"], "policy_revision": "r1"}
ACTIVE = {"/verify": (200, b'{"status":"active"}'), "/plan": (200, json.dumps(PLAN).encode())}
CLASSIFIED = '{"category":"source_change","classes":["api_change","dependency_change"]}'
# Each of these must end the step at exit 1 with no plan reported.
REFUSALS: tuple[tuple[str, tuple[str, ...], dict[str, tuple[int, bytes]]], ...] = (
    ("a key the service calls invalid", (), {"/verify": (401, b'{"status":"invalid key"}')}),
    ("a status and body that disagree", (), {"/verify": (200, b'{"status":"invalid key"}')}),
    ("a plan the service refused", ("--files", "a.py"), {"/plan": (400, b'{"error":"x"}')}),
    (
        "a gate name carrying a second output line",
        ("--files", "a.py"),
        {"/plan": (200, b'{"required_gates":["a\\nb=c"],"policy_revision":"r1"}')},
    ),
    ("a change set nothing names", (), {}),
)


def activation_case(module: ModuleType) -> None:
    """The key gates the hosted plan: no key asks nothing, an active key plans, anything else stops the step."""
    import mind_verifier

    requests: list[tuple[str, str, bytes]] = []
    replies: dict[str, tuple[int, bytes]] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            requests.append((self.path, self.headers.get("Authorization", ""), body))
            status, answer = replies[self.path]
            self.send_response(status)
            self.end_headers()
            self.wfile.write(answer)

        def log_message(self, format: str, *args: object):
            pass

    listener = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=listener.serve_forever, daemon=True)
    thread.start()
    classifier = subprocess.CompletedProcess([], 0, CLASSIFIED, "")
    try:
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(mind_verifier, "print", create=True),
            mock.patch.object(mind_verifier.subprocess, "run", return_value=classifier) as child,
        ):
            out = Path(tmp) / "out"
            fixed = ["--url", f"http://127.0.0.1:{listener.server_port}", "--output", str(out)]

            def activate(key: str, *extra: str, **changed: tuple[int, bytes]) -> tuple[int, str]:
                replies.clear()
                replies.update(ACTIVE | changed)
                del requests[:]
                out.write_text("")
                with mock.patch.dict(os.environ, {"HEADRON_MIND_KEY": key}, clear=True):
                    code = mind_verifier.main(["activate", *fixed, "--risk-modifiers", "webhook", *extra])
                return code, out.read_text()

            code, text = activate("")
            if code or not text.startswith("mind-status=inactive\n") or requests:
                raise SystemExit("FAIL an Action without a Mind key did not stay inactive and silent")
            code, text = activate(KEY, "--files", "\n".join(("a.py", "b.py")))
            if code or "change-classes=api_change,dependency_change\nrequired-gates=formatter,unit_tests\n" not in text:
                raise SystemExit(f"FAIL an active Mind key did not report the hosted plan: {code} {text!r}")
            plans = [json.loads(body) for path, _, body in requests if path == "/plan"]
            wanted = [
                {"change_class": name, "risk_modifiers": ["webhook"]} for name in json.loads(CLASSIFIED)["classes"]
            ]
            if requests[0] != ("/verify", f"Bearer {KEY}", b"") or plans != wanted:
                raise SystemExit("FAIL activation did not verify the key and then plan each class once")
            if "HEADRON_MIND_KEY" in child.call_args.kwargs["env"] or child.call_args.args[0][-2:] != ["a.py", "b.py"]:
                raise SystemExit("FAIL activation handed the Mind key to the classifier")
            for what, extra, changed in REFUSALS:
                code, text = activate(KEY, *extra, **changed)
                if code != 1 or "mind-status=active" in text or ("/verify" in changed and len(requests) != 1):
                    raise SystemExit(f"FAIL activation did not refuse {what}")
    finally:
        listener.shutdown()
        listener.server_close()
        thread.join(timeout=5)
    module.CASES.append(
        (
            "the Action's Mind step asks nothing without a key, plans each class once with an active one, and keeps the key from child processes",
            "an invalid key, a disagreeing reply, a refused plan, an injected output line or an unknown change set read as an active plan",
        )
    )
    print("  ok    the Action's Mind step is gated by the key and refuses what it cannot confirm")


def run(module: ModuleType) -> None:
    activation_case(module)
