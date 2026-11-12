#!/usr/bin/env python3
"""Planted cases: the Action's Mind step is silent without a key, plans every class in one request, refuses the rest;
its install and execution steps use the pinned checkout."""

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
CLASSES = ["api_change", "dependency_change"]
PLAN = {"change_classes": CLASSES, "required_gates": ["formatter", "unit_tests"], "policy_revision": "r1"}
ACTIVE = {"/verify": (200, b'{"status":"active"}'), "/plan": (200, json.dumps(PLAN).encode())}
CLASSIFIED = json.dumps({"category": "source_change", "classes": CLASSES})
# Each of these must end the step at exit 1 with no plan reported.
REFUSALS: tuple[tuple[str, tuple[str, ...], dict[str, tuple[int, bytes]]], ...] = (
    ("a key the service calls invalid", (), {"/verify": (401, b'{"status":"invalid key"}')}),
    ("a status and body that disagree", (), {"/verify": (200, b'{"status":"invalid key"}')}),
    ("a plan the service refused", ("--files", "a.py"), {"/plan": (400, b'{"error":"x"}')}),
    ("an unreadable successful plan", ("--files", "a.py"), {"/plan": (200, b"not json")}),
    (
        "a gate name carrying a second output line",
        ("--files", "a.py"),
        {"/plan": (200, json.dumps(PLAN | {"required_gates": ["a\nb=c"]}).encode())},
    ),
    (
        "a plan answered for classes nobody asked about",
        ("--files", "a.py"),
        {"/plan": (200, json.dumps(PLAN | {"change_classes": ["api_change"]}).encode())},
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
            wanted = [{"change_classes": CLASSES, "risk_modifiers": ["webhook"]}]
            if requests[0] != ("/verify", f"Bearer {KEY}", b"") or plans != wanted:
                raise SystemExit(
                    f"FAIL activation did not verify the key and then plan every class in one request: {plans}"
                )
            many = [f"class_{n}" for n in range(mind_verifier.PLAN_BATCH + 1)]
            answer = {"required_gates": ["formatter"], "policy_revision": "r1"}
            with mock.patch.object(mind_verifier, "hosted_plan", return_value=answer) as asked:
                mind_verifier.hosted_gates("http://unused", KEY, many, [])
            if [call.args[2] for call in asked.call_args_list] != [many[:-1], many[-1:]]:
                raise SystemExit("FAIL a class list longer than the service takes was not split into full requests")
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
            "the Action's Mind step asks nothing without a key, plans every class in one request with an active one, and keeps the key from child processes",
            "an invalid key, a disagreeing reply, a refused plan, an answer for other classes, an injected output line or an unknown change set read as an active plan",
        )
    )
    print("  ok    the Action's Mind step is gated by the key and refuses what it cannot confirm")


def _install_problems(root: Path) -> list[str]:
    """Refuse an Action that installs or resolves a different checkout."""
    lines = [line.strip() for line in (root / "action.yml").read_text(encoding="utf-8").splitlines()]
    installs = [line for line in lines if "pip install" in line]
    problems = [] if installs else ["action.yml holds no pip install line: the install check saw nothing"]
    for line in installs:
        if '"$GITHUB_ACTION_PATH"' not in line:
            problems.append(f"action.yml installs a different launcher: {line}")
    if 'export HEADRON_ROOT="$GITHUB_ACTION_PATH"' not in lines:
        problems.append("action.yml does not execute the pinned checkout's atlas")
    return problems


def install_case(module: ModuleType) -> None:
    """SIGHTED (review): `uses: ...@<sha>` pinned the Action's files while its step installed the newest release."""
    problems = _install_problems(module.ROOT)
    if problems:
        raise SystemExit("FAIL the Action's install step: " + "; ".join(problems))
    plants = (
        ('pip install --quiet "$GITHUB_ACTION_PATH"', "pip install --quiet headron-software", "different launcher"),
        ('export HEADRON_ROOT="$GITHUB_ACTION_PATH"', "export HEADRON_ROOT=.", "pinned checkout's atlas"),
        ("python3 -m pip install", "python3 -m pipx run", "saw nothing"),
    )
    for old, new, needle in plants:
        with module.mutated("action.yml", lambda s, old=old, new=new: s.replace(old, new)):
            planted = _install_problems(module.ROOT)
        if not any(needle in problem for problem in planted):
            raise SystemExit(f"FAIL the install check did not notice {old!r} -> {new!r}: {planted}")
    module.CASES.append(
        (
            "the Action installs and executes its own checkout",
            "a workflow pinned to a commit running another launcher or atlas",
        )
    )
    print(f"  ok    the Action's install step is pinned to its checkout; {len(plants)} planted drifts caught")


def run(module: ModuleType) -> None:
    activation_case(module)
    install_case(module)
