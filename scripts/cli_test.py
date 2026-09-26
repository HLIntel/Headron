#!/usr/bin/env python3
"""The install, the CLI and the MCP route, split out of atlas_test.py to keep it under the shape cap.

Named *_test.py because it IS a test harness. Like atlas_guards_test, run() takes the RUNNING
atlas_test module and registers into its counted CASES: a fresh `import atlas_test` would be a
second copy whose cases nobody counts.

  install_cases       only what the wheel ships, run from outside the atlas: check, doctor, roster, an instrument
  cli_and_mcp_cases   every command has a help line; the roster satisfies thea-commands/1; thea-mcp speaks
                      MCP, lists the CLI's own commands and refuses writes — each property planted and refused
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = CASES = case = mutated = atlas = None  # bound by run() from the running atlas_test module


def run(module) -> None:
    global ROOT, CASES, case, mutated, atlas
    ROOT, CASES, case, mutated, atlas = module.ROOT, module.CASES, module.case, module.mutated, module.atlas
    install_cases()
    cli_and_mcp_cases()


def install_cases() -> None:
    """The wheel actually WORKS, proved by copying only what ships and running every kind of command.

    A checkout has every module, so an install-only break is invisible here. At 3.6 this case ran
    route, plan and process — and `check` and `doctor` died in a real install ("No module named
    'identity'", a pyproject read beside site-packages): a window smaller than the defect. It now
    runs the contract itself, the environment report, the roster and a dispatched instrument, from a
    directory that is not the atlas, with nothing importable but what ships.
    """
    import re as _re
    import shutil as _shutil
    import subprocess as _sub
    import tempfile as _temp

    shipped = _re.findall(r'"([a-z_][a-z0-9_]*)"', _re.search(
        r"py-modules = \[(.*?)\]", (ROOT / "pyproject.toml").read_text(), _re.S).group(1))
    staging = Path(_temp.mkdtemp())
    for name in shipped:
        _shutil.copy(ROOT / "scripts" / f"{name}.py", staging / f"{name}.py")
    env = {"THEA_ROOT": str(ROOT), "PYTHONPATH": str(staging), "PATH": os.environ["PATH"]}
    runs = (
        (["route", "scripts/doctor.py"], "python"),
        (["process", "implementation"], "source_change"),
        (["plan", "scripts/doctor.py", "--task", "implementation", "--change", "source_change"], "unit_tests"),
        (["commands", "--json"], '"thea-commands/1"'),
        (["doctor"], "python"),
        (["staleness", "oldest", "1"], "least recently edited"),
        (["check"], "contract"),
    )
    for argv, needle in runs:
        done = _sub.run([sys.executable, str(staging / "atlas_cli.py"), *argv], cwd=staging,
                        capture_output=True, text=True, env=env, check=False, timeout=600)
        assert done.returncode == 0 and needle in done.stdout, \
            f"`thea {' '.join(argv)}` fails in an install: rc={done.returncode} {(done.stderr or done.stdout)[-300:]}"
    _shutil.rmtree(staging)
    CASES.append((f"an install shipping {len(shipped)} module(s) runs {len(runs)} commands, check and doctor included",
                  "a wheel that routes and cannot check, which a checkout can never reveal because every "
                  "module is present in it"))
    print(f"  ok    simulated install: {len(shipped)} shipped module(s) run {len(runs)} commands, check included")


def _mcp_problems() -> list[str]:
    """Speak MCP to thea_mcp.py on stdio and list every way it disagrees with the CLI."""
    import commands as _commands
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "x", "capabilities": {}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "gate", "arguments": {"path": "scripts/doctor.py", "json": True}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "check", "arguments": {"fix": True}}},
            {"jsonrpc": "2.0", "id": 5, "method": "no/such"}]
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "thea_mcp.py")], cwd="/tmp", timeout=600,
                          input="\n".join(json.dumps(m) for m in msgs) + "\n", capture_output=True, text=True, check=False)
    replies = {r.get("id"): r for r in map(json.loads, done.stdout.splitlines())}
    problems = []
    if set(replies) != {1, 2, 3, 4, 5}:
        problems.append(f"answered ids {sorted(replies, key=str)}; a notification must get no reply, every request one")
    if replies.get(1, {}).get("result", {}).get("serverInfo", {}).get("version") != str(atlas.atlas().get("version")):
        problems.append("initialize does not report the contract version")
    declared = str((atlas.atlas().get("external_versions") or {}).get("mcp_specification"))
    if replies.get(1, {}).get("result", {}).get("protocolVersion") != declared:
        problems.append("initialize echoed an unknown protocol version instead of answering the one it supports")
    parser, _ = _commands.build_parser()
    sub = next(a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction")  # noqa: SLF001
    listed = replies.get(2, {}).get("result", {}).get("tools", [])
    if sorted(t["name"] for t in listed) != sorted(sub.choices):
        problems.append("tools/list is not the CLI's own command list")
    for tool in listed:
        if (tool.get("annotations") or {}).get("readOnlyHint") is not True:
            problems.append(f"tool '{tool['name']}' does not declare readOnlyHint")
        writes = {"fix", "write", "run"} & set(tool["inputSchema"]["properties"])
        if writes:
            problems.append(f"tool '{tool['name']}' offers write flag(s) {sorted(writes)} on the read-only route")
    gate = replies.get(3, {}).get("result", {})
    if gate.get("isError") or '"runnable"' not in gate.get("content", [{}])[0].get("text", ""):
        problems.append("tools/call gate did not return the CLI's JSON record")
    if not replies.get(4, {}).get("result", {}).get("isError"):
        problems.append("tools/call check with fix=true was not refused")
    if replies.get(5, {}).get("error", {}).get("code") != -32601:
        problems.append("an unknown method is not answered method-not-found")
    return problems


def cli_and_mcp_cases() -> None:
    """One CLI, one roster, one MCP route over it — each property planted and refused (3.7.0)."""
    import commands as _commands
    from packmanifest import validate
    # PLANTED IN A PARSER, NOT A FILE: the contract runs in this process, so a mutated .py is never
    # re-imported — the first draft of this case planted nothing and the harness said so.
    parser, sub = _commands.build_parser()
    sub.add_parser("planted", help="")
    if _commands.cli_errors() or not any("'planted'" in e for e in _commands.cli_errors(parser)):
        raise SystemExit("FAIL cli_errors does not refuse a command with no help line, or refuses the real parser")
    CASES.append(("a command with no help line FAILS", "a command nobody but its author can find"))
    print("  ok    a command with no help line FAILS")
    schema = json.loads((ROOT / "tools/thea-commands.schema.json").read_text())
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        _commands.commands(True)
    record = json.loads(out.getvalue())
    broken = {**record, "commands": [{k: v for k, v in record["commands"][0].items() if k != "summary"}]}
    if validate(record, schema, "thea commands --json") or not validate(broken, schema, "planted"):
        raise SystemExit("FAIL the command roster does not satisfy thea-commands/1, or the schema accepts a row with no summary")
    CASES.append((f"the {len(record['commands'])}-row command roster satisfies thea-commands/1; a row missing its summary is refused",
                  "a roster a front end or MCP server parses that is whatever the producer printed today"))
    print(f"  ok    thea commands --json: {len(record['commands'])} rows validate; a planted bad row is refused")
    problems = _mcp_problems()
    if problems:
        raise SystemExit("FAIL thea_mcp: " + "; ".join(problems))
    CASES.append(("thea-mcp speaks MCP: lists the CLI's own commands, returns their records, refuses writes",
                  "an MCP server that re-implements the CLI and drifts from it, or offers a write"))
    print("  ok    thea-mcp: initialize, tools/list = the CLI, tools/call returns records, writes refused")
    with mutated("scripts/thea_mcp.py", lambda s: s.replace('MUTATING = {"--write", "--run", "--fix"}',
                                                             'MUTATING = {"--write", "--run"}', 1)):
        planted = _mcp_problems()
    if not any("fix" in p for p in planted):
        raise SystemExit("FAIL the MCP probe did not notice a write flag planted back into the read-only route")
    CASES.append(("a write flag planted into the MCP route is caught", "a probe that passes whatever the server offers"))
    print("  ok    thea-mcp: a planted write flag is caught by the probe")
