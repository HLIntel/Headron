#!/usr/bin/env python3
"""The audit stream: a hash chain, not a log.

WHY A CHAIN (2.9.0). The structured outcome record this repository already described could be
written by the agent it describes. A log its own subject can append to can also be edited, and an
edited log is indistinguishable from an honest one — so the record proved nothing it was being
read to prove. Each event here carries the hash of the one before it, so removing or editing an
event breaks every hash after it and `verify` names the first break by sequence number.

WHAT IT DOES NOT PROVE, stated because the chain is exactly the kind of instrument that gets read
as proving more: a chain covers the events it CONTAINS. It says nothing about an action that was
never appended. That gap is closed by the runner being the only caller that executes anything,
and by the host — an agent that can run commands outside the runner is outside this instrument.

REDACTION HAS A FLOOR. Arguments and output are recorded as a hash and a byte count, never echoed,
so a secret in an argument does not enter the stream. The event kind, the exit code, the paths and
the sequence ARE recorded in full: a log redacted past the point of establishing what happened is
not an audit, it is a receipt for having logged.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
from pathlib import Path

from atlascore import ROOT, atlas

GENESIS = "0" * 64


def _rules() -> dict:
    return ((atlas().get("agent_policy") or {}).get("audit")) or {}


def stream_path(task_id: str) -> Path:
    """Where one task's events live. One file per task, named by the id the contract declares."""
    return ROOT / str(_rules().get("stream") or ".agent/audit") / f"{task_id}.jsonl"


def digest(value: object) -> dict:
    """A value as evidence rather than as content: its hash and its size."""
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, default=str).encode()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _seal(previous: str, body: dict) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(f"{previous}\n{canonical}".encode()).hexdigest()


def read_events(path: Path) -> list[dict]:
    """Every event on disk, with an unparseable line REPORTED rather than raised.

    FOUND BY ITS OWN NEGATIVE TEST: this raised on the first malformed line, which meant a
    corrupted stream could not be read at all — and a verifier that crashes on a tampered file is
    a verifier that says nothing about the tampering. A broken line is now an event of its own,
    so it breaks the chain at its sequence number and is named there, which is the point.
    """
    if not path.exists():
        return []
    try:
        if path.suffix == ".gz":
            import gzip  # noqa: PLC0415

            text = gzip.decompress(path.read_bytes()).decode("utf-8", errors="replace")
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        # A corrupt archive is evidence of one unreadable event; the verifier must report it
        # instead of treating an archived month as empty historical coverage.
        return [{"seq": 0, "event": "unparseable", "prev": "", "hash": "", "body": {}}]
    events: list[dict] = []
    for index, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            parsed = None
        events.append(
            parsed
            if isinstance(parsed, dict)
            else {"seq": index, "event": "unparseable", "prev": "", "hash": "", "body": {}}
        )
    return events


def head(path: Path) -> str:
    events = read_events(path)
    return str(events[-1]["hash"]) if events else GENESIS


def append(path: Path, kind: str, body: dict) -> dict:
    """Seal one event onto the chain. Refuses an undeclared kind and a stream over its byte cap.

    THE CAP IS A REFUSAL, NOT A PRUNE. A rotation here would delete the evidence the stream exists
    to hold, so the stream stops and says so — the refusal is itself the last event, which is why
    a truncated stream and a finished one can never be read as the same file.

    ONE WRITER AT A TIME. The head and the sequence are read, then the line is written; two hooks
    that did both at once sealed the same sequence twice and forked the owner's field ledger (found
    at 3.61.0, event 695, two writes 2 ms apart). The stream's own lock spans the read and the write.
    """
    kinds = [str(k) for k in (_rules().get("events") or [])]
    limit = int(_rules().get("max_stream_bytes") or 0)
    if kind not in kinds and kind != "audit_capped":
        raise ValueError(f"'{kind}' is not one of the {len(kinds)} declared audit events")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        events = read_events(path)
        size = path.stat().st_size
        if limit and size >= limit and kind != "audit_capped":
            # THE REFUSAL IS WRITTEN ONCE: re-recording it on every dropped event grew a capped stream
            # without limit, one refusal line per event, which made the cap a rate and not a bound.
            if events and events[-1].get("event") == "audit_capped":
                return events[-1]
            kind, body = "audit_capped", {"bytes": size, "cap": limit, "dropped_kind": kind}
        previous = str(events[-1]["hash"]) if events else GENESIS
        event = {"seq": len(events), "event": kind, "prev": previous, "body": body}
        event["hash"] = _seal(previous, event)
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":"), default=str) + "\n")
    return event


def verify(path: Path) -> list[str]:
    """Recompute every link. The FIRST break is what matters; the rest are its consequence."""
    problems: list[str] = []
    previous = GENESIS
    for index, event in enumerate(read_events(path)):
        body = {k: v for k, v in event.items() if k != "hash"}
        if event.get("seq") != index:
            problems.append(f"event {index}: sequence says {event.get('seq')} — an event was removed")
        if event.get("prev") != previous:
            problems.append(
                f"event {index}: links to {str(event.get('prev'))[:12]}, "
                f"the chain is at {previous[:12]} — history was rewritten here"
            )
        recomputed = _seal(str(event.get("prev")), body)
        if event.get("hash") != recomputed:
            problems.append(f"event {index} ({event.get('event')}): body does not hash to its seal")
        previous = str(event.get("hash"))
        if problems:
            break
    return problems


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="agentaudit.py")
    parser.add_argument("command", choices=("verify", "show"))
    parser.add_argument("task_id")
    args = parser.parse_args(argv)
    path = stream_path(args.task_id)
    events = read_events(path)
    if args.command == "show":
        for event in events:
            print(f"{event['seq']:>4} {event['event']:<20} {str(event['hash'])[:12]} {json.dumps(event['body'])[:120]}")
    problems = verify(path)
    for problem in problems:
        print(f"- {problem}")
    verdict = "BROKEN" if problems else ("OK" if events else "EMPTY")
    print(
        f"audit {args.task_id}: {verdict} — {len(events)} event(s), {path.stat().st_size if path.exists() else 0} bytes, "
        f"head {head(path)[:12]}"
    )
    return 1 if problems or not events else 0


if __name__ == "__main__":
    raise SystemExit(main())
