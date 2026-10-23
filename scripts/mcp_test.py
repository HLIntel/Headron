#!/usr/bin/env python3
"""The MCP route's process cases, split out of cli_test.py to keep it under the code-blob cap.

A case module: run() takes the RUNNING atlas_test module and registers into its counted CASES.

  mcp_fork_cases      a forked call reads an edited atlas and refuses a stale module; a slow call is killed
  bounded_output_case a call printing past MAX_OUTPUT is cut, drained and labelled, never held whole
  batch_cases        a batch validates whole before it runs; parallel replies keep request order
  featured_cases     each typed tool builds one exact argv (--json forced, paths resolved, refusals), and a planted drop is caught
  portability_cases  THEA_CLIENT_DIR resolves relative paths for both routes; a bad one exits 2; no os.fork still answers
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast
from unittest import mock

ROOT = CASES = mutated = atlas = cast(Any, None)  # bound by run() from the running atlas_test module


def run(module) -> None:
    global ROOT, CASES, mutated, atlas
    ROOT, CASES, mutated, atlas = module.ROOT, module.CASES, module.mutated, module.atlas
    mcp_fork_cases()
    bounded_output_case()
    batch_cases()
    prompt_cases()
    featured_cases()
    portability_cases()


_FORK_PROBE = """
import os, sys
sys.path.insert(0, sys.argv[1])
import atlascore, thea_mcp
def version():
    return ((thea_mcp.call("thea", {"argv": ["commands", "--json"]}).get("structuredContent") or {}).get("record") or {}).get("version")
print("warm", version(), thea_mcp._forkable(), flush=True)
atlascore.atlas()
input()
print("atlas-edited", version(), flush=True)
input()
print("module-edited", thea_mcp._forkable(), flush=True)
input()  # the harness has restored every planted file: a 1s child must not race that write
thea_mcp.TIMEOUT = 1
print("timeout", "timed out" in thea_mcp.call("thea", {"argv": ["check"]})["content"][0]["text"], flush=True)
print("parent", os.getcwd(), "THEA_READ_ONLY" in os.environ, flush=True)
"""


def _fork_answers() -> dict[str, list[str]]:
    """Run the probe through its edits; each printed line keyed by its first word."""
    probe = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", _FORK_PROBE, str(ROOT / "scripts")],
        cwd="/tmp",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "THEA_MCP_ISOLATE"},
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
        raise SystemExit(f"FAIL thea-mcp fork: wanted {want}, got {got}")
    for needle, mutant, key in (
        ("value.cache_clear()", "pass", "atlas-edited"),
        ('return _WARM["stamp"] == _source_stamp()', "return True", "module-edited"),
    ):
        with mutated("scripts/thea_mcp.py", lambda t, n=needle, m=mutant: t.replace(n, m, 1)):
            planted = _fork_answers()
        if planted.get(key) == want[key]:
            raise SystemExit(f"FAIL the fork probe did not notice '{mutant}' planted for '{needle}'")
    CASES.append(
        (
            "a forked MCP call reads an edited atlas, refuses a stale module, is killed at its timeout",
            "a warm server answering from the atlas or the code it held before the edit",
        )
    )
    print("  ok    thea-mcp fork: edited atlas read fresh, stale module refused, timeout kills; two mutants caught")


def bounded_output_case() -> None:
    """THE REPLY IS BOUNDED (3.54.x): a command printing without end grew the server and the client's reply."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import thea_mcp

    cut = thea_mcp._bounded("x" * (thea_mcp.MAX_OUTPUT + 10))
    whole = thea_mcp._bounded("short")
    if whole != "short" or not cut.startswith("x" * thea_mcp.MAX_OUTPUT) or "output cut" not in cut:
        raise SystemExit("FAIL thea-mcp: an over-long output was not cut and labelled, or a short one was altered")
    saved = thea_mcp.MAX_OUTPUT
    thea_mcp.MAX_OUTPUT = 64
    try:
        shown = thea_mcp.call("thea", {"argv": ["commands"]})["content"][0]["text"]
    finally:
        thea_mcp.MAX_OUTPUT = saved
    if "output cut at 64" not in shown or len(shown) > 64 + 200:
        raise SystemExit(f"FAIL thea-mcp: a call past the cap returned {len(shown)} characters uncut")
    CASES.append(
        (
            "an MCP call's output past MAX_OUTPUT is cut and labelled",
            "a command printing without end held whole in memory",
        )
    )
    print("  ok    thea-mcp: output past the cap is cut, drained and labelled")


def batch_cases() -> None:
    """A batch validates wholly before it starts and parallel replies retain request order."""
    import importlib

    sys.path.insert(0, str(ROOT / "scripts"))
    thea_mcp = importlib.reload(importlib.import_module("thea_mcp"))

    called: list[list[str]] = []

    def fake_forked(argv: list[str]) -> subprocess.CompletedProcess:
        called.append(argv)
        return subprocess.CompletedProcess(argv, 0, argv[0], "")

    def fake_spawn(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        called.append(argv[2:])
        return subprocess.CompletedProcess(argv, 0, argv[-1], "")

    with (
        mock.patch.object(thea_mcp, "_forkable", return_value=True),
        mock.patch.object(thea_mcp, "_forked", side_effect=fake_forked) as forked,
        mock.patch.object(thea_mcp.subprocess, "run", side_effect=fake_spawn),
    ):
        reply = thea_mcp.call("thea", {"batch": [["commands"], ["check"]], "parallel": True})
    results = reply.get("structuredContent", {}).get("results")
    if (
        sorted(called) != [["check"], ["commands"]]
        or forked.called
        or results != [{"exit": 0, "text": "commands"}, {"exit": 0, "text": "check"}]
    ):
        raise SystemExit(f"FAIL thea-mcp batch: order/results changed: called={called}, results={results}")
    called.clear()
    with (
        mock.patch.object(thea_mcp, "_forkable", return_value=True),
        mock.patch.object(thea_mcp, "_forked", side_effect=fake_forked),
    ):
        refused = thea_mcp.call("thea", {"batch": [["commands"], ["verify"]]})
    if not refused.get("isError") or called:
        raise SystemExit(f"FAIL thea-mcp batch: unsafe member ran part of batch: called={called}, reply={refused}")
    oversized = thea_mcp.call("thea", {"batch": [["commands"]] * 9})
    if not oversized.get("isError") or called:
        raise SystemExit(
            f"FAIL thea-mcp batch: schema-only limit accepted a ninth member: called={called}, reply={oversized}"
        )
    CASES.append(
        (
            "an MCP batch validates every read-only command before running and preserves reply order when parallel",
            "a batch partly executing before its unsafe member is refused, exceeding eight members, forking from a worker, or completion order changing result identity",
        )
    )
    print("  ok    thea-mcp batch: whole-batch validation, bounded parallelism, ordered replies")


def prompt_cases() -> None:
    """prompts/get refuses a missing required argument with -32602 rather than rendering a placeholder."""
    import thea_mcp

    def get(arguments: dict) -> dict | None:
        return thea_mcp.handle(
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
    filled = get({"path": "scripts/thea_mcp.py"})
    text = (filled or {}).get("result", {}).get("messages", [{}])[0].get("content", {}).get("text", "")
    if "thea steps scripts/thea_mcp.py" not in text or "<path>" in text:
        raise SystemExit(f"FAIL prompts/get with a path must name it, got {text[:120]!r}")
    CASES.append(
        (
            "an MCP prompt refuses a missing required argument and names the one it needs",
            "a prompt rendered with a placeholder path, or an absent argument answered as a crash",
        )
    )
    print("  ok    thea-mcp prompts: a missing required argument is refused (-32602), never rendered as a placeholder")


_FEATURED_CASES = (
    # (tool, arguments, the exact argv it must build: verb, positionals, options, then --json forced)
    ("port", {"target": "scripts/thea_mcp.py"}, ["port", "scripts/thea_mcp.py", "--json"]),
    ("route", {"path": "scripts/thea_mcp.py"}, ["route", "scripts/thea_mcp.py", "--json"]),
    (
        "gate",
        {"path": "scripts/thea_mcp.py", "gate": "formatter"},
        ["gate", "scripts/thea_mcp.py", "formatter", "--json"],
    ),
    (
        "steps",
        {"path": "scripts/thea_mcp.py", "runtime": "claude"},
        ["steps", "scripts/thea_mcp.py", "--runtime", "claude", "--json"],
    ),
    (
        "failures",
        {"for": "scripts/thea_mcp.py", "limit": 2},
        ["failures", "--for", "scripts/thea_mcp.py", "--limit", "2", "--json"],
    ),
    ("successes", {"id": "gate_on_the_unpiped_exit_code"}, ["successes", "gate_on_the_unpiped_exit_code", "--json"]),
    ("proof", {"path": "scripts/thea_mcp.py"}, ["proof", "scripts/thea_mcp.py", "--json"]),
)
_FEATURED_REFUSALS = (
    ("port", {"target": "--run"}, "refused"),
    ("route", {"path": "no/such/file_zz.py"}, "no such path"),
    ("failures", {}, "needs one of"),
    ("successes", {"id": "x", "fix": True}, "takes no argument"),
    ("proof", {"path": ["a.py", "b.py"]}, "one value"),
    ("port", {"lens": "wide", "target": "x"}, "takes no argument"),
)


def _featured_problems(thea_mcp) -> list[str]:
    """Every way the typed tools disagree with their table: the argv each builds, the refusals each holds.
    The table names one file relative to the repository; it is passed absolute, so the check reads the same from any cwd."""
    here = str(ROOT / "scripts" / "thea_mcp.py")
    problems = []
    for name, arguments, want in _FEATURED_CASES:
        arguments = {k: here if v == "scripts/thea_mcp.py" else v for k, v in arguments.items()}
        want = [here if w == "scripts/thea_mcp.py" else w for w in want]
        try:
            argv, _ = thea_mcp._featured(name, arguments)
        except ValueError as refused:
            problems.append(f"{name} refused {arguments}: {refused}")
            continue
        if argv != want:
            problems.append(f"{name} built {argv}, wanted {want}")
    for name, arguments, needle in _FEATURED_REFUSALS:
        try:
            thea_mcp._featured(name, arguments)
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

    import thea_mcp

    problems = _featured_problems(thea_mcp)
    if problems:
        raise SystemExit("FAIL thea-mcp typed tools: " + "; ".join(problems))

    # THE CALL, END TO END, WITH THE FORK MOCKED: the argv that reaches the process, and the path it resolved.
    seen: list[list[str]] = []

    def fake_forked(argv: list[str]) -> subprocess.CompletedProcess:
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, '{"schema": 1, "command": "route"}', "")

    with (
        mock.patch.object(thea_mcp, "_forkable", return_value=True),
        mock.patch.object(thea_mcp, "_forked", side_effect=fake_forked),
    ):
        reply = thea_mcp.call("route", {"path": str(ROOT / "scripts" / "thea_mcp.py")})
    content = reply["structuredContent"]
    if (
        seen != [["route", str(ROOT / "scripts" / "thea_mcp.py"), "--json"]]
        or content["record"] != {"schema": 1, "command": "route"}
        or content["resolved"] != {"path": str(ROOT / "scripts" / "thea_mcp.py")}
        or reply["isError"]
    ):
        raise SystemExit(f"FAIL thea-mcp typed call: argv={seen} structuredContent={content}")

    # A PLANTED DROP IS CAUGHT: a typed tool that stops forcing --json returns text a client re-parses.
    with mutated("scripts/thea_mcp.py", lambda t: t.replace('argv = argv + ["--json"]', "argv = argv", 1)):
        planted = importlib.reload(thea_mcp)
        caught = _featured_problems(planted)
    importlib.reload(thea_mcp)  # the restored file, not the planted one, stays in the cache
    if not any("--json" in problem for problem in caught):
        raise SystemExit("FAIL the featured-tool case did not notice --json dropped from the typed tools")

    CASES.append(
        (
            "each typed MCP tool builds its exact argv with --json forced; refusals hold; a planted drop is caught",
            "a typed tool returning text a client re-parses, a whole ledger dumped on request, or a path read in the wrong directory",
        )
    )
    print("  ok    thea-mcp typed tools: exact argv per tool, --json forced, refusals hold, a planted drop caught")


def portability_cases() -> None:
    """Any runtime, any working directory: THEA_CLIENT_DIR sets where relative paths resolve, for the typed tools and
    the `thea` tool's child alike; a directory that does not exist refuses to start; a host without os.fork still answers."""
    import json
    import tempfile

    sys.path.insert(0, str(ROOT / "scripts"))
    import thea_mcp

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
                    "params": {"name": "thea", "arguments": {"argv": ["route", "probe_target.py", "--json"]}},
                },
            )
        )
        # Started from `/`, the way a runtime that ignores the project directory starts it.
        env = {**os.environ, "THEA_CLIENT_DIR": str(project)}
        served = subprocess.run(  # noqa: S603
            [sys.executable, str(ROOT / "scripts" / "thea_mcp.py")],
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
            raise SystemExit(f"FAIL THEA_CLIENT_DIR: typed={typed} generic={generic} stderr={served.stderr[-300:]}")

        # A directory that does not exist refuses to start, with the reason on stderr and exit 2.
        missing = subprocess.run(  # noqa: S603
            [sys.executable, str(ROOT / "scripts" / "thea_mcp.py")],
            input="",
            capture_output=True,
            text=True,
            cwd="/",
            env={**os.environ, "THEA_CLIENT_DIR": str(project / "absent")},
            timeout=600,
        )
        if missing.returncode != 2 or "THEA_CLIENT_DIR" not in missing.stderr:
            raise SystemExit(
                f"FAIL a missing THEA_CLIENT_DIR must exit 2 with a reason: {missing.returncode} {missing.stderr!r}"
            )

    # A HOST WITHOUT os.fork (Windows): the call spawns its child, and still answers the same record.
    saved = os.fork
    del os.fork
    try:
        if thea_mcp._forkable():
            raise SystemExit("FAIL _forkable() claimed fork on a host without os.fork")
        reply = thea_mcp.call("route", {"path": str(ROOT / "scripts" / "thea_mcp.py")})
    finally:
        os.fork = saved
    content = reply["structuredContent"]
    if content["exit"] != 0 or content["record"]["command"] != "route" or reply["isError"]:
        raise SystemExit(f"FAIL the no-fork host did not answer through the spawned route: {content}")

    CASES.append(
        (
            "THEA_CLIENT_DIR resolves relative paths for both MCP routes from any start directory; a missing one refuses; a host without os.fork answers",
            "a runtime that starts the server in `/` getting every relative path resolved against the wrong tree, or a Windows host that cannot answer at all",
        )
    )
    # A MEASURED CLIENT: Claude Code 2.1.304 asked for 2025-11-25 and was answered 2026-07-28 until the row was added.
    for asked in ("2025-11-25", "2024-11-05"):
        answered = thea_mcp.handle(
            {"jsonrpc": "2.0", "id": 9, "method": "initialize", "params": {"protocolVersion": asked}}
        )
        got = ((answered or {}).get("result") or {}).get("protocolVersion")
        if got != asked:
            raise SystemExit(f"FAIL initialize asked {asked} was answered {got}")
    print("  ok    thea-mcp portability: THEA_CLIENT_DIR from `/`, missing dir refused, no-fork host answers")
