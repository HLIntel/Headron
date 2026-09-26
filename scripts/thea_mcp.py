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
atlas.yaml is read fresh on every call. SCAFFOLD: tools only — no resources or prompts yet.

  python scripts/thea_mcp.py                 serve on stdio
  claude mcp add thea -- thea-mcp            register an installed copy with Claude Code
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

from atlascore import ROOT, atlas
from commands import build_parser

MUTATING = {"--write", "--run", "--fix"}  # the safe route is incapable of these, not flagged against them
TIMEOUT = 600
# Hints for a client's UI only — a client must treat them as untrusted, so the guarantee stays the construction.
ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


def _subparsers() -> dict[str, argparse.ArgumentParser]:
    parser, _ = build_parser()
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))  # noqa: SLF001
    return {c.dest: sub.choices[c.dest] for c in sub._choices_actions}  # noqa: SLF001


def _helps() -> dict[str, str]:
    parser, _ = build_parser()
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))  # noqa: SLF001
    return {c.dest: c.help or "" for c in sub._choices_actions}  # noqa: SLF001


def _arguments(command: str) -> list[argparse.Action]:
    return [a for a in _subparsers()[command]._actions  # noqa: SLF001
            if a.dest != "help" and not (set(a.option_strings) & MUTATING)]


def _schema(command: str) -> dict:
    """A JSON Schema for one command, read off its argparse arguments — never typed twice."""
    props, required = {}, []
    for action in _arguments(command):
        if isinstance(action, argparse._StoreTrueAction):  # noqa: SLF001
            kind = {"type": "boolean"}
        elif action.nargs in ("+", "*") or isinstance(action, argparse._AppendAction):  # noqa: SLF001
            kind = {"type": "array", "items": {"type": "string"}}
        elif action.type is int:
            kind = {"type": "integer"}
        else:
            kind = {"type": "string"}
        props[action.dest] = {**kind, "description": action.help or action.dest}
        if not action.option_strings and action.nargs not in ("?", "*"):
            required.append(action.dest)
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def tools() -> list[dict]:
    helps = _helps()
    return [{"name": name, "description": helps[name], "inputSchema": _schema(name), "annotations": ANNOTATIONS}
            for name in _subparsers()]


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


def call(name: str, arguments: dict) -> dict:
    if name not in _subparsers():
        return {"content": [{"type": "text", "text": f"no tool '{name}'; tools/list names every one"}], "isError": True}
    try:
        argv = _argv(name, arguments or {})
    except ValueError as refused:
        return {"content": [{"type": "text", "text": str(refused)}], "isError": True}
    try:
        # THE CLIENT'S DIRECTORY, NOT THE ATLAS: a relative path names the consumer's file. The first draft
        # ran in ROOT, so `route app.py` answered for a file in the atlas the client never meant.
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "atlas.py"), *argv],  # noqa: S603
                              capture_output=True, text=True, timeout=TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": f"thea {name} timed out after {TIMEOUT}s"}], "isError": True}
    text = done.stdout + (f"\n[stderr]\n{done.stderr}" if done.stderr.strip() else "")
    return {"content": [{"type": "text", "text": text.strip() or f"exit {done.returncode}"}],
            "isError": done.returncode != 0}


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
        result = {"protocolVersion": asked if asked in supported else declared,
                  "capabilities": {"tools": {"listChanged": False}},
                  "serverInfo": {"name": "thea", "version": str(atlas().get("version"))},
                  "instructions": "Route before reading: `route` or `gate` a file first, then load only what it "
                                  "names. Every tool is a read-only `thea` command; its exit code is the verdict."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": tools()}
    elif method == "tools/call":
        result = call(str(params.get("name")), params.get("arguments") or {})
    else:
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def serve() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            reply = handle(message)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(serve())
