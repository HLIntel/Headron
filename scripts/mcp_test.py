#!/usr/bin/env python3
"""The MCP route's process cases, split out of cli_test.py to keep it under the code-blob cap.

A case module: run() takes the RUNNING atlas_test module and registers into its counted CASES.

  mcp_fork_cases      a forked call reads an edited atlas and refuses a stale module; a slow call is killed
  bounded_output_case a call printing past MAX_OUTPUT is cut, drained and labelled, never held whole
  batch_cases        a batch validates whole before it runs; parallel replies keep request order
  featured_cases     each typed tool builds one exact argv (--json forced, paths resolved, refusals), and a planted drop is caught
  portability_cases  HEADRON_CLIENT_DIR resolves relative paths for both routes; a bad one exits 2; no os.fork still answers
"""

from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, cast
from unittest import mock

ROOT = CASES = mutated = atlas = cast(Any, None)  # bound by run() from the running atlas_test module


def run(module) -> None:
    global ROOT, CASES, mutated, atlas
    ROOT, CASES, mutated, atlas = module.ROOT, module.CASES, module.mutated, module.atlas
    mcp_fork_cases()
    bounded_output_case()
    scope_cases()
    batch_cases()
    prompt_cases()
    featured_cases()
    portability_cases()


_FORK_PROBE = """
import os, sys
sys.path.insert(0, sys.argv[1])
import atlascore, headron_mcp
def version():
    return ((headron_mcp.call("headron", {"argv": ["commands", "--json"]}).get("structuredContent") or {}).get("record") or {}).get("version")
print("warm", version(), headron_mcp._forkable(), flush=True)
atlascore.atlas()
input()
print("atlas-edited", version(), flush=True)
input()
print("module-edited", headron_mcp._forkable(), flush=True)
input()  # the harness has restored every planted file: a 1s child must not race that write
headron_mcp.TIMEOUT = 1
print("timeout", "timed out" in headron_mcp.call("headron", {"argv": ["check"]})["content"][0]["text"], flush=True)
print("parent", os.getcwd(), "HEADRON_READ_ONLY" in os.environ, flush=True)
"""


def _fork_answers() -> dict[str, list[str]]:
    """Run the probe through its edits; each printed line keyed by its first word."""
    probe = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", _FORK_PROBE, str(ROOT / "scripts")],
        cwd="/tmp",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "HEADRON_MCP_ISOLATE"},
    )
    assert probe.stdin and probe.stdout
    lines = [probe.stdout.readline()]
    with mutated("atlas.yaml", lambda t: t.replace("version: ", "version: 9", 1)):
        probe.stdin.write("\n")
        probe.stdin.flush()
        lines.append(probe.stdout.readline())
    with mutated("scripts/commands.py", lambda t: t + "\n# planted: a module edited under a warm parent\n"):
        probe.stdin.write("\n")
        probe.stdin.flush()
        lines.append(probe.stdout.readline())
    # RELEASED ONLY AFTER THE RESTORE: the timeout step ran while `mutated` was still rewriting
    # commands.py, and a child that imported it half-written crashed inside its 1s, reading False.
    out, _ = probe.communicate(input="\n", timeout=600)
    return {line.split()[0]: line.split()[1:] for line in [*lines, *out.splitlines()] if line.split()}


def mcp_fork_cases() -> None:
    """A warm parent answers from the tree on disk, never from what it imported; a slow child is killed."""
    version = str(atlas.atlas().get("version"))
    want = {
        "warm": [version, "True"],
        "atlas-edited": ["9" + version],
        "module-edited": ["False"],
        "timeout": ["True"],
        "parent": [str(Path("/tmp").resolve()), "False"],
    }
    got = _fork_answers()
    if got != want:
        raise SystemExit(f"FAIL headron-mcp fork: wanted {want}, got {got}")
    for needle, mutant, key in (
        ("value.cache_clear()", "pass", "atlas-edited"),
        ('return _WARM["stamp"] == _source_stamp()', "return True", "module-edited"),
    ):
        with mutated("scripts/headron_mcp.py", lambda t, n=needle, m=mutant: t.replace(n, m, 1)):
            planted = _fork_answers()
        if planted.get(key) == want[key]:
            raise SystemExit(f"FAIL the fork probe did not notice '{mutant}' planted for '{needle}'")
    CASES.append(
        (
            "a forked MCP call reads an edited atlas, refuses a stale module, is killed at its timeout",
            "a warm server answering from the atlas or the code it held before the edit",
        )
    )
    print("  ok    headron-mcp fork: edited atlas read fresh, stale module refused, timeout kills; two mutants caught")


def bounded_output_case() -> None:
    """THE REPLY IS BOUNDED (3.54.x): a command printing without end grew the server and the client's reply."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import headron_mcp

    cut = headron_mcp._bounded("x" * (headron_mcp.MAX_OUTPUT + 10))
    whole = headron_mcp._bounded("short")
    if whole != "short" or not cut.startswith("x" * headron_mcp.MAX_OUTPUT) or "output cut" not in cut:
        raise SystemExit("FAIL headron-mcp: an over-long output was not cut and labelled, or a short one was altered")
    saved = headron_mcp.MAX_OUTPUT
    headron_mcp.MAX_OUTPUT = 64
    try:
        shown = headron_mcp.call("headron", {"argv": ["commands"]})["content"][0]["text"]
    finally:
        headron_mcp.MAX_OUTPUT = saved
    if "output cut at 64" not in shown or len(shown) > 64 + 200:
        raise SystemExit(f"FAIL headron-mcp: a call past the cap returned {len(shown)} characters uncut")
    CASES.append(
        (
            "an MCP call's output past MAX_OUTPUT is cut and labelled",
            "a command printing without end held whole in memory",
        )
    )
    print("  ok    headron-mcp: output past the cap is cut, drained and labelled")


def scope_cases() -> None:
    """HEADRON_MCP_VERBS narrows the offered verbs for one agent: it never widens them, and an unknown name fails loud."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import headron_mcp

    full = headron_mcp.offered()
    keep, drop = full[0], full[1]
    saved = os.environ.get("HEADRON_MCP_VERBS")
    try:
        os.environ["HEADRON_MCP_VERBS"] = keep
        if headron_mcp.offered() != [keep]:
            raise SystemExit(f"FAIL headron-mcp scope: HEADRON_MCP_VERBS={keep} offered {headron_mcp.offered()}")
        if not headron_mcp.call("headron", {"argv": [drop]}).get("isError"):
            raise SystemExit(f"FAIL headron-mcp scope: verb '{drop}' outside the grant still ran")
        os.environ["HEADRON_MCP_VERBS"] = f"{keep},no-such-verb"
        try:
            headron_mcp.offered()
        except ValueError:
            pass
        else:
            raise SystemExit("FAIL headron-mcp scope: an unknown verb in the grant was silently dropped")
    finally:
        if saved is None:
            os.environ.pop("HEADRON_MCP_VERBS", None)
        else:
            os.environ["HEADRON_MCP_VERBS"] = saved
    CASES.append(
        (
            "HEADRON_MCP_VERBS narrows the offered verbs and refuses an unknown name",
            "an agent granted more verbs than it named, or a typo silently hiding a grant",
        )
    )
    print("  ok    headron-mcp scope: one agent's grant narrows the route; an unknown name fails loud")


def batch_cases() -> None:
    """A batch validates wholly before it starts and parallel replies retain request order."""
    import importlib

    sys.path.insert(0, str(ROOT / "scripts"))
    headron_mcp = importlib.reload(importlib.import_module("headron_mcp"))

    called: list[list[str]] = []

    def fake_forked(argv: list[str]) -> subprocess.CompletedProcess:
        called.append(argv)
        return subprocess.CompletedProcess(argv, 0, argv[0], "")

    def fake_spawn(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        called.append(argv[2:])
        return subprocess.CompletedProcess(argv, 0, argv[-1], "")

    with (
        mock.patch.object(headron_mcp, "_forkable", return_value=True),
        mock.patch.object(headron_mcp, "_forked", side_effect=fake_forked) as forked,
        mock.patch.object(headron_mcp.subprocess, "run", side_effect=fake_spawn),
    ):
        reply = headron_mcp.call("headron", {"batch": [["commands"], ["check"]], "parallel": True})
    results = reply.get("structuredContent", {}).get("results")
    if (
        sorted(called) != [["check"], ["commands"]]
        or forked.called
        or results != [{"exit": 0, "text": "commands"}, {"exit": 0, "text": "check"}]
    ):
        raise SystemExit(f"FAIL headron-mcp batch: order/results changed: called={called}, results={results}")
    called.clear()
    with (
        mock.patch.object(headron_mcp, "_forkable", return_value=True),
        mock.patch.object(headron_mcp, "_forked", side_effect=fake_forked),
    ):
        refused = headron_mcp.call("headron", {"batch": [["commands"], ["verify"]]})
    if not refused.get("isError") or called:
        raise SystemExit(f"FAIL headron-mcp batch: unsafe member ran part of batch: called={called}, reply={refused}")
    oversized = headron_mcp.call("headron", {"batch": [["commands"]] * 9})
    if not oversized.get("isError") or called:
        raise SystemExit(
            f"FAIL headron-mcp batch: schema-only limit accepted a ninth member: called={called}, reply={oversized}"
        )
    CASES.append(
        (
            "an MCP batch validates every read-only command before running and preserves reply order when parallel",
            "a batch partly executing before its unsafe member is refused, exceeding eight members, forking from a worker, or completion order changing result identity",
        )
    )
    print("  ok    headron-mcp batch: whole-batch validation, bounded parallelism, ordered replies")


def prompt_cases() -> None:
    """prompts/get refuses a missing required argument with -32602 rather than rendering a placeholder."""
    import headron_mcp

    def get(arguments: dict) -> dict | None:
        return headron_mcp.handle(
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "prompts/get",
                "params": {"name": "plan-change", "arguments": arguments},
            }
        )

    missing = get({})
    error = (missing or {}).get("error", {})
    if error.get("code") != -32602 or "'path'" not in error.get("message", ""):
        raise SystemExit(f"FAIL prompts/get without a path must answer -32602 naming it, got {missing}")
    filled = get({"path": "scripts/headron_mcp.py"})
    text = (filled or {}).get("result", {}).get("messages", [{}])[0].get("content", {}).get("text", "")
    if "headron steps scripts/headron_mcp.py" not in text or "<path>" in text:
        raise SystemExit(f"FAIL prompts/get with a path must name it, got {text[:120]!r}")
    CASES.append(
        (
            "an MCP prompt refuses a missing required argument and names the one it needs",
            "a prompt rendered with a placeholder path, or an absent argument answered as a crash",
        )
    )
    print(
        "  ok    headron-mcp prompts: a missing required argument is refused (-32602), never rendered as a placeholder"
    )


_FEATURED_CASES = (
    # (tool, arguments, the exact argv it must build: verb, positionals, options, then --json forced)
    ("port", {"target": "scripts/headron_mcp.py"}, ["port", "scripts/headron_mcp.py", "--json"]),
    ("route", {"path": "scripts/headron_mcp.py"}, ["route", "scripts/headron_mcp.py", "--json"]),
    (
        "gate",
        {"path": "scripts/headron_mcp.py", "gate": "formatter"},
        ["gate", "scripts/headron_mcp.py", "formatter", "--json"],
    ),
    (
        "steps",
        {"path": "scripts/headron_mcp.py", "runtime": "claude"},
        ["steps", "scripts/headron_mcp.py", "--runtime", "claude", "--json"],
    ),
    (
        "failures",
        {"for": "scripts/headron_mcp.py", "limit": 2},
        ["failures", "--for", "scripts/headron_mcp.py", "--limit", "2", "--json"],
    ),
    ("successes", {"id": "gate_on_the_unpiped_exit_code"}, ["successes", "gate_on_the_unpiped_exit_code", "--json"]),
    ("proof", {"path": "scripts/headron_mcp.py"}, ["proof", "scripts/headron_mcp.py", "--json"]),
)
_FEATURED_REFUSALS = (
    ("port", {"target": "--run"}, "refused"),
    ("route", {"path": "no/such/file_zz.py"}, "no such path"),
    ("failures", {}, "needs one of"),
    ("successes", {"id": "x", "fix": True}, "takes no argument"),
    ("proof", {"path": ["a.py", "b.py"]}, "one value"),
    ("port", {"lens": "wide", "target": "x"}, "takes no argument"),
)


def _featured_problems(headron_mcp) -> list[str]:
    """Every way the typed tools disagree with their table: the argv each builds, the refusals each holds.
    The table names one file relative to the repository; it is passed absolute, so the check reads the same from any cwd."""
    here = str(ROOT / "scripts" / "headron_mcp.py")
    problems = []
    for name, arguments, want in _FEATURED_CASES:
        arguments = {k: here if v == "scripts/headron_mcp.py" else v for k, v in arguments.items()}
        want = [here if w == "scripts/headron_mcp.py" else w for w in want]
        try:
            argv, _ = headron_mcp._featured(name, arguments)
        except ValueError as refused:
            problems.append(f"{name} refused {arguments}: {refused}")
            continue
        if argv != want:
            problems.append(f"{name} built {argv}, wanted {want}")
    for name, arguments, needle in _FEATURED_REFUSALS:
        try:
            headron_mcp._featured(name, arguments)
        except ValueError as refused:
            if needle not in str(refused):
                problems.append(f"{name} refused {arguments} without '{needle}': {refused}")
        else:
            problems.append(f"{name} accepted {arguments}; it must be refused")
    return problems


def featured_cases() -> None:
    """Each typed tool builds one exact argv, forced to --json; its paths are checked and echoed; a planted drop is caught."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib

    import headron_mcp

    problems = _featured_problems(headron_mcp)
    if problems:
        raise SystemExit("FAIL headron-mcp typed tools: " + "; ".join(problems))

    # THE CALL, END TO END, WITH THE FORK MOCKED: the argv that reaches the process, and the path it resolved.
    seen: list[list[str]] = []

    def fake_forked(argv: list[str]) -> subprocess.CompletedProcess:
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, '{"schema": 1, "command": "route"}', "")

    with (
        mock.patch.object(headron_mcp, "_forkable", return_value=True),
        mock.patch.object(headron_mcp, "_forked", side_effect=fake_forked),
    ):
        reply = headron_mcp.call("route", {"path": str(ROOT / "scripts" / "headron_mcp.py")})
    content = reply["structuredContent"]
    if (
        seen != [["route", str(ROOT / "scripts" / "headron_mcp.py"), "--json"]]
        or content["record"] != {"schema": 1, "command": "route"}
        or content["resolved"] != {"path": str(ROOT / "scripts" / "headron_mcp.py")}
        or reply["isError"]
    ):
        raise SystemExit(f"FAIL headron-mcp typed call: argv={seen} structuredContent={content}")

    # A PLANTED DROP IS CAUGHT: a typed tool that stops forcing --json returns text a client re-parses.
    with mutated("scripts/headron_mcp.py", lambda t: t.replace('argv = argv + ["--json"]', "argv = argv", 1)):
        planted = importlib.reload(headron_mcp)
        caught = _featured_problems(planted)
    importlib.reload(headron_mcp)  # the restored file, not the planted one, stays in the cache
    if not any("--json" in problem for problem in caught):
        raise SystemExit("FAIL the featured-tool case did not notice --json dropped from the typed tools")

    CASES.append(
        (
            "each typed MCP tool builds its exact argv with --json forced; refusals hold; a planted drop is caught",
            "a typed tool returning text a client re-parses, a whole ledger dumped on request, or a path read in the wrong directory",
        )
    )
    print("  ok    headron-mcp typed tools: exact argv per tool, --json forced, refusals hold, a planted drop caught")


def portability_cases() -> None:
    """Any runtime, any working directory: HEADRON_CLIENT_DIR sets where relative paths resolve, for the typed tools and
    the `headron` tool's child alike; a directory that does not exist refuses to start; a host without os.fork still answers."""
    import json
    import tempfile

    sys.path.insert(0, str(ROOT / "scripts"))
    import headron_mcp

    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp).resolve()
        (project / "probe_target.py").write_text("print('probe')\n", encoding="utf-8")
        request = "\n".join(
            json.dumps(message)
            for message in (
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "route", "arguments": {"path": "probe_target.py"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "headron", "arguments": {"argv": ["route", "probe_target.py", "--json"]}},
                },
            )
        )
        # Started from `/`, the way a runtime that ignores the project directory starts it.
        env = {**os.environ, "HEADRON_CLIENT_DIR": str(project)}
        served = subprocess.run(  # noqa: S603
            [sys.executable, str(ROOT / "scripts" / "headron_mcp.py")],
            input=request + "\n",
            capture_output=True,
            text=True,
            cwd="/",
            env=env,
            timeout=600,
        )
        replies = {reply["id"]: reply["result"] for reply in map(json.loads, served.stdout.splitlines())}
        typed, generic = replies.get(1, {}), replies.get(2, {})
        if (
            typed.get("structuredContent", {}).get("resolved", {}).get("path") != str(project / "probe_target.py")
            or generic.get("structuredContent", {}).get("exit") != 0
            or generic.get("isError")
        ):
            raise SystemExit(f"FAIL HEADRON_CLIENT_DIR: typed={typed} generic={generic} stderr={served.stderr[-300:]}")

        # A directory that does not exist refuses to start, with the reason on stderr and exit 2.
        missing = subprocess.run(  # noqa: S603
            [sys.executable, str(ROOT / "scripts" / "headron_mcp.py")],
            input="",
            capture_output=True,
            text=True,
            cwd="/",
            env={**os.environ, "HEADRON_CLIENT_DIR": str(project / "absent")},
            timeout=600,
        )
        if missing.returncode != 2 or "HEADRON_CLIENT_DIR" not in missing.stderr:
            raise SystemExit(
                f"FAIL a missing HEADRON_CLIENT_DIR must exit 2 with a reason: {missing.returncode} {missing.stderr!r}"
            )

    # A HOST WITHOUT os.fork (Windows): the call spawns its child, and still answers the same record.
    saved = os.fork
    del os.fork
    try:
        if headron_mcp._forkable():
            raise SystemExit("FAIL _forkable() claimed fork on a host without os.fork")
        reply = headron_mcp.call("route", {"path": str(ROOT / "scripts" / "headron_mcp.py")})
    finally:
        os.fork = saved
    content = reply["structuredContent"]
    if content["exit"] != 0 or content["record"]["command"] != "route" or reply["isError"]:
        raise SystemExit(f"FAIL the no-fork host did not answer through the spawned route: {content}")

    CASES.append(
        (
            "HEADRON_CLIENT_DIR resolves relative paths for both MCP routes from any start directory; a missing one refuses; a host without os.fork answers",
            "a runtime that starts the server in `/` getting every relative path resolved against the wrong tree, or a Windows host that cannot answer at all",
        )
    )
    # A MEASURED CLIENT: Claude Code 2.1.304 asked for 2025-11-25 and was answered 2026-07-28 until the row was added.
    for asked in ("2025-11-25", "2024-11-05"):
        answered = headron_mcp.handle(
            {"jsonrpc": "2.0", "id": 9, "method": "initialize", "params": {"protocolVersion": asked}}
        )
        got = ((answered or {}).get("result") or {}).get("protocolVersion")
        if got != asked:
            raise SystemExit(f"FAIL initialize asked {asked} was answered {got}")
    print("  ok    headron-mcp portability: HEADRON_CLIENT_DIR from `/`, missing dir refused, no-fork host answers")


def _stdio_session(env: dict[str, str] | None = None) -> subprocess.Popen:
    root = Path(__file__).resolve().parent.parent
    cmd = [sys.executable, str(root / "scripts" / "headron_mcp.py")]
    base_env = {**os.environ, "HEADRON_ROOT": str(root)}
    if env:
        base_env.update(env)
    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=base_env,
        cwd=str(root),
    )


def _rpc_exchange(proc: subprocess.Popen, method: str, params: dict, req_id: int) -> dict:
    msg = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(msg + "\n")
    proc.stdin.flush()
    line = proc.stdout.readline()
    if not line:
        err = proc.stderr.read() if proc.stderr else ""
        raise RuntimeError(f"Server closed stdio unexpectedly: {err}")
    return json.loads(line)


EXPECTED_TOOL_NAMES = [
    "headron",
    "port",
    "route",
    "gate",
    "steps",
    "failures",
    "successes",
    "proof",
    "mind_classify",
    "mind_plan",
    "mind_route",
    "mind_health",
    "mind_receipts",
]

TOOL_TEST_CALLS = {
    "headron": {"argv": ["route", "scripts/headron_mcp.py", "--json"]},
    "port": {"target": "scripts/headron_mcp.py"},
    "route": {"path": "scripts/headron_mcp.py"},
    "gate": {"path": "scripts/headron_mcp.py", "gate": "formatter"},
    "steps": {"path": "scripts/headron_mcp.py"},
    "failures": {"for": "scripts/headron_mcp.py", "limit": 2},
    "successes": {"id": "gate_on_the_unpiped_exit_code"},
    "proof": {"path": "scripts/headron_mcp.py"},
    "mind_classify": {"files": ["scripts/headron_mcp.py"]},
    "mind_plan": {"files": ["scripts/headron_mcp.py"]},
    "mind_route": {"files": ["scripts/headron_mcp.py"]},
    "mind_health": {},
    "mind_receipts": {"limit": 5},
}


def _close(proc: subprocess.Popen) -> None:
    if proc.stdin:
        proc.stdin.close()
    proc.wait(timeout=5)


def _check_initialize(proc: subprocess.Popen, expected_version: str) -> None:
    init_reply = _rpc_exchange(
        proc, "initialize", {"clientInfo": {"name": "mcp-test", "version": "1.0"}, "protocolVersion": "2026-07-28"}, 1
    )
    init_res = init_reply.get("result", {})
    info = init_res.get("serverInfo", {})
    if info.get("name") != "Headron MCP" or info.get("version") != expected_version:
        raise SystemExit(f"FAIL initialize serverInfo mismatch: {info}")
    if not init_res.get("protocolVersion"):
        raise SystemExit(f"FAIL initialize missing protocolVersion: {init_res}")
    if not init_res.get("capabilities", {}).get("tools"):
        raise SystemExit(f"FAIL initialize missing tools capability: {init_res}")
    print(
        f"PASS  initialize -> protocolVersion {init_res['protocolVersion']}, serverInfo Headron MCP {expected_version}"
    )


def _check_tools_list(proc: subprocess.Popen) -> None:
    list_reply = _rpc_exchange(proc, "tools/list", {}, 2)
    tools = list_reply.get("result", {}).get("tools", [])
    tool_names = [t["name"] for t in tools]
    if tool_names != EXPECTED_TOOL_NAMES:
        raise SystemExit(f"FAIL tools/list tool names mismatch: {tool_names} != {EXPECTED_TOOL_NAMES}")
    for t in tools:
        if not t.get("description"):
            raise SystemExit(f"FAIL tool '{t['name']}' has an empty description")
        schema = t.get("inputSchema", {})
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            raise SystemExit(f"FAIL tool '{t['name']}' inputSchema is not strict object: {schema}")
    print(f"PASS  tools/list -> {len(tools)} tools registered with strict schemas")


def _check_tool_calls(proc: subprocess.Popen) -> None:
    for req_id, (tool_name, args) in enumerate(TOOL_TEST_CALLS.items(), start=10):
        call_reply = _rpc_exchange(proc, "tools/call", {"name": tool_name, "arguments": args}, req_id)
        res = call_reply.get("result", {})
        sc = res.get("structuredContent", {})
        expected_exit = 2 if tool_name == "proof" else 0
        if sc.get("exit") != expected_exit:
            raise SystemExit(f"FAIL tools/call '{tool_name}' exit != {expected_exit}: {res}")
        if "record" not in sc and "text" not in sc:
            raise SystemExit(f"FAIL tools/call '{tool_name}' missing structured output: {sc}")
        print(f"PASS  tools/call {tool_name}")


class MockMindHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"command": "mind", "mock": true, "status": "healthy"}')

    def log_message(self, format: str, *args: Any) -> None:
        pass


def _check_hosted_dispatch() -> None:
    mock_server = http.server.HTTPServer(("127.0.0.1", 0), MockMindHandler)
    threading.Thread(target=mock_server.serve_forever, daemon=True).start()
    try:
        proc = _stdio_session(
            {"HEADRON_MIND_URL": f"http://127.0.0.1:{mock_server.server_port}", "HEADRON_MIND_KEY": "test-key"}
        )
        try:
            h_reply = _rpc_exchange(proc, "tools/call", {"name": "mind_health", "arguments": {}}, 90)
            h_res = h_reply.get("result", {})
            if h_res.get("isError") or not h_res.get("structuredContent", {}).get("record", {}).get("mock"):
                raise SystemExit(f"FAIL hosted Mind API dispatch failed: {h_res}")
            print("PASS  mind hosted API dispatch over HTTP")
        finally:
            _close(proc)
    finally:
        mock_server.shutdown()


def _check_unreachable_hosted() -> None:
    proc = _stdio_session({"HEADRON_MIND_URL": "http://127.0.0.1:9"})
    try:
        bad_reply = _rpc_exchange(proc, "tools/call", {"name": "mind_health", "arguments": {}}, 91)
        bad_res = bad_reply.get("result", {})
        if not bad_res.get("isError"):
            raise SystemExit(f"FAIL unreachable hosted Mind API did not return error: {bad_res}")
        print("PASS  mind clear error returned when hosted URL is unreachable")
    finally:
        _close(proc)


def _check_rejects_non_http_url() -> None:
    proc = _stdio_session({"HEADRON_MIND_URL": "file:///etc/passwd"})
    try:
        reply = _rpc_exchange(proc, "tools/call", {"name": "mind_health", "arguments": {}}, 92)
        res = reply.get("result", {})
        if not res.get("isError") or "http or https" not in res.get("content", [{}])[0].get("text", ""):
            raise SystemExit(f"FAIL non-http HEADRON_MIND_URL was not refused: {res}")
        print("PASS  mind refuses non-http HEADRON_MIND_URL scheme")
    finally:
        _close(proc)


def stdio_suite() -> int:
    """End-to-end stdio protocol test: initialize, tools/list, one call per tool, then hosted Mind API."""
    root = Path(__file__).resolve().parent.parent
    expected_version = (root / "VERSION").read_text(encoding="utf-8").strip()

    proc = _stdio_session()
    try:
        _check_initialize(proc, expected_version)
        _check_tools_list(proc)
        _check_tool_calls(proc)
    finally:
        _close(proc)

    _check_hosted_dispatch()
    _check_unreachable_hosted()
    _check_rejects_non_http_url()

    print("scripts/mcp_test.py: initialize, tools/list, and one call per tool over stdio, all pass")
    return 0


def main() -> int:
    return stdio_suite()


if __name__ == "__main__":
    sys.exit(main())
