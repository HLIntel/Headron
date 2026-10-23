#!/usr/bin/env python3
"""Thea as an MCP server: the same commands `thea` answers, offered as tools over stdio.

WHY A ROUTE, NOT A SECOND SYSTEM (3.7.0). The one tool here, `thea {argv}`, runs a `thea` command, listed from the one
parser in commands.py and run as `atlas.py <command>` in a subprocess. So an MCP client, a shell and
a future front end get the same answer to the same question, and nothing here can drift from the CLI
because nothing here re-implements it. Its schema is derived from the parser's arguments.

THE TYPED TOOLS (3.60.0) are the seven questions an agent asks before it edits a file (`port`, `route`,
`gate`, `steps`, `failures`, `successes`, `proof`), each a named tool with a schema read off its verb's
parser (`FEATURED`). They are the same verbs with the arguments renamed to public names, `--json` forced,
paths checked and resolved against the client's directory, and the resolution echoed back. A verb not in
`FEATURED` is not callable by name; the `thea` tool still takes its argv.

THE MCP ROUTE IS READ-ONLY BY CONSTRUCTION. Flags that write (`--write`, `--run`, `--fix`) and flags
that run declared verification (`proof --verify`) never appear in a tool's schema and are refused if
sent; instruments (which include landing and pushing) are not offered at all. A client cannot set them
wrongly because it cannot set them.

Transport: newline-delimited JSON-RPC 2.0 on stdin/stdout (MCP stdio). Each call runs in its own
process with a timeout, so a command's prints never reach the protocol stream and a changed
atlas.yaml is read fresh on every call. That process is forked from this one with the modules already
imported and every cache emptied, not spawned: a spawned call paid the imports each time. Resources are the atlas.yaml sections, read on demand; prompts
are the two questions asked most. Every call result carries `structuredContent.exit`, the verdict, and
`structuredContent.record` when the command was asked for --json and printed one, `structuredContent.text`
otherwise.

  python scripts/thea_mcp.py                 serve on stdio
  python scripts/thea_mcp.py --check         speak the protocol to itself once; the exit code is the verdict
  claude mcp add thea -e THEA_ROOT=<atlas> -- thea-mcp    register an installed copy with Claude Code

Any runtime that speaks MCP over stdio can run it. Two environment variables configure it, and nothing else:
`THEA_ROOT` (the atlas) and `THEA_CLIENT_DIR` (the directory relative paths resolve against).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import json
import os
import selectors
import signal
import subprocess
import sys
import threading
import time
import traceback

import agents
from atlascore import ROOT, atlas
from commands import command_table

# THE ONE WRITE THIS ROUTE MAKES (3.51.0) is outside the tree: a heartbeat in the agent registry, so a
# client that runs only this server is still counted. It fails open: a missed beat never fails a call.
CLIENT: dict[str, str | None] = {"name": None}


def _beat(ended: bool = False) -> None:
    """A heartbeat, or the session's end at stdin EOF. A client that never named itself is not beaten.

    UNNAMED IS A PROBE (3.54.0): 110 of 117 registry records were `mcp-client` in /private/tmp, 108 of
    them under a second old — the in-process `--check` and test spawns, never a client. The protocol
    makes `clientInfo` required, so a real client always names itself and nothing is lost by this.
    """
    if not CLIENT["name"]:
        return
    try:
        (agents.end if ended else agents.beat)(CLIENT["name"], f"mcp-{os.getpid()}", "mcp", os.getcwd())
    except (agents.BeatError, OSError) as exc:
        print(f"thea-mcp: no beat recorded: {exc}", file=sys.stderr)


MUTATING = {"--write", "--run", "--fix", "--shown"}  # the safe route is incapable of these, not flagged against them
READ_ONLY_EXCLUDED_OPTIONS = {"proof": {"--verify": "it runs declared verification; use the CLI, not read-only MCP"}}
# A VERB THAT RUNS ITS OWN ARGV IS NOT READ-ONLY (3.54.x): `slot` executes whatever follows it, so
# `["slot", "touch", "x"]` wrote a file through the "read-only" route. Such a verb is not offered at all.
# `verify` runs declared gates (and may write evidence / field events); keep it on the explicit CLI.
UNOFFERED = {
    "slot": "it runs the rest of its argv as a command",
    "verify": "it runs declared gates; use the CLI, not read-only MCP",
    "init": "it writes agent wiring files and runs declared checks; use the CLI",
}
TIMEOUT = 600
# A CALL'S OUTPUT IS BOUNDED (3.54.x): a command printing without end grew this process's memory and the
# client's reply alike. Past the cap the rest is drained and dropped, and the text says so.
MAX_OUTPUT = 1 << 20
# Hints for a client's UI only — a client must treat them as untrusted, so the guarantee stays the construction.
ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


def offered() -> list[str]:
    """Every CLI verb this route offers: the command table, less the verbs that run their own argv."""
    return [c for c in command_table() if c not in UNOFFERED]


def _arguments(command: str) -> list[argparse.Action]:
    excluded = MUTATING | set(READ_ONLY_EXCLUDED_OPTIONS.get(command, {}))
    return [a for a in command_table()[command]["arguments"] if not (set(a.option_strings) & excluded)]


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


TOOL = "thea"


def tools() -> list[dict]:
    """THE GENERIC TOOL, PLUS THE TYPED SEVEN (3.60.0). A tool per command listed 30-odd schemas on every request,
    and a client that budgets its tool list dropped the server whole (3.54.0). So the list is the one `thea` tool,
    which takes the CLI's own argv and names every verb, and the seven `FEATURED` tools an agent reaches for first."""
    verbs = ", ".join(offered())
    typed = [
        {
            "name": n,
            "description": f"{s['about']} Read-only; the exit code is the verdict.",
            "inputSchema": _featured_schema(n),
            "annotations": ANNOTATIONS,
        }
        for n, s in FEATURED.items()
    ]
    return [
        {
            "name": TOOL,
            "description": f'One read-only thea command as argv, e.g. ["gate", "app.py", "--json"]. Verbs: {verbs}. '
            '["commands", "--json"] lists each with its arguments; the exit code is the verdict.',
            "inputSchema": {
                "type": "object",
                "properties": {
                    "argv": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    "batch": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 8,
                        "items": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    },
                    "parallel": {
                        "type": "boolean",
                        "default": False,
                        "description": "Run a validated read-only batch concurrently; defaults to ordered execution.",
                    },
                },
                "additionalProperties": False,
            },
            "annotations": ANNOTATIONS,
        },
        *typed,
    ]


def _cli_argv(argv: object) -> list[str]:
    """The CLI's argv, admitted only as the typed route would admit it. EXACT OPTIONS ONLY: argparse expands
    a prefix, so `--wri` would reach `--write`; a token is an option this route offers, or a plain value."""
    if not isinstance(argv, list) or not argv or not all(isinstance(t, str) for t in argv):
        raise ValueError("'argv' is a non-empty list of strings, the verb first")
    command, *rest = argv
    if command in UNOFFERED:
        raise ValueError(f"'{command}' refused: {UNOFFERED[command]}, so the read-only route does not offer it")
    if command not in command_table():
        raise ValueError(f"no command '{command}'; [\"commands\"] names every one")
    excluded = READ_ONLY_EXCLUDED_OPTIONS.get(command, {})
    for token in rest:
        if (option := token.split("=", 1)[0]) in excluded:
            raise ValueError(f"'{option}' refused: {excluded[option]}")
    offered = {o for a in _arguments(command) for o in a.option_strings}
    for token in rest:
        if token.startswith("-") and token.split("=", 1)[0] not in offered:
            raise ValueError(f"'{token}' refused: not an option '{command}' offers over MCP — writes are refused here")
    return argv


def _argv(command: str, arguments: dict) -> list[str]:
    if command in UNOFFERED:
        raise ValueError(f"'{command}' refused: {UNOFFERED[command]}, so the read-only route does not offer it")
    known = {a.dest: a for a in _arguments(command)}
    unknown = sorted(set(arguments) - set(known))
    if unknown:
        raise ValueError(f"'{command}' takes no argument(s) {unknown} over MCP — writes are refused on this route")
    argv, tail = [command], []
    for dest, action in known.items():
        if dest not in arguments:
            continue
        value = arguments[dest]
        # ONE VALUE IS ONE WORD (3.50.x): a list for a single-value argument became separate words, so
        # `do {"action": ["check", "--run"]}` ran the file; a leading dash is an option, never a value.
        if isinstance(value, list) and action.nargs in (None, "?"):
            raise ValueError(f"'{dest}' takes one value, not a list")
        if any(str(v).startswith("-") for v in (value if isinstance(value, list) else [value])):
            raise ValueError(f"'{dest}' refused: a value starting with '-' would be read as an option")
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


# THE TYPED TOOLS (3.60.0): one named tool per question an agent asks before it edits, read off the verb's parser,
# never typed twice. `args` maps each public name to the CLI's dest (`--for` reads badly as `for_`); `required`
# and `scope` are the refusals a verb's own parser does not make; `paths` maps each path-like argument to whether
# it must exist (a place or task name is not a path). Every entry's verb offers --json, so the verdict is always data.
FEATURED: dict[str, dict] = {
    "port": {
        "verb": "port",
        "about": "START HERE before editing a file: its route, tier, the gates to run, the lessons that apply, and the next commands.",
        "args": {"target": "target", "runtime": "runtime"},
        "required": ["target"],
        "paths": {"target": False},
    },
    "route": {
        "verb": "route",
        "about": "Which pack, card, manifest and rule resolved a path, and what else decides it.",
        "args": {"path": "path"},
        "required": ["path"],
        "paths": {"path": True},
    },
    "gate": {
        "verb": "gate",
        "about": "The one command a named gate runs for a file, as argv, with its state. It shows the command and does not run it.",
        "args": {"path": "path", "gate": "gate", "change": "change"},
        "required": ["path"],
        "paths": {"path": True},
    },
    "steps": {
        "verb": "steps",
        "about": "The ordered implementation plan for one file, to its return point.",
        "args": {"path": "path", "runtime": "runtime", "change": "change", "tier": "tier"},
        "required": ["path"],
        "paths": {"path": True},
    },
    "failures": {
        "verb": "failures",
        "about": "Mistakes agents made with a file (`for`) or with an error text (`match`), each with the guard that stops it. "
        "The whole ledger is not offered: scope it with `for`, `match` or one shape's `id`.",
        "args": {"id": "id", "for": "for_", "match": "match", "limit": "limit"},
        "required": [],
        "scope": ["id", "for", "match"],
        "paths": {"for": False},
    },
    "successes": {
        "verb": "successes",
        "about": "The moves that replaced recorded failures, for a file (`for`) or one move (`id`), and how each is proved.",
        "args": {"id": "id", "for": "for_", "limit": "limit"},
        "required": [],
        "scope": ["id", "for"],
        "paths": {"for": False},
    },
    "proof": {
        "verb": "proof",
        "about": "Deterministic scope of a change to one file: its change class, planned gates and tools. "
        "Measured verification (`--verify`) runs gates and stays on the CLI.",
        "args": {"path": "path", "task": "task", "change": "change", "modifier": "modifier"},
        "required": ["path"],
        "paths": {"path": True},
    },
}


def _featured_schema(name: str) -> dict:
    """A typed tool's JSON Schema: its verb's arguments under their public names, each description as the parser wrote it."""
    spec = FEATURED[name]
    base = _schema(spec["verb"])["properties"]
    props = {public: base[dest] for public, dest in spec["args"].items() if dest in base}
    return {"type": "object", "properties": props, "required": spec["required"], "additionalProperties": False}


def _featured(name: str, arguments: dict) -> tuple[list[str], dict]:
    """A typed tool's argv and the paths it resolved. Every refusal a value can earn is `_argv`'s, the one place
    that checks a value; this adds only the scope and the path rules a parser does not state."""
    spec = FEATURED[name]
    unknown = sorted(set(arguments) - set(spec["args"]))
    if unknown:
        raise ValueError(f"'{name}' takes no argument(s) {unknown} over MCP — writes are refused on this route")
    if missing := [p for p in spec["required"] if p not in arguments]:
        raise ValueError(f"'{name}' needs {missing}")
    if "scope" in spec and not any(arguments.get(p) for p in spec["scope"]):
        raise ValueError(f"'{name}' needs one of {spec['scope']}: the whole ledger is not offered; scope it")
    argv = _argv(spec["verb"], {spec["args"][public]: value for public, value in arguments.items()})
    argv = argv + ["--json"]  # FORCED (3.60.0): the verdict is always a record, never text a client re-parses
    resolved: dict[str, str] = {}
    for public, must_exist in spec["paths"].items():
        if public not in arguments:
            continue
        raw = str(arguments[public])
        if os.path.exists(raw):
            resolved[public] = os.path.abspath(raw)  # the client's directory, echoed so the answer names its file
        elif must_exist:
            raise ValueError(
                f"no such path '{raw}' under {os.getcwd()}: a path is read against the client's directory. "
                "Pass an absolute path, or set THEA_CLIENT_DIR on the server to the project directory."
            )
    return argv, resolved


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
    kept = dict.fromkeys(chunks, 0)
    deadline = time.monotonic() + TIMEOUT
    with selectors.DefaultSelector() as sel:
        for read in chunks:
            sel.register(read, selectors.EVENT_READ)
        while sel.get_map() and time.monotonic() < deadline:
            for key, _ in sel.select(deadline - time.monotonic()):
                data = os.read(key.fd, 65536)
                if data and kept[key.fd] <= MAX_OUTPUT:  # past the cap: drained, so the child never blocks
                    chunks[key.fd].append(data)
                    kept[key.fd] += len(data)
                elif not data:
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


def _bounded(text: str) -> str:
    """One stream as the client receives it: whole, or its first MAX_OUTPUT characters and a note saying so."""
    if len(text) <= MAX_OUTPUT:
        return text
    return text[:MAX_OUTPUT] + f"\n[thea-mcp: output cut at {MAX_OUTPUT} characters; run it in a shell for the rest]"


def call(name: str, arguments: dict) -> dict:
    """`thea {argv}` and the typed `FEATURED` tools are the listed tools; any other verb is reached through `thea`."""
    arguments = arguments or {}
    if name != TOOL and name not in FEATURED:
        return {"content": [{"type": "text", "text": f"no tool '{name}'; tools/list names every one"}], "isError": True}
    try:
        if name == TOOL and "batch" in arguments:
            if set(arguments) - {"batch", "parallel"}:
                raise ValueError(f"'{TOOL}' takes either 'argv' or 'batch' with optional 'parallel'")
            if not isinstance(arguments.get("parallel", False), bool):
                raise ValueError("'parallel' is a boolean")
            if not isinstance(arguments["batch"], list) or not arguments["batch"]:
                raise ValueError("'batch' is a non-empty list of argv lists")
            if len(arguments["batch"]) > 8:
                raise ValueError("'batch' accepts at most 8 argv lists")
            calls = [_cli_argv(item) for item in arguments["batch"]]
            # Validate every member before any command starts: a mixed batch never partly runs.
            if arguments.get("parallel"):
                # This switch is only available to the read-only MCP route.  Keep map()'s input order
                # so a client can pair result N with argv N even when completion order differs.
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(calls))) as pool:
                    replies = list(pool.map(lambda item: call(TOOL, {"argv": item}), calls))
            else:
                replies = [call(TOOL, {"argv": item}) for item in calls]
            return {
                "content": [{"type": "text", "text": "\n\n".join(reply["content"][0]["text"] for reply in replies)}],
                "structuredContent": {"results": [reply.get("structuredContent") for reply in replies]},
                "isError": any(reply.get("isError") for reply in replies),
            }
        resolved: dict[str, str] = {}
        if name == TOOL:
            argv = _cli_argv(arguments.get("argv"))
            if set(arguments) != {"argv"}:
                raise ValueError(f"'{TOOL}' takes only 'argv' or 'batch'")
        else:
            argv, resolved = _featured(name, arguments)
    except ValueError as refused:
        return {"content": [{"type": "text", "text": str(refused)}], "isError": True}
    name = argv[0]
    try:
        # THE CLIENT'S DIRECTORY, NOT THE ATLAS: a relative path names the consumer's file. The first draft
        # ran in ROOT, so `route app.py` answered for a file in the atlas the client never meant.
        done = (
            _forked(argv)
            # fork() from a ThreadPoolExecutor worker can inherit a locked interpreter state.
            # Batch workers take the portable subprocess path; main-thread calls retain the warm fast path.
            if _forkable() and threading.current_thread() is threading.main_thread()
            else subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "atlas.py"), *argv],
                env={**os.environ, "THEA_READ_ONLY": "1"},  # noqa: S603
                stdin=subprocess.DEVNULL,  # the client's JSON-RPC stream is ours: a `--hook` child read it and hung the session
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                check=False,
            )
        )
    except subprocess.TimeoutExpired:
        return {"content": [{"type": "text", "text": f"thea {name} timed out after {TIMEOUT}s"}], "isError": True}
    stdout, stderr = _bounded(done.stdout), _bounded(done.stderr)
    text = stdout + (f"\n[stderr]\n{stderr}" if stderr.strip() else "")
    # THE VERDICT TRAVELS AS DATA: the text carried the exit code only when stdout was empty, so a client
    # read "a verdict 1 with findings" and "a crash" as the same isError. The record rides beside it.
    try:
        record = json.loads(stdout) if "--json" in argv else None
    except ValueError:
        record = None
    shown = text.strip() or f"exit {done.returncode}"
    # THE TEXT RIDES IN BOTH: a client that renders structuredContent in place of content (Claude Code
    # does) showed a text-mode `route` as {"exit":0} and nothing else — the answer reached no agent.
    return {
        "content": [{"type": "text", "text": shown}],
        "structuredContent": {
            "exit": done.returncode,
            **({"record": record} if record is not None else {"text": shown}),
            **({"resolved": resolved} if resolved else {}),
        },
        "isError": done.returncode != 0,
    }


def negotiate(asked: object) -> str:
    """The revision to answer: the client's if supported, else the declared one. Both MCP routes call this."""
    declared = str((atlas().get("external_versions") or {}).get("mcp_specification") or "")
    supported = {str(v) for k, v in (atlas().get("external_versions") or {}).items() if k.startswith("mcp_")}
    return asked if isinstance(asked, str) and asked in supported else declared


def handle(message: dict) -> dict | None:
    """One JSON-RPC message in, one response out (None for a notification)."""
    method, ident = message.get("method"), message.get("id")
    if ident is None:
        return None
    params = message.get("params") or {}
    if method == "initialize":
        CLIENT["name"] = str((params.get("clientInfo") or {}).get("name") or "") or None
        # NEVER ECHO AN UNKNOWN VERSION (3.9.2). The spec: answer the client's version only if the server
        # supports it, else the latest it does. Echoing claimed support for any revision a client named,
        # including one not yet written. Supported = the declared spec plus the published revisions that
        # keep initialize, tools/list and tools/call unchanged — the only methods this route uses.
        result = {
            "protocolVersion": negotiate(params.get("protocolVersion")),
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {"name": "thea", "version": str(atlas().get("version"))},
            "instructions": "Start with `port` on the file you will edit: its route, gates, lessons and next commands. "
            "`failures` and `successes` take a file or an error text, never the whole ledger. The `thea` tool takes "
            "any other read-only command's argv; the exit code is the verdict.",
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": tools()}
    elif method == "tools/call":
        _beat()
        result = call(str(params.get("name")), params.get("arguments") or {})
    elif method in ("resources/list", "resources/read", "prompts/list", "prompts/get"):
        try:
            result = CONTEXT[method](params)
        except KeyError as missing:
            return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32602, "message": f"unknown: {missing}"}}
        except ValueError as bad:  # a required prompt argument missing: a reply the client can act on, not a crash
            return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32602, "message": str(bad)}}
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
    required = PROMPTS[name][1]
    if not args.get(required):  # NO PLACEHOLDER: a missing `path` once rendered as the literal `<path>` in the prompt
        raise ValueError(f"prompt '{name}' needs argument '{required}'")
    text = (
        f"Run `thea steps {args['path']}` (or the steps tool) and follow each step in order; "
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
        ("tools/list", {}, lambda r: [t["name"] for t in r["result"]["tools"]] == [TOOL, *FEATURED]),
        (
            "tools/call",
            {"name": TOOL, "arguments": {"argv": ["route", "x.py", "--json"]}},
            lambda r: r["result"]["structuredContent"]["exit"] == 0 and "record" in r["result"]["structuredContent"],
        ),
        ("tools/call", {"name": TOOL, "arguments": {"argv": ["index", "--wri"]}}, lambda r: r["result"]["isError"]),
        ("tools/call", {"name": TOOL, "arguments": {"argv": ["slot", "true"]}}, lambda r: r["result"]["isError"]),
        (
            "tools/call",
            {"name": "route", "arguments": {"path": os.path.abspath(__file__)}},  # a probe runs in any cwd
            lambda r: (
                r["result"]["structuredContent"]["exit"] == 0
                and r["result"]["structuredContent"]["record"]["command"] == "route"
                and r["result"]["structuredContent"]["resolved"]["path"].endswith("scripts/thea_mcp.py")
            ),
        ),
        ("tools/call", {"name": "index", "arguments": {"write": True}}, lambda r: r["result"]["isError"]),
        (
            "tools/call",
            {"name": "gate", "arguments": {"path": ["x.py", "--run"]}},
            lambda r: "one value" in r["result"]["content"][0]["text"],
        ),
        (
            "tools/call",
            {"name": "port", "arguments": {"target": "--run"}},
            lambda r: "refused" in r["result"]["content"][0]["text"],
        ),
        (
            "tools/call",
            {"name": "failures", "arguments": {}},
            lambda r: "whole ledger" in r["result"]["content"][0]["text"],
        ),
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
    """The stdio loop, shared: the edit route passes its own handler rather than copying this.

    THE CLIENT'S DIRECTORY IS SET ONCE, HERE (3.60.0). Runtimes start a stdio server wherever they like — often
    `/` or `$HOME` — so a relative path would resolve against the wrong tree. `THEA_CLIENT_DIR` moves the
    process there before the first message; the typed tools and the `thea` tool's child both inherit it, so the
    two routes agree. Unset, the server keeps the directory it was started in.
    """
    handler = handler or handle
    base = os.environ.get("THEA_CLIENT_DIR")
    if base:
        try:
            os.chdir(base)
        except OSError as exc:
            print(f"thea-mcp: THEA_CLIENT_DIR '{base}' is not a usable directory: {exc}", file=sys.stderr)
            return 2
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
    if handler is handle:
        _beat(ended=True)  # stdin closed: the client disconnected cleanly, so the record says so
    return 0


if __name__ == "__main__":
    raise SystemExit(self_check() if "--check" in sys.argv[1:] else serve())
