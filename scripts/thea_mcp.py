#!/usr/bin/env python3
"""Thea as an MCP server: the same commands `thea` answers, offered as tools over stdio.

WHY A ROUTE, NOT A SECOND SYSTEM (3.7.0). Every tool here is a `thea` command, listed from the one
parser in commands.py and run as `atlas.py <command>` in a subprocess. So an MCP client, a shell and
a future front end get the same answer to the same question, and nothing here can drift from the CLI
because nothing here re-implements it. Its schema is derived from the parser's arguments.

THE MCP ROUTE IS READ-ONLY BY CONSTRUCTION. Flags that write (`--write`, `--run`, `--fix`) never
appear in a tool's schema and are refused if sent; instruments (which include landing and pushing)
are not offered at all. A client cannot set them wrongly because it cannot set them.

Transport: newline-delimited JSON-RPC 2.0 on stdin/stdout (MCP stdio). Each call runs in its own
process with a timeout, so a command's prints never reach the protocol stream and a changed
atlas.yaml is read fresh on every call. That process is forked from this one with the modules already
imported and every cache emptied, not spawned: a spawned call paid the imports each time. Resources are the atlas.yaml sections, read on demand; prompts
are the two questions asked most. Every call result carries `structuredContent.exit`, the verdict, and
`structuredContent.record` when the command was asked for --json and printed one.

  python scripts/thea_mcp.py                 serve on stdio
  python scripts/thea_mcp.py --check         speak the protocol to itself once; the exit code is the verdict
  claude mcp add thea -e THEA_ROOT=<atlas> -- thea-mcp    register an installed copy with Claude Code
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import selectors
import signal
import subprocess
import sys
import time
import traceback

from atlascore import ROOT, atlas
from commands import command_table

MUTATING = {"--write", "--run", "--fix"}  # the safe route is incapable of these, not flagged against them
TIMEOUT = 600
# Hints for a client's UI only — a client must treat them as untrusted, so the guarantee stays the construction.
ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


def _arguments(command: str) -> list[argparse.Action]:
    return [a for a in command_table()[command]["arguments"] if not (set(a.option_strings) & MUTATING)]


def _schema(command: str) -> dict:
    """A JSON Schema for one command, read off its argparse arguments — never typed twice."""
    props, required = {}, []
    for action in _arguments(command):
        if isinstance(action, argparse._StoreTrueAction):  # noqa: SLF001
            kind = {"type": "boolean"}
        elif action.nargs in ("+", "*") or isinstance(action, argparse._AppendAction):  # noqa: SLF001
            kind = {"type": "array", "items": {"type": "string"}}
        else:
            kind = {"type": {int: "integer", float: "number"}.get(action.type, "string")}
        kind |= {"enum": list(action.choices)} if action.choices else {}
        kind |= {"default": action.default} if action.default not in (None, False, [], argparse.SUPPRESS) else {}
        props[action.dest] = {**kind, "description": action.help or action.dest}
        if not action.option_strings and action.nargs not in ("?", "*"):
            required.append(action.dest)
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def tools() -> list[dict]:
    return [
        {"name": name, "description": row["help"], "inputSchema": _schema(name), "annotations": ANNOTATIONS}
        for name, row in command_table().items()
    ]


def _argv(command: str, arguments: dict) -> list[str]:
    known = {a.dest: a for a in _arguments(command)}
    unknown = sorted(set(arguments) - set(known))
    if unknown:
        raise ValueError(f"'{command}' takes no argument(s) {unknown} over MCP — writes are refused on this route")
    argv, tail = [command], []
    for dest, action in known.items():
        if dest not in arguments:
            continue
        value = arguments[dest]
        if not action.option_strings:
            tail += [str(v) for v in value] if isinstance(value, list) else [str(value)]
        elif isinstance(action, argparse._StoreTrueAction):  # noqa: SLF001
            argv += [action.option_strings[0]] if value else []
        elif isinstance(value, list):
            for v in value:
                argv += [action.option_strings[0], str(v)]
        else:
            argv += [action.option_strings[0], str(value)]
    return argv[:1] + tail + argv[1:]


def _scripts_modules() -> list:
    return [m for m in list(sys.modules.values()) if str(getattr(m, "__file__", "")).startswith(str(ROOT / "scripts"))]


def _source_stamp() -> tuple:
    return tuple(sorted((m.__file__, os.stat(m.__file__).st_mtime_ns) for m in _scripts_modules()))


_WARM: dict = {}


def _forkable() -> bool:
    """FORK ONLY WHAT IS STILL THE SOURCE (3.50.0). The warm parent holds imported code; once a module file
    changes on disk that code is stale, and a fork would answer with it. Every call after that spawns."""
    if not hasattr(os, "fork") or os.environ.get("THEA_MCP_ISOLATE"):
        return False
    if not _WARM:
        import atlas as _atlas  # noqa: F401 — the import is the warm-up

        _WARM["stamp"] = _source_stamp()
    return _WARM["stamp"] == _source_stamp()


def _child(argv: list[str], out: int, err: int) -> None:
    """In the fork: the old subprocess's isolation, rebuilt. Fresh caches, read-only env, own fds; never returns."""
    code = 1
    try:
        for module in _scripts_modules():  # every lru_cache, found rather than listed: a list goes stale
            for value in list(vars(module).values()):
                if callable(getattr(value, "cache_clear", None)) and hasattr(value, "cache_info"):
                    value.cache_clear()
        os.environ["THEA_READ_ONLY"] = "1"
        null = os.open(os.devnull, os.O_RDONLY)
        for source, target in ((null, 0), (out, 1), (err, 2)):
            os.dup2(source, target)
        sys.argv = [str(ROOT / "scripts" / "atlas.py"), *argv]
        import atlas as _atlas

        code = _atlas.main(argv) or 0
    except SystemExit as exit_:
        code = exit_.code if isinstance(exit_.code, int) else (0 if exit_.code is None else 1)
        if not isinstance(exit_.code, (int, type(None))):
            print(exit_.code, file=sys.stderr)
    except BaseException:  # noqa: BLE001 — the child's last word is the traceback, as a crashed subprocess's was
        traceback.print_exc()
    finally:
        with contextlib.suppress(Exception):
            sys.stdout.flush()
            sys.stderr.flush()
        os._exit(code if isinstance(code, int) else 1)


def _forked(argv: list[str]) -> subprocess.CompletedProcess:
    """Fork, read both pipes until EOF or TIMEOUT, kill on expiry. Raises TimeoutExpired as subprocess.run did."""
    pipes = [os.pipe(), os.pipe()]
    sys.stdout.flush()
    sys.stderr.flush()
    pid = os.fork()
    if pid == 0:
        _child(argv, pipes[0][1], pipes[1][1])
    for _, write in pipes:
        os.close(write)
    chunks: dict[int, list[bytes]] = {read: [] for read, _ in pipes}
    deadline = time.monotonic() + TIMEOUT
    with selectors.DefaultSelector() as sel:
        for read in chunks:
            sel.register(read, selectors.EVENT_READ)
        while sel.get_map() and time.monotonic() < deadline:
            for key, _ in sel.select(deadline - time.monotonic()):
                data = os.read(key.fd, 65536)
                if data:
                    chunks[key.fd].append(data)
                else:
                    sel.unregister(key.fd)
        expired = bool(sel.get_map())
    for read in chunks:
        os.close(read)
    if expired:
        os.kill(pid, signal.SIGKILL)
    status = os.waitpid(pid, 0)[1]
    if expired:
        raise subprocess.TimeoutExpired(argv, TIMEOUT)
    text = [b"".join(chunks[read]).decode(errors="replace") for read, _ in pipes]
    return subprocess.CompletedProcess(argv, os.waitstatus_to_exitcode(status), *text)


def call(name: str, arguments: dict) -> dict:
    if name not in command_table():
        return {"content": [{"type": "text", "text": f"no tool '{name}'; tools/list names every one"}], "isError": True}
    try:
        argv = _argv(name, arguments or {})
    except ValueError as refused:
        return {"content": [{"type": "text", "text": str(refused)}], "isError": True}
    try:
        # THE CLIENT'S DIRECTORY, NOT THE ATLAS: a relative path names the consumer's file. The first draft
        # ran in ROOT, so `route app.py` answered for a file in the atlas the client never meant.
        done = (
            _forked(argv)
            if _forkable()
            else subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "atlas.py"), *argv],
                env={**os.environ, "THEA_READ_ONLY": "1"},  # noqa: S603
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                check=False,
            )
        )
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": f"thea {name} timed out after {TIMEOUT}s"}], "isError": True}
    text = done.stdout + (f"\n[stderr]\n{done.stderr}" if done.stderr.strip() else "")
    # THE VERDICT TRAVELS AS DATA: the text carried the exit code only when stdout was empty, so a client
    # read "a verdict 1 with findings" and "a crash" as the same isError. The record rides beside it.
    try:
        record = json.loads(done.stdout) if arguments.get("json") else None
    except ValueError:
        record = None
    return {
        "content": [{"type": "text", "text": text.strip() or f"exit {done.returncode}"}],
        "structuredContent": {"exit": done.returncode, **({"record": record} if record is not None else {})},
        "isError": done.returncode != 0,
    }


def handle(message: dict) -> dict | None:
    """One JSON-RPC message in, one response out (None for a notification)."""
    method, ident = message.get("method"), message.get("id")
    if ident is None:
        return None
    params = message.get("params") or {}
    if method == "initialize":
        # NEVER ECHO AN UNKNOWN VERSION (3.9.2). The spec: answer the client's version only if the server
        # supports it, else the latest it does. Echoing claimed support for any revision a client named,
        # including one not yet written. Supported = the declared spec plus the published revisions that
        # keep initialize, tools/list and tools/call unchanged — the only methods this route uses.
        declared = str((atlas().get("external_versions") or {}).get("mcp_specification") or "")
        asked = params.get("protocolVersion")
        supported = {str(v) for k, v in (atlas().get("external_versions") or {}).items() if k.startswith("mcp_")}
        result = {
            "protocolVersion": asked if asked in supported else declared,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {"name": "thea", "version": str(atlas().get("version"))},
            "instructions": "Route before reading: `route` or `gate` a file first, then load only what it "
            "names. Every tool is a read-only `thea` command; its exit code is the verdict.",
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": tools()}
    elif method == "tools/call":
        result = call(str(params.get("name")), params.get("arguments") or {})
    elif method in ("resources/list", "resources/read", "prompts/list", "prompts/get"):
        try:
            result = CONTEXT[method](params)
        except KeyError as missing:
            return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32602, "message": f"unknown: {missing}"}}
    else:
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": ident, "result": result}


# CONTEXT ON DEMAND, NOT IN THE TOOL LIST (3.14.0). A tool list is paid on every request; a resource is
# paid only when read. Each atlas.yaml section is one resource, so a client pulls the block a route names
# and nothing else — the progressive disclosure the entry files practise, offered to an MCP client.
# Prompts are the two questions asked most: plan a change to a file, review a diff against its gates.
PROMPTS = {
    "plan-change": ("the ordered steps that prove a change to one file, for this runtime", "path"),
    "review-diff": ("check a pasted diff against the gates its change class requires", "diff"),
}
PROMPT_ARGUMENTS = {
    "path": "the file the change touches, relative to the client's directory",
    "diff": "a unified diff, as `git diff` prints it",
}


def _resources(_params: dict) -> dict:
    return {
        "resources": [
            {
                "uri": f"thea://atlas/{key}",
                "name": key,
                "mimeType": "application/yaml",
                "description": f"atlas.yaml/{key}",
            }
            for key in atlas()
        ]
    }


def _read(params: dict) -> dict:
    import yaml  # noqa: PLC0415

    uri = str(params.get("uri"))
    key = uri.removeprefix("thea://atlas/")
    if not uri.startswith("thea://atlas/") or key not in atlas():
        raise KeyError(uri)
    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": "application/yaml",
                "text": yaml.safe_dump({key: atlas()[key]}, sort_keys=False, allow_unicode=True),
            }
        ]
    }


def _prompts(_params: dict) -> dict:
    return {
        "prompts": [
            {
                "name": n,
                "description": d,
                "arguments": [{"name": arg, "description": PROMPT_ARGUMENTS[arg], "required": True}],
            }
            for n, (d, arg) in PROMPTS.items()
        ]
    }


def _prompt(params: dict) -> dict:
    name, args = str(params.get("name")), params.get("arguments") or {}
    if name not in PROMPTS:
        raise KeyError(name)
    text = (
        f"Run `thea steps {args.get('path', '<path>')}` (or the steps tool) and follow each step in order; "
        "stop at the first gate that fails and report it with its exit code."
        if name == "plan-change"
        else "For this diff: name each file's route, the gates its change class requires, and any "
        "agent_failure_modes shape it matches; the verdict is a gate's exit code, never your reading.\n\n"
        + str(args.get("diff", ""))
    )
    return {"description": PROMPTS[name][0], "messages": [{"role": "user", "content": {"type": "text", "text": text}}]}


CONTEXT = {"resources/list": _resources, "resources/read": _read, "prompts/list": _prompts, "prompts/get": _prompt}


def _guarded(handler, message: object) -> dict | None:
    """ONE BAD MESSAGE MUST NOT END THE SESSION: a batch, a bare value or a handler's exception killed the
    stdio loop, and the client saw only a dropped connection. Each now answers as a JSON-RPC error."""
    if not isinstance(message, dict) or not isinstance(message.get("params", {}), (dict, type(None))):
        return {
            "jsonrpc": "2.0",
            "id": message.get("id") if isinstance(message, dict) else None,
            "error": {"code": -32600, "message": "invalid request: one JSON object with object params"},
        }
    try:
        return handler(message)
    except Exception as crash:  # noqa: BLE001 — the boundary: every failure becomes a reply
        return {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {"code": -32603, "message": f"{type(crash).__name__}: {crash}"},
        }


def self_check() -> int:
    """`--check`: initialize, list, call and refuse once, in process; prints one line per probe."""
    probes = [
        ("initialize", {"protocolVersion": "0"}, lambda r: r["result"]["serverInfo"]["name"] == "thea"),
        ("tools/list", {}, lambda r: any(t["name"] == "route" for t in r["result"]["tools"])),
        (
            "tools/call",
            {"name": "route", "arguments": {"path": "x.py", "json": True}},
            lambda r: r["result"]["structuredContent"]["exit"] == 0 and "record" in r["result"]["structuredContent"],
        ),
        ("tools/call", {"name": "index", "arguments": {"write": True}}, lambda r: r["result"]["isError"]),
        ("resources/list", {}, lambda r: bool(r["result"]["resources"])),
    ]
    failed = 0
    for number, (method, params, holds) in enumerate(probes, 1):
        reply = _guarded(handle, {"jsonrpc": "2.0", "id": number, "method": method, "params": params})
        try:
            ok = bool(holds(reply))
        except (KeyError, TypeError, IndexError):
            ok = False
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {method} {params.get('name', '')}".rstrip())
    print(f"thea-mcp --check: {len(probes) - failed} of {len(probes)} probes held")
    return 1 if failed else 0


def serve(handler=None) -> int:
    """The stdio loop, shared: the edit route passes its own handler rather than copying this."""
    handler = handler or handle
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            reply = _guarded(handler, message)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(self_check() if "--check" in sys.argv[1:] else serve())
