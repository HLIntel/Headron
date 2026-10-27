#!/usr/bin/env python3
"""Which agent sessions are live on this machine: the registry Headron Desktop counts.

WHY (3.51.0). Plans price Headron Desktop by agents running at once, and nothing recorded which agents
were running. A key handed to each agent was refused as the design: a key in a model's context reaches
its transcripts and logs, and an agent that names itself proves nothing. Every session already passes
through Headron's hooks and MCP server, so those calls ARE the heartbeat, and linking an agent needs no
secret at all.

ONE FILE PER SESSION, written whole and renamed into place, so concurrent agents never share a lock
or read a half-written record. A record holds the agent's name, its session id, the directory it works
in and when it was seen; never a prompt, a command or a file's content.

ONE AGENT, ONE COUNT. A hooked agent that also runs the MCP server reports through both. An MCP record
in a directory a live hook record already covers is not counted again; an agent with only the MCP
server (no hooks) is counted by that record alone.

THE COUNT NEVER GATES ENFORCEMENT. The open-source core enforces every agent; this registry only tells
Headron Desktop how many there are.

  headron agents                       live sessions, newest first
  headron agents --json                the same, as a record
  headron agents --hook claude-code    read one agent hook's JSON on stdin and record a beat
  headron agents --hook claude-code --end   the same, as the session's end

A SESSION HAS A LIFECYCLE (3.54.0): live (seen within LIVE_SECONDS), idle (seen, then silent), ended
(its client said so: stdin closed, a SessionEnd hook). Before it, a closed session stayed "live" for
LIVE_SECONDS after its last beat, so the count ran high by every agent closed in the last ten minutes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# THE PRIVACY PROMISE, ENFORCED (3.51.0): everything Headron records stays on the machine that ran it. These
# are the only modules that may open a network connection, each one run only by its own command with the
# user's own keys or remote: model benchmarks, the repository audit, and the retry wrapper they share;
# the launcher, which downloads only its own public release with no checkout (HEADRON_NO_FETCH=1 stops it);
# and the GitHub App service, which talks only to the GitHub API with its host's App keys (3.56.0).
# A new import of a network module anywhere else fails the planted suite until it is declared here.
NETWORK_MODULES = ("abtest.py", "atlas_cli.py", "ghaudit.py", "githubapp.py", "providers.py", "resilience.py")
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

# CONTEXT LIFECYCLE (3.60.0). Track token consumption per session to prevent context degradation.
# When a session approaches its context window limit, trigger compaction before quality degrades.
CONTEXT_COMPACT_THRESHOLD = 0.7  # trigger compaction at 70% of context window
DEFAULT_CONTEXT_WINDOW = 128_000  # default context window in tokens (adjustable per agent)


class BeatError(ValueError):
    """A beat this registry refuses to record rather than invent a field for."""


def registry() -> Path:
    """The session directory; HEADRON_HOME moves it, so a test never touches the real one."""
    from atlascore import headron_home  # noqa: PLC0415

    return headron_home() / "sessions"


def beat(agent: object, session: object, source: str, cwd: object = None, now: float | None = None) -> Path:
    """Record that one agent session was seen now. Refuses an empty agent or session id."""
    return _record(agent, session, source, cwd, now, None)


def end(agent: object, session: object, source: str, cwd: object = None, now: float | None = None) -> Path:
    """Record that one agent session ended now: it leaves the live count at once, not LIVE_SECONDS later."""
    stamp = time.time() if now is None else now
    path = _record(agent, session, source, cwd, stamp, stamp)
    field("session_ended", {"agent": agent, "source": source})
    return path


def _record(
    agent: object, session: object, source: str, cwd: object, now: float | None, ended_at: float | None
) -> Path:
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
        "ended_at": ended_at,
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
    for orphan in registry().glob("*.tmp"):  # a writer killed between write and replace leaves one behind
        if now - orphan.stat().st_mtime > KEEP_SECONDS:
            orphan.unlink(missing_ok=True)
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


def status(row: dict, now: float) -> str:
    """ended, live or idle: an end recorded wins over any age."""
    if isinstance(row.get("ended_at"), (int, float)):
        return "ended"
    return "live" if now - row["last_seen"] <= LIVE_SECONDS else "idle"


def live(rows: list[dict], now: float) -> list[dict]:
    """Live sessions, one per agent: an MCP record under a live hook's cwd is dropped; an ended one never counts."""
    fresh = [r for r in rows if status(r, now) == "live"]
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


def field_stream(now: float | None = None) -> Path:
    """This month's field ledger: one hash-chained stream per month under HEADRON_HOME, capped in bytes."""
    month = time.strftime("%Y-%m", time.gmtime(time.time() if now is None else now))
    return registry().parent / "field" / f"{month}.jsonl"


def field(kind: str, body: dict) -> dict | None:
    """Seal one field event (a refusal, a verify, a lesson shown, a land, an end) onto the field ledger.

    ONE LEDGER, NOT TWO (3.54.0): this is the audit chain's `append`, pointed at HEADRON_HOME, so the byte
    cap, the declared kinds and tamper evidence come with it. FAILS OPEN: a ledger that cannot be written
    never blocks the command that reported to it; the miss is printed, never raised.
    """
    import agentaudit
    from runtime import resolve  # noqa: PLC0415

    agent = resolve()
    ids = {
        "session": os.environ.get("CLAUDE_CODE_SESSION_ID"),
        "task": os.environ.get("HEADRON_TASK_ID"),
        "agent": agent["agent"],
        "runtime": agent["runtime"],
    }
    ids = {key: value for key, value in ids.items() if value}
    try:
        stream = field_stream()
        if not stream.exists():  # a new month: the oldest beyond FIELD_MONTHS are compressed aside, never deleted
            archive_months(stream.parent)
        return agentaudit.append(stream, kind, {"ts": round(time.time(), 3), **ids, **body})
    except (OSError, ValueError) as exc:
        print(f"agents: no field event recorded: {exc}", file=sys.stderr)
        return None


def record_test_run(groups_ran: int, groups_total: int, secs: float, passed: bool) -> dict | None:
    """Record a test run summary for session-to-session benefits: timing, coverage, and pass/fail.

    This lets a later session know how long tests typically take and whether the last run passed,
    so it can make better decisions about which gates to run first.
    """
    return field(
        "field_test_run",
        {"groups_ran": groups_ran, "groups_total": groups_total, "secs": round(secs, 1), "passed": passed},
    )


# Context lifecycle management: track token consumption per session to prevent degradation


def context_path() -> Path:
    """The context tracking directory under HEADRON_HOME."""
    ctx_dir = registry().parent / "context"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    return ctx_dir


def record_token_usage(session_id: str, tokens_used: int, context_window: int | None = None) -> dict | None:
    """Record token consumption for a session to enable context lifecycle management.

    When a session approaches its context window limit (CONTEXT_COMPACT_THRESHOLD),
    the system can trigger compaction before quality degrades.
    """
    if not isinstance(session_id, str) or not session_id.strip():
        return None
    context_window = context_window or DEFAULT_CONTEXT_WINDOW
    usage_ratio = tokens_used / context_window if context_window > 0 else 0
    status = {
        "session_id": session_id,
        "tokens_used": tokens_used,
        "context_window": context_window,
        "usage_ratio": round(usage_ratio, 3),
        "should_compact": usage_ratio >= CONTEXT_COMPACT_THRESHOLD,
        "ts": round(time.time(), 3),
    }
    ctx_file = context_path() / f"{session_id}.json"
    ctx_file.write_text(json.dumps(status, indent=1), encoding="utf-8")
    if status["should_compact"]:
        field(
            "field_context_compact",
            {"session": session_id, "usage_ratio": status["usage_ratio"], "tokens_used": tokens_used},
        )
    return status


def should_compact(session_id: str) -> bool:
    """Check if a session should compact its context based on token usage."""
    ctx_file = context_path() / f"{session_id}.json"
    if not ctx_file.exists():
        return False
    try:
        status = json.loads(ctx_file.read_text(encoding="utf-8"))
        return status.get("should_compact", False)
    except (json.JSONDecodeError, OSError):
        return False


def compact_context(session_id: str) -> dict | None:
    """Mark a session's context as compacted, resetting the token usage counter.

    Called after the agent compacts its context (summarizes history, removes stale information).
    """
    ctx_file = context_path() / f"{session_id}.json"
    if not ctx_file.exists():
        return None
    try:
        status = json.loads(ctx_file.read_text(encoding="utf-8"))
        compacted_at = round(time.time(), 3)
        status["compacted_at"] = compacted_at
        status["compaction_count"] = status.get("compaction_count", 0) + 1
        status["should_compact"] = False
        status["tokens_used"] = max(1, status.get("tokens_used", 0) // 2)
        status["usage_ratio"] = round(status["tokens_used"] / status.get("context_window", DEFAULT_CONTEXT_WINDOW), 3)
        status["ts"] = compacted_at
        ctx_file.write_text(json.dumps(status, indent=1), encoding="utf-8")
        field("field_context_compacted", {"session": session_id, "compaction_count": status["compaction_count"]})
        return status
    except (json.JSONDecodeError, OSError):
        return None


def context_summary(session_id: str | None = None) -> dict:
    """Get context usage summary for a session or all sessions."""
    if session_id:
        ctx_file = context_path() / f"{session_id}.json"
        if not ctx_file.exists():
            return {"session_id": session_id, "tokens_used": 0, "context_window": DEFAULT_CONTEXT_WINDOW}
        try:
            return json.loads(ctx_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"session_id": session_id, "tokens_used": 0, "context_window": DEFAULT_CONTEXT_WINDOW}
    else:
        summaries = []
        for ctx_file in context_path().glob("*.json"):
            try:
                summaries.append(json.loads(ctx_file.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        total_tokens = sum(s.get("tokens_used", 0) for s in summaries)
        should_compact_count = sum(1 for s in summaries if s.get("should_compact"))
        return {
            "sessions_tracked": len(summaries),
            "total_tokens": total_tokens,
            "sessions_needing_compact": should_compact_count,
        }


def cleanup_old_context(max_age_seconds: int = 86400 * 7) -> int:
    """Remove context records older than max_age_seconds (bounded storage)."""
    ctx_dir = context_path()
    now = time.time()
    cleaned = 0
    for ctx_file in ctx_dir.glob("*.json"):
        try:
            status = json.loads(ctx_file.read_text(encoding="utf-8"))
            ts = status.get("ts", 0)
            if now - ts > max_age_seconds:
                ctx_file.unlink()
                cleaned += 1
        except (json.JSONDecodeError, OSError):
            continue
    return cleaned


# Structured handoff: one file, overwritten each time, so the next session reads the latest state.
# Bounded: the handoff file is small (task, last action, pending gates) and replaced, not appended.
HANDOFF_FILE = "handoff.json"
HANDOFF_SCHEMA = 1


def handoff_path() -> Path:
    """The handoff file: ~/.headron/handoff.json, overwritten atomically."""
    return registry().parent / HANDOFF_FILE


def handoff(
    task: str,
    last_action: str,
    pending_gates: list[str] | None = None,
    cwd: str | None = None,
    agent: str | None = None,
    session: str | None = None,
) -> Path:
    """Write a structured handoff brief so the next session can pick up where this one left off.

    This is the missing link: currently, session-to-session transfer is purely passive (state files).
    A handoff captures: what the task was, what was last done, what gates still need to run,
    and where the work was happening. The next session reads this via `read_handoff()`.

    ARGUMENTS:
        task: one-sentence description of the current task
        last_action: what was just completed (e.g., "fixed CI install check", "added bounded storage")
        pending_gates: list of gate IDs that still need to run, or None if all done
        cwd: working directory of the task
        agent: agent name (auto-detected if not provided)
        session: session ID (auto-detected if not provided)

    RETURNS:
        Path to the handoff file written.
    """
    from runtime import resolve  # noqa: PLC0415

    if not isinstance(task, str) or not task.strip():
        raise BeatError("handoff task must be a non-empty string")
    if not isinstance(last_action, str) or not last_action.strip():
        raise BeatError("handoff last_action must be a non-empty string")

    agt = resolve() if agent is None else {"agent": agent}
    brief = {
        "schema": HANDOFF_SCHEMA,
        "ts": round(time.time(), 3),
        "agent": agt.get("agent", ""),
        "session": session or os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
        "task": task.strip()[:500],  # cap task length
        "last_action": last_action.strip()[:500],  # cap action length
        "pending_gates": pending_gates or [],
        "cwd": cwd if isinstance(cwd, str) and cwd else None,
    }
    path = handoff_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(brief, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    # Also record to the field ledger for cross-session audit
    field("field_handoff", {"task": brief["task"][:100], "pending_gates": len(brief["pending_gates"])})
    return path


def read_handoff() -> dict | None:
    """Read the last handoff brief, or None if there is none.

    Returns the handoff dict with schema, task, last_action, pending_gates, cwd, agent, session.
    A handoff older than KEEP_SECONDS is stale; it is returned but marked stale.
    """
    path = handoff_path()
    if not path.exists():
        return None
    try:
        brief = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(brief, dict) or brief.get("schema") != HANDOFF_SCHEMA:
        return None
    now = time.time()
    age = now - brief.get("ts", 0)
    if age > KEEP_SECONDS:
        brief["stale"] = True
        brief["age_seconds"] = round(age, 1)
    return brief


def gate_answer(record: dict) -> int:
    """`headron gate`'s exit: 0 answered, 2 not, and a refusal is sealed onto the field ledger as it happens.

    The ledger row was a manual step; here the refusal writes it, carrying the gate, the route and the state,
    never the path. FAILS OPEN like every field write."""
    if record["state"] in ("runnable", "absent"):
        return 0
    field("field_gate_refused", {"gate": record["gate"], "route": record["route"], "state": record["state"]})
    return 2


FIELD_MONTHS = 12  # each month is byte-capped; this caps how many stay plain, so the ledger has a total bound


def failures_shown(keys: list[str], route: str | None, ledger: dict) -> int:
    """`headron failures --shown ID --route R` — a hook that printed lessons seals what it showed (3.54.0).

    The edit hook read the ledger before an edit and nothing recorded it, so `agents --field` said
    lessons_shown 0 while agents read lessons on every first edit. Refuses the whole call on an unknown
    id rather than sealing a shape the ledger does not have."""
    unknown = [key for key in keys if key not in ledger]
    if unknown:
        print(f"refused: not in atlas.yaml/agent_failure_modes: {', '.join(unknown)}", file=sys.stderr)
        return 2
    sealed = field("field_lesson", {"route": route, "failures": keys})
    print(f"{'sealed' if sealed else 'NOT sealed'}: field_lesson {len(keys)} shape(s)")
    return 0 if sealed else 1


def archive_months(folder: Path) -> list[Path]:
    """gzip every month but the newest FIELD_MONTHS into folder/archive/; returns what moved."""
    import gzip  # noqa: PLC0415

    moved = []
    for month in sorted(folder.glob("*.jsonl"))[:-FIELD_MONTHS]:
        target = folder / "archive" / f"{month.name}.gz"
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(gzip.compress(month.read_bytes()))
        if gzip.decompress(target.read_bytes()) == month.read_bytes():  # read back before the original goes
            month.unlink()
            moved.append(target)
    return moved


def field_summary(streams: list[Path]) -> dict:
    """The field ledger as aggregates only: counts and rates, never a path, a command or a session id.

    THE JOINS ARE PER SESSION. A refusal whose shape already fired in the same session is a RE-FIRE (the
    reason did not land); a session whose verify failed and later passed RECOVERED. An event with no session
    id is counted but joins nothing, and the uncounted share is printed, never folded in.
    """
    import agentaudit

    events = [e for path in streams for e in agentaudit.read_events(path)]
    by = {
        k: [e["body"] for e in events if e.get("event") == k]
        for k in ("field_refused", "field_verify", "field_lesson", "field_landed", "session_ended")
    }
    seen, refires = set(), 0
    for body in by["field_refused"]:
        key = (body.get("session"), body.get("shape"))
        refires += bool(body.get("session")) and key in seen
        seen.add(key)
    runs: dict[str, list[int]] = {}
    for body in by["field_verify"]:
        if body.get("session"):
            runs.setdefault(body["session"], []).append(body.get("exit"))
    failed = [codes for codes in runs.values() if 1 in codes]
    recovered = sum(0 in codes[codes.index(1) :] for codes in failed)
    return {
        "events": len(events),
        "broken_chains": sum(bool(agentaudit.verify(path)) for path in streams),
        "refusals": len(by["field_refused"]),
        "refusal_shapes": len({b.get("shape") for b in by["field_refused"]}),
        "refires": refires,
        "refusals_without_session": sum(not b.get("session") for b in by["field_refused"]),
        "verify_runs": len(by["field_verify"]),
        "verify_pass": sum(b.get("exit") == 0 for b in by["field_verify"]),
        "verify_fail": sum(b.get("exit") == 1 for b in by["field_verify"]),
        "sessions_failed": len(failed),
        "sessions_recovered": recovered,
        "lessons_shown": sum(len(b.get("failures") or []) for b in by["field_lesson"]),
        "lesson_shapes": len({f for b in by["field_lesson"] for f in b.get("failures") or []}),
        "lands": len(by["field_landed"]),
        "lands_armed": sum(bool(b.get("armed")) for b in by["field_landed"]),
        "sessions_ended": len(by["session_ended"]),
    }


def from_hook(agent: str, stream, ended: bool = False) -> Path:
    """One agent hook's stdin payload -> one beat (or the end). Its `session_id` is required, `cwd` optional."""
    try:
        payload = json.load(stream)
    except ValueError:
        raise BeatError("hook input is not JSON") from None
    if not isinstance(payload, dict):
        raise BeatError("hook input is not a JSON object")
    return (end if ended else beat)(agent, payload.get("session_id"), "hook", payload.get("cwd"))


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


def _field_report(record: bool) -> int:
    """Print the field aggregates; with record, write them as the README's evidence. Exit 2 on no ledger."""
    from atlascore import ROOT, atlas

    streams = sorted((registry().parent / "field").glob("*.jsonl"))
    if not streams:
        print(f"field: NOT RUN — no ledger under {registry().parent / 'field'}")
        return 2
    archived = len(list((registry().parent / "field" / "archive").glob("*.gz")))
    summary = field_summary(streams) | {
        "months": len(streams),
        "archived_months": archived,  # coverage: compressed months are counted, never read here
        "measured_at": str(atlas().get("version")),
    }
    print(json.dumps(summary, indent=2))
    if record:
        (ROOT / "benchmarks" / "field-latest.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 1 if summary["broken_chains"] else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="headron agents", description="live agent sessions on this machine")
    parser.add_argument("--json", action="store_true", help="emit the live sessions as a record")
    parser.add_argument("--hook", metavar="AGENT", help="record a beat from an agent hook's JSON on stdin")
    parser.add_argument("--end", action="store_true", help="with --hook: record the session's end, not a beat")
    parser.add_argument(
        "--field", action="store_true", help="aggregate the field ledger: refusals, re-fires, verifies, lessons, lands"
    )
    parser.add_argument("--record", action="store_true", help="with --field: write benchmarks/field-latest.json")
    parser.add_argument("--read-handoff", action="store_true", help="print the last handoff brief as JSON")
    parser.add_argument("--handoff", metavar="TASK", help="write a handoff brief: TASK describes the current work")
    parser.add_argument("--handoff-action", default="", help="with --handoff: what was last completed")
    parser.add_argument("--handoff-gates", default="", help="with --handoff: comma-separated pending gate IDs")
    parser.add_argument(
        "--context-status",
        metavar="SESSION",
        nargs="?",
        const="all",
        help="show context usage for a session or all sessions",
    )
    parser.add_argument("--context-compact", metavar="SESSION", help="compact a session's context")
    parser.add_argument("--context-tokens", type=int, help="record token usage (with --context-session)")
    parser.add_argument("--context-session", help="session id for context commands")
    parser.add_argument("--context-cleanup", action="store_true", help="clean up old context records")
    args = parser.parse_args(argv)
    if args.context_cleanup:
        cleaned = cleanup_old_context()
        print(f"cleaned {cleaned} old context records")
        return 0
    if args.context_status:
        summary = context_summary() if args.context_status == "all" else context_summary(args.context_status)
        print(json.dumps(summary, indent=2))
        return 0
    if args.context_compact:
        if args.context_tokens is not None:
            record_token_usage(args.context_compact, args.context_tokens)
        status = compact_context(args.context_compact)
        if status is None:
            print(f"no context record for session {args.context_compact!r}")
            return 2
        print(json.dumps(status, indent=2))
        return 0
    if args.read_handoff:
        brief = read_handoff()
        if brief is None:
            print("no handoff found")
            return 2
        print(json.dumps(brief, indent=2))
        return 0
    if args.handoff:
        pending = [g.strip() for g in args.handoff_gates.split(",") if g.strip()] if args.handoff_gates else []
        action = args.handoff_action or "session ended"
        try:
            handoff(args.handoff, action, pending if pending else None, cwd=os.getcwd())
        except (BeatError, OSError) as exc:
            print(f"agents: handoff not written: {exc}", file=sys.stderr)
            return 1
        print(f"handoff written: {handoff_path()}")
        return 0
    if args.field:
        return _field_report(args.record)
    if args.hook:
        try:
            from_hook(args.hook, sys.stdin, args.end)
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
