#!/usr/bin/env python3
"""Which agent sessions are live on this machine: the registry a local dashboard counts.

WHY (3.51.0). Plans price the dashboard by agents running at once, and nothing recorded which agents
were running. A key handed to each agent was refused as the design: a key in a model's context reaches
its transcripts and logs, and an agent that names itself proves nothing. Every session already passes
through Thea's hooks and MCP server, so those calls ARE the heartbeat, and linking an agent needs no
secret at all.

ONE FILE PER SESSION, written whole and renamed into place, so concurrent agents never share a lock
or read a half-written record. A record holds the agent's name, its session id, the directory it works
in and when it was seen; never a prompt, a command or a file's content.

ONE AGENT, ONE COUNT. A hooked agent that also runs the MCP server reports through both. An MCP record
in a directory a live hook record already covers is not counted again; an agent with only the MCP
server (no hooks) is counted by that record alone.

THE COUNT NEVER GATES ENFORCEMENT. The open-source core enforces every agent; this registry only tells
a dashboard how many there are.

  thea agents                       live sessions, newest first
  thea agents --json                the same, as a record
  thea agents --hook claude-code    read one agent hook's JSON on stdin and record a beat
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# THE PRIVACY PROMISE, ENFORCED (3.51.0): everything Thea records stays on the machine that ran it. These
# are the only modules that may open a network connection, each one run only by its own command with the
# user's own keys or remote: model benchmarks, the repository audit, and the retry wrapper they share;
# and the launcher, which downloads only its own public release with no checkout (THEA_NO_FETCH=1 stops it).
# A new import of a network module anywhere else fails the planted suite until it is declared here.
NETWORK_MODULES = ("abtest.py", "atlas_cli.py", "ghaudit.py", "providers.py", "resilience.py")
NETWORK_IMPORTS = (
    "urllib.request",
    "http.client",
    "socket",
    "ssl",
    "requests",
    "httpx",
    "aiohttp",
    "urllib3",
    "ftplib",
    "smtplib",
)

LIVE_SECONDS = 600  # a session unseen this long is idle, not running
KEEP_SECONDS = 7 * 86400  # a record older than this is removed when the registry is listed
SOURCES = ("hook", "mcp")


class BeatError(ValueError):
    """A beat this registry refuses to record rather than invent a field for."""


def registry() -> Path:
    """The session directory; THEA_HOME moves it, so a test never touches the real one."""
    return Path(os.environ.get("THEA_HOME") or Path.home() / ".thea") / "sessions"


def beat(agent: object, session: object, source: str, cwd: object = None, now: float | None = None) -> Path:
    """Record that one agent session was seen now. Refuses an empty agent or session id."""
    if source not in SOURCES:
        raise BeatError(f"source must be one of {SOURCES}; got {source!r}")
    for name, value in (("agent", agent), ("session", session)):
        if not isinstance(value, str) or not value.strip():
            raise BeatError(f"{name} must be a non-empty string; got {value!r}")
    now = time.time() if now is None else now
    folder = registry()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (hashlib.sha256(f"{source}\0{agent}\0{session}".encode()).hexdigest()[:24] + ".json")
    record = {
        "agent": agent,
        "session": session,
        "source": source,
        "cwd": cwd if isinstance(cwd, str) and cwd else None,
        "first_seen": _first_seen(path, now),
        "last_seen": now,
    }
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(record), encoding="utf-8")
    os.replace(tmp, path)
    return path


def _first_seen(path: Path, now: float) -> float:
    """The earlier record's first sighting; an unreadable one restarts the session's clock."""
    try:
        first = json.loads(path.read_text(encoding="utf-8")).get("first_seen")
    except (OSError, ValueError, AttributeError):
        return now
    return first if isinstance(first, (int, float)) else now


def records(now: float) -> tuple[list[dict], list[str]]:
    """(readable records, unreadable file names); a record past KEEP_SECONDS is removed."""
    rows, bad = [], []
    for path in sorted(registry().glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            bad.append(path.name)
            continue
        if (
            not isinstance(row, dict)
            or row.get("source") not in SOURCES
            or not isinstance(row.get("last_seen"), (int, float))
        ):
            bad.append(path.name)
        elif now - row["last_seen"] > KEEP_SECONDS:
            path.unlink(missing_ok=True)
        else:
            rows.append(row)
    return rows, bad


def live(rows: list[dict], now: float) -> list[dict]:
    """Sessions seen within LIVE_SECONDS, one per agent: an MCP record under a live hook's cwd is dropped."""
    fresh = [r for r in rows if now - r["last_seen"] <= LIVE_SECONDS]
    hooked = {r.get("cwd") for r in fresh if r["source"] == "hook" and r.get("cwd")}
    kept = [r for r in fresh if r["source"] == "hook" or r.get("cwd") not in hooked]
    return sorted(kept, key=lambda r: -r["last_seen"])


def network_modules(root: Path) -> list[str]:
    """Every .py under root that imports a network module, by path relative to root; a parse error is listed too."""
    import ast

    from atlascore import files_under, parsed_python, walked

    found = []
    for path in (p for p in files_under(root) if p.suffix == ".py"):
        try:
            tree = parsed_python(path.read_text(encoding="utf-8"), str(path))
        except (OSError, ValueError):
            tree = None
        if tree is None:
            found.append(f"{path.relative_to(root)} (unparsed)")
            continue
        names = set()
        for node in walked(tree):
            if isinstance(node, ast.Import):
                names |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        if any(n == m or n.startswith(m + ".") for n in names for m in NETWORK_IMPORTS):
            found.append(str(path.relative_to(root)))
    return found


def from_hook(agent: str, stream) -> Path:
    """One agent hook's stdin payload -> one beat. Its `session_id` is required, `cwd` optional."""
    try:
        payload = json.load(stream)
    except ValueError:
        raise BeatError("hook input is not JSON") from None
    if not isinstance(payload, dict):
        raise BeatError("hook input is not a JSON object")
    return beat(agent, payload.get("session_id"), "hook", payload.get("cwd"))


def _print(on: list[dict], bad: list[str], now: float) -> None:
    for row in on:
        where = row.get("cwd") or "-"
        print(
            f"  {row['agent']:<14} {row['source']:<4}  {str(row['session'])[:12]:<12}  "
            f"seen {int(now - row['last_seen'])}s ago  {where}"
        )
    for name in bad:
        print(f"  UNREADABLE  {registry() / name}")
    print(f"{len(on)} live agent session(s), seen within {LIVE_SECONDS}s; registry {registry()}")
    print("SCOPE: counts sessions whose hooks or MCP calls reached this machine; an agent with neither is not seen")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thea agents", description="live agent sessions on this machine")
    parser.add_argument("--json", action="store_true", help="emit the live sessions as a record")
    parser.add_argument("--hook", metavar="AGENT", help="record a beat from an agent hook's JSON on stdin")
    args = parser.parse_args(argv)
    if args.hook:
        try:
            from_hook(args.hook, sys.stdin)
        except (BeatError, OSError) as exc:
            # 1, NOT 2: an agent runtime may read exit 2 from a hook as "block this tool call", and a
            # missed heartbeat must never stop the agent's work.
            print(f"agents: no beat recorded: {exc}", file=sys.stderr)
            return 1
        return 0
    now = time.time()
    rows, bad = records(now)
    on = live(rows, now)
    if args.json:
        print(
            json.dumps(
                {"schema": 1, "command": "agents", "live_seconds": LIVE_SECONDS, "live": on, "unreadable": bad},
                indent=2,
            )
        )
    else:
        _print(on, bad, now)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
