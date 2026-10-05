#!/usr/bin/env python3
"""The install, the CLI and the MCP route, split out of atlas_test.py to keep it under the shape cap.

Named *_test.py because it IS a test harness. Like atlas_guards_test, run() takes the RUNNING
atlas_test module and registers into its counted CASES: a fresh `import atlas_test` would be a
second copy whose cases nobody counts.

  install_cases       only what the wheel ships, run from outside the atlas: check, doctor, roster, an instrument
  cli_and_mcp_cases   every command has a help line; the roster satisfies thea-commands/1; thea-mcp speaks
                      MCP, lists the CLI's own commands and refuses writes — each property planted and refused
  cli_record_cases    every `--json` command's real record against tools/atlas-output.schema.json; an
                      unoffered record and an undeclared id each planted and refused
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
    entry_refusal_cases()
    cli_and_mcp_cases()
    compact_context_cases()
    cli_record_cases()


def _compact_context_problems() -> list[str]:
    """Check the actual CLI packet against the declarations its consumer needs."""
    import agentpolicy
    import atlascore
    import dirscope
    from packmanifest import validate

    base = Path(__file__).resolve().parents[1]
    data = atlascore.atlas()
    schema = json.loads((base / "tools/codexbrief.schema.json").read_text())
    runtime = next(row for row in data["runtime_entry"] if row["id"] == "openai_codex")
    via = data["native_agent_tools"]["runtimes"]["openai_codex"]["thea_via"]
    scope, row = dirscope.scope_for("scripts/atlas.py")
    problems = []
    for change in ("source_change", "api_change"):
        done = subprocess.run([sys.executable, str(base / "scripts/codexbrief.py"), "--path",
                               "scripts/atlas.py", "--task", "implementation", "--change", change,
                               "--json"], cwd=base, capture_output=True, text=True, check=False, timeout=30)
        if done.returncode:
            problems.append(f"{change}: compact context crashed: {done.stderr[-180:]}")
            continue
        packet = json.loads(done.stdout)
        problems += validate(packet, schema, "compact context")
        expected = agentpolicy.required_gates({"change_class": change})
        if packet.get("gates") != expected:
            problems.append(f"{change}: gates {packet.get('gates')} differ from plan {expected}")
        if packet.get("runtime") != {"id": runtime["id"], "runtime": runtime["runtime"],
                                      "loads": runtime["loads"], "adapter": runtime["adapter"],
                                      "thea_via": via}:
            problems.append(f"{change}: runtime does not match runtime_entry/native_agent_tools")
        if packet.get("scope") != scope or [t["id"] for t in packet.get("traps") or []] != row["traps"]:
            problems.append(f"{change}: scope or traps differ from directory_scopes")
    return problems


def compact_context_cases() -> None:
    import agentpolicy
    problems = _compact_context_problems()
    if problems:
        raise SystemExit("FAIL compact context: " + "; ".join(problems))
    CASES.append(("compact context matches route, scope, runtime and inherited gates",
                  "a context packet that crashes or sends an agent an empty proof plan"))
    print("  ok    compact context: runtime, scope and inherited gates match the atlas")
    with mutated("scripts/codexbrief.py", lambda s: s.replace(
            'return required_gates({"change_class": change})', "return []", 1)):
        planted = _compact_context_problems()
    if not any("gates" in p for p in planted):
        raise SystemExit("FAIL compact context probe missed a planted empty gate plan")
    typos = []  # the same empty plan reached by a NAME: a typo'd class or modifier must refuse, not certify
    for contract in ({"change_class": "source_chnage"}, {"change_class": "source_change", "risk_modifiers": ["hotpath"]}):
        try:
            typos.append(f"{contract} planned {agentpolicy.required_gates(contract)}")
        except SystemExit:
            pass
    typos += _do_run_cwd_errors()
    if typos:
        raise SystemExit("FAIL an unknown change class or modifier planned, or do --run left the caller's tree: " + "; ".join(typos))
    CASES.append(("an empty compact gate plan is caught, a typo'd change class or modifier refuses, and do --run acts in the caller's tree",
                  "a routing projection that passes while dropping every required check, `--change nonsense` certified by all([]), "
                  "or a relative path run inside the atlas"))
    print("  ok    compact context: planted empty gates are refused")



def _do_run_cwd_errors() -> list[str]:
    """`do <path> <action> --run` from another tree runs THERE: the path was typed relative to it."""
    import tempfile
    from unittest import mock

    import agentpolicy
    import atlas
    ran: list = []
    with tempfile.TemporaryDirectory() as away, contextlib.chdir(away), contextlib.redirect_stdout(io.StringIO()), \
            mock.patch.object(atlas.subprocess, "run", lambda argv, **kw: ran.append(kw["cwd"]) or mock.Mock(returncode=0)):
        (Path(away) / "x.py").write_text("")
        action = next(a for a in atlas.atlas()["pack_actions"] if agentpolicy.action_command("python", a, "x.py")[0])
        atlas.do("x.py", action, True)
        here = Path(away).resolve()
    return [] if ran == [here] else [f"do --run ran in {ran}, not {here}"]

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


def _refusal(call) -> str:
    """The ConfigError message `call` raises, or a verdict naming what it did instead of refusing."""
    import atlas_cli
    try:
        got = call()
    except atlas_cli.ConfigError as exc:
        return str(exc)
    except Exception as exc:  # noqa: BLE001 — a crash is the defect this case plants, so it is reported
        return f"CRASHED {type(exc).__name__}: {exc}"
    return f"ACCEPTED {got!r}"


def _flag_problems() -> list[str]:
    """Every shape of a root flag with no value must be refused by name, never crash or fall through."""
    import atlas_cli
    problems = []
    for argv in (["check", "--atlas-root"], ["--atlas-root="], ["--atlas-root", "--where"],
                 ["--atlas-root", ".", "--atlas-root=."]):
        said = _refusal(lambda argv=argv: atlas_cli.resolve_root(argv, Path("/")))
        if "--atlas-root" not in said or said.startswith(("CRASHED", "ACCEPTED")):
            problems.append(f"{argv}: {said}")
    said = _refusal(lambda: atlas_cli.resolve_root(["--atlas-root=/x", "check"], Path("/"))[0])
    if said != f"ACCEPTED {Path('/x').resolve()!r}":
        problems.append(f"the `=` form with a value is not read as the root: {said}")
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = _refusal(lambda: atlas_cli.main(["check", "--atlas-root"]))
    if rc != "ACCEPTED 2" or "--atlas-root" not in err.getvalue():
        problems.append(f"main() with a trailing flag: rc={rc}, stderr={err.getvalue()[-160:]!r}")
    return problems


def _config_problems() -> list[str]:
    """Each unparseable or unknown line of a consumer config must be refused with its file:line."""
    import tempfile

    import atlas_cli
    good = "# pin\natlas:\n  ref: v1.0.0\n  root: ..\nstack_tiers:\n  edge:\n    suffixes: [.py]\n"
    planted = {  # body -> the line the refusal must name
        "atlas:\n  ref: v1\nrot: ..\n": 3,                 # an unknown top-level key, once skipped
        "atlas:\n  ref: v1\n  rooot: ..\n": 3,             # a typo under the pin
        "root: ..\n": 1,                                   # the flat form, once read from anywhere
        "atlas:\n  ref: v1\n  ref: v2\n": 3,               # a duplicate, once last-wins
        "atlas:\n  ref: [v1\n": 3,                         # unparseable, once half-read
        "atlas:\n  ref:\n": 2,                             # an empty value, once dropped
        "just a line with no colon\n": 1,                  # once skipped
    }
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp, ".atlas.yaml")
        path.write_text(good, encoding="utf-8")
        if _refusal(lambda: atlas_cli._config(Path(tmp))) != f"ACCEPTED ({{'ref': 'v1.0.0', 'root': '..'}}, {path!r})":
            problems.append(f"a valid config is not read as its pin: {_refusal(lambda: atlas_cli._config(Path(tmp)))}")
        for body, line in planted.items():
            path.write_text(body, encoding="utf-8")
            said = _refusal(lambda: atlas_cli._config(Path(tmp)))
            if not said.startswith(f"{path}:{line}:"):
                problems.append(f"{body!r}: wanted a refusal at {path.name}:{line}, got {said}")
    return problems


def entry_refusal_cases() -> None:
    """The install entry point refuses a root flag with no value and a config line it cannot read (3.47.0)."""
    problems = _flag_problems()
    if problems:
        raise SystemExit("FAIL a root flag with no value is not refused by name:\n  " + "\n  ".join(problems))
    CASES.append(("a root flag with no value is refused by name, never an IndexError or a silent fall-through",
                  "a trailing --atlas-root that crashes, and an empty --atlas-root= that runs another atlas"))
    print("  ok    a root flag with no value is refused by name")
    problems = _config_problems()
    if problems:
        raise SystemExit("FAIL a consumer config line is skipped or invented:\n  " + "\n  ".join(problems))
    CASES.append(("an unknown or unparseable consumer config line is refused at its file:line",
                  "a reader that skips what it does not understand, so a typo or a misplaced root moves the atlas"))
    print("  ok    an unknown or unparseable consumer config line is refused at its file:line")


def _mcp_problems() -> list[str]:
    """Speak MCP to thea_mcp.py on stdio and list every way it disagrees with the CLI."""
    import commands as _commands
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "x", "capabilities": {}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "gate", "arguments": {"path": "scripts/doctor.py", "json": True}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "check", "arguments": {"fix": True}}},
            {"jsonrpc": "2.0", "id": 5, "method": "no/such"},
            [1], {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": [1]}]
    # EVERY DECLARED REVISION IS ANSWERED IN KIND (3.10.1). The probe above asks with "x" and so proves only
    # the fallback; a real client asks with a real revision, and a route that answers every one with the
    # fallback passes that probe while refusing every client that is not on mcp_specification.
    revisions = {k: str(v) for k, v in (atlas.atlas().get("external_versions") or {}).items() if k.startswith("mcp_")}
    msgs += [{"jsonrpc": "2.0", "id": f"rev:{k}", "method": "initialize", "params": {"protocolVersion": v, "capabilities": {}}}
             for k, v in revisions.items()]
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "thea_mcp.py")], cwd="/tmp", timeout=600,
                          input="\n".join(json.dumps(m) for m in msgs) + "\n", capture_output=True, text=True, check=False)
    replies = {r.get("id"): r for r in map(json.loads, done.stdout.splitlines())}
    problems = []
    if set(replies) != {None, 1, 2, 3, 4, 5, 6} | {f"rev:{k}" for k in revisions}:
        problems.append(f"answered ids {sorted(replies, key=str)}; a notification must get no reply, every request one")
    if {replies.get(i, {}).get("error", {}).get("code") for i in (None, 6)} != {-32600}:
        problems.append("a non-object message or non-object params is not answered invalid-request")
    if replies.get(1, {}).get("result", {}).get("serverInfo", {}).get("version") != str(atlas.atlas().get("version")):
        problems.append("initialize does not report the contract version")
    declared = str((atlas.atlas().get("external_versions") or {}).get("mcp_specification"))
    if replies.get(1, {}).get("result", {}).get("protocolVersion") != declared:
        problems.append("initialize echoed an unknown protocol version instead of answering the one it supports")
    for key, revision in revisions.items():
        if replies.get(f"rev:{key}", {}).get("result", {}).get("protocolVersion") != revision:
            problems.append(f"initialize asked for declared revision {key} and answered another, which the client refuses")
    listed = replies.get(2, {}).get("result", {}).get("tools", [])
    if sorted(t["name"] for t in listed) != sorted(_commands.command_table()):
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
    if (gate.get("structuredContent") or {}).get("exit") != 0 or '"runnable"' not in json.dumps(gate["structuredContent"].get("record")):
        problems.append("tools/call gate does not carry structuredContent {exit, record}")
    port = next((t["inputSchema"]["properties"] for t in listed if t["name"] == "port"), {})
    if "enum" not in port.get("lens", {}):
        problems.append("a choices argument reaches the schema without its enum")
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
    sub.add_parser("planted_mute", help="a command with no --json and no reason")
    hidden = min(set(_commands.instruments_on_path()) - set(sub.choices))  # an instrument only the epilog names
    parser.epilog = parser.epilog.replace(f" {hidden},", " ").replace(f", {hidden}", "")
    if _commands.cli_errors() or not all(any(f"'{n}'" in e for e in _commands.cli_errors(parser))
                                         for n in ("planted", "planted_mute", hidden)):
        raise SystemExit("FAIL cli_errors misses a command with no help line, one with no --json and no "
                         "reason, or an instrument --help omits — or refuses the real parser")
    CASES.append(("a command with no help line FAILS", "a command nobody but its author can find"))
    runs = _commands.runs_when_executed
    if "atlascore" in _commands.instruments_on_path() or "vaultlinks" not in _commands.instruments_on_path() \
            or runs("import x\nif x:\n    '__main__'\nT.update(x)\n") or not runs('if __name__ == "__main__":\n    main()\n'):
        raise SystemExit("FAIL a library with no main block is offered as a runnable instrument")
    CASES.append(("a declared library with no main block is not offered as `thea <name>`",
                  "`thea atlascore` printing nothing and exiting 0, a blind run read as a pass"))
    planted = ROOT / "scripts" / "planted_argparse_reader.py"
    planted.write_text("names = [c.dest for c in sub." + "_choices_actions]\n", encoding="utf-8")  # split: the tree scan reads this file
    try:
        caught = _commands.argparse_reader_errors([planted])
    finally:
        planted.unlink()
    if _commands.argparse_reader_errors() or not caught:
        raise SystemExit(f"FAIL argparse_reader_errors misses a private read outside commands.py, or flags the tree: {caught}")
    CASES.append(("a module outside commands.py reading argparse privates FAILS",
                  "a stdlib change breaking four copies of the same private read one at a time"))
    print("  ok    a command with no help line FAILS")
    schema = json.loads((ROOT / "tools/thea-commands.schema.json").read_text())
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        _commands.commands(True)
    record = json.loads(out.getvalue())
    broken = {**record, "commands": [{k: v for k, v in record["commands"][0].items() if k != "summary"}]}
    gate_row = next(r for r in record["commands"] if r["name"] == "gate")
    if validate(record, schema, "thea commands --json") or not validate(broken, schema, "planted") \
            or gate_row["arguments"][:2] != ["path", "gate"] or "--json" not in gate_row["arguments"]:
        raise SystemExit("FAIL the command roster does not satisfy thea-commands/1, a command row lacks its arguments, "
                         "or the schema accepts a row with no summary")
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
    with mutated("scripts/thea_mcp.py", lambda s: s.replace('"protocolVersion": asked if asked in supported else declared',
                                                             '"protocolVersion": declared', 1)):
        planted = _mcp_problems()
    if not any("declared revision" in p for p in planted):
        raise SystemExit("FAIL the MCP probe did not notice a route answering every client with the fallback revision")
    CASES.append(("a route answering every declared revision with the fallback is caught",
                  "a handshake probed only with a revision the server already treats as unknown"))
    print("  ok    thea-mcp: a route that ignores the client's declared revision is caught")
    for needle, mutant, sign in (("reply = _guarded(handler, message)", "reply = handler(message)", "answered ids"),
                                 ('"exit": done.returncode,', "", "structuredContent"),
                                 ('kind |= {"enum"', 'kind |= {"enun"', "enum")):
        with mutated("scripts/thea_mcp.py", lambda s, n=needle, m=mutant: s.replace(n, m, 1)):
            if not any(sign in p for p in _mcp_problems()):
                raise SystemExit(f"FAIL the MCP probe did not notice the planted '{mutant}' in place of '{needle}'")
    checked = subprocess.run([sys.executable, str(ROOT / "scripts" / "thea_mcp.py"), "--check"], cwd="/tmp",
                             timeout=600, capture_output=True, text=True, check=False)
    if checked.returncode != 0 or "probes held" not in checked.stdout:
        raise SystemExit(f"FAIL thea-mcp --check: rc={checked.returncode} {checked.stdout[-300:]}")
    CASES.append(("an unguarded loop, a result without its verdict as data, or a schema dropping choices is caught",
                  "one malformed message ending the session; a client re-parsing text to learn the exit code"))
    print("  ok    thea-mcp: an unguarded loop, a dropped structured verdict and a dropped enum are each caught")


def cli_record_cases() -> None:
    """EVERY `--json` COMMAND'S REAL OUTPUT, against the frozen schema (3.47.0).

    A review found `port` emitting `thea-port/1` against no declaration while the documents called every
    `--json` record frozen: atlas_test.external_api_cases built its records by hand, from the producers it knew.
    Here the sample set is asserted EQUAL to the roster's `--json` commands, so a new one arrives with a
    sample or this fails; `commands` is held by its own schema, and `verify` by its one producer, because
    running verify inside the suite verify runs would recurse.
    """
    import tempfile

    import commands
    import packmanifest
    import verify

    schema = json.loads((ROOT / "tools/atlas-output.schema.json").read_text(encoding="utf-8"))
    try:  # the independent JSON Schema reference, when this machine has it
        from jsonschema import Draft202012Validator
        reference = Draft202012Validator(schema)
    except ImportError:
        reference = None

    def emitted(argv: list[str]) -> str:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.suppress(SystemExit):
            atlas.main(argv)
        return buf.getvalue()

    tmp = Path(tempfile.mkdtemp(prefix="thea-records-"))
    (tmp / "pick.yaml").write_text(emitted(["brainstorm", "--new", "pick a cache"]), encoding="utf-8")
    here = "scripts/doctor.py"
    samples = {"check": [["check", "--json"], ["check", "--fix", "--json"]], "doctor": [["doctor", "--json"]],
               "intake": [["intake", f"fix a bug in {here}", "--json"], ["intake", "add a cache", "--json"]],
               "shell": [["shell", "--json", "ls -la"]], "delegate": [["delegate", "--json"]],
               "handoff": [["handoff", here, "--json"]], "cadence": [["cadence", "--json"]],
               "role": [["role", r, "--json"] for r in atlas.atlas().get("agent_roles") or {}],
               "resume": [["resume", "--json"]], "steps": [["steps", here, "--json"]],
               "failures": [["failures", "--json"], ["failures", "--for", here, "--json"]],
               "successes": [["successes", "--json"], ["successes", "--for", here, "--json"]],
               "brainstorm": [["brainstorm", str(tmp / "pick.yaml"), "--json"]],
               "port": [["port", here, "--frame", f, "--json"] for f in ("agent", "chat", "model")]
               + [["port", "scripts", "--json"], ["port", ".", "--json"]],
               "route": [], "plan": [], "gate": [], "decide": [], "process": []}  # swept above, by producer
    takes_json = {n for n, c in commands.command_table().items() if any("--json" in a.option_strings for a in c["arguments"])}
    unsampled = (takes_json ^ set(samples)) - {"commands", "verify"}  # own schema; one producer, below
    assert not unsampled, f"--json commands and samples disagree: {sorted(unsampled)}"
    records = []
    from unittest import mock
    with mock.patch.object(atlas, "_repair", lambda: print("repaired")):  # --fix narrates; it never writes here
        for argv in (a for rows in samples.values() for a in rows):
            records.append(json.loads(emitted(argv)))
    rows = [verify.run_gate({"id": f"probe_{n}", "argv": argv}) for n, argv in
            (("pass", ["python", "-c", "pass"]), ("fail", ["python", "-c", "raise SystemExit(1)"]),
             ("absent", ["thea-no-such-binary"]))] + [verify.unpushed_row()]
    assert [r["verdict"] for r in rows[:3]] == ["PASS", "FAIL", "NOT RUN"], "verify rows did not cover each verdict"
    records.append(verify.record(rows, {v: sum(r["verdict"] == v for r in rows) for v in
                                        ("PASS", "REUSED", "FAIL", "NOT RUN")}, 1))
    for record in records:
        where = str(record.get("command") or record.get("schema"))
        bad = packmanifest.validate(record, schema, where)
        assert not bad, f"{where} record violates the frozen output schema: {bad[:2]}"
        if reference is not None:
            ref_bad = [e.message[:160] for e in reference.iter_errors(record)]
            assert not ref_bad, f"{where}: the JSON Schema reference refuses what this validator accepts: {ref_bad[:1]}"
    covered = {str(r.get("command") or r["schema"].removeprefix("thea-").split("/")[0]) for r in records}
    assert covered == set(samples) - {"route", "plan", "gate", "decide", "process"} | {"verify"}, f"covered {sorted(covered)}"
    CASES.append((f"every --json command's real output satisfies the frozen schema ({len(records)} records)",
                  "a command whose record ships against no declaration while the documents call it frozen"))
    print(f"  ok    {len(records)} real --json records, every --json command, validate against the frozen schema")
    with mutated("tools/atlas-output.schema.json", lambda s: s.replace('"$ref": "#/$defs/port"', '"$ref": "#/$defs/brainstorm"', 1)):
        case("a --json command its schema does not offer FAILS", "a record consumers are told is frozen and "
             "no schema declares", True, "`thea port --json` emits a record")
    with mutated("tools/atlas-output.schema.json", lambda s: s.replace('"const": "thea-port/1"', '"const": "thea-port/2"', 1)):
        case("a record id an instrument emits and no schema declares FAILS", "an id the producer prints that "
             "no consumer can pin", True, "emits record id thea-port/1")


if __name__ == "__main__":
    if sys.argv[1:] != ["--brief-smoke"]:
        raise SystemExit("usage: python scripts/cli_test.py --brief-smoke")
    found = _compact_context_problems()
    if found:
        raise SystemExit("FAIL compact context: " + "; ".join(found))
    print("compact context: 2 change classes match route, scope, runtime and gates")
