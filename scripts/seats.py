#!/usr/bin/env python3
"""Attach declared agent, model, chat, and plugin seats on this machine.

The roster is atlas.yaml's runtime_entry plus the declared companion rows: a client never carries a
second list of attachable integrations.  State is deliberately local and contains only attachment
times, never credentials, paths, network answers, or an assertion that an attached runtime is live.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import tempfile
from pathlib import Path

from atlascore import atlas


def state_path() -> Path:
    """The explicit state file wins; the standard state-home fallback stays outside the checkout."""
    if value := os.environ.get("THEA_SEATS_STATE"):
        return Path(value)
    if value := os.environ.get("XDG_STATE_HOME"):
        return Path(value) / "thea" / "seats.json"
    return Path.home() / ".local" / "state" / "thea" / "seats.json"


def roster() -> list[dict[str, str | None]]:
    """The only seat roster: atlas runtime entries, then declared companions, with atlas owning kinds."""
    spec = atlas().get("seats") or {}
    excluded = set(spec.get("exclude") or [])
    kinds = spec.get("kinds") or {}
    default = kinds.get("runtime_entry")
    rows = []
    for item in atlas().get("runtime_entry") or []:
        seat_id = item.get("id")
        if seat_id in excluded:
            continue
        rows.append(
            {
                "id": seat_id,
                "kind": kinds.get(seat_id, default),
                "name": item.get("runtime"),
                "loads": item.get("loads"),
                "adapter": item.get("adapter"),
            }
        )
    for seat_id in spec.get("companions") or []:
        item = (atlas().get("companions") or {}).get(seat_id) or {}
        if seat_id not in excluded:
            rows.append(
                {"id": seat_id, "kind": kinds.get(seat_id), "name": item.get("what"), "loads": None, "adapter": None}
            )
    return rows


def _timestamp(value: object) -> bool:
    if not isinstance(value, str) or "T" not in value:
        return False
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def read_state(path: Path, known: set[str]) -> tuple[dict[str, dict[str, str]], str]:
    """Return the whole file or unreadable: malformed state is never silently repaired."""
    if not path.exists():
        return {}, "empty"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, "unreadable"
    if not isinstance(raw, dict) or any(
        seat_id not in known
        or not isinstance(record, dict)
        or set(record) != {"attached_at"}
        or not _timestamp(record.get("attached_at"))
        for seat_id, record in raw.items()
    ):
        return {}, "unreadable"
    return raw, "recorded" if raw else "empty"


def write_state(path: Path, state: dict[str, dict[str, str]]) -> None:
    """Write a private complete replacement beside its destination, then atomically rename it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".seats-", delete=False)
    temporary = Path(handle.name)
    try:
        os.chmod(temporary, 0o600)
        json.dump(state, handle, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(temporary, path)
    finally:
        if not handle.closed:
            handle.close()
        temporary.unlink(missing_ok=True)


def seat_records(rows: list[dict[str, str | None]], state: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    return [
        {**row, "attached": row["id"] in state, "attached_at": state.get(row["id"], {}).get("attached_at")}
        for row in rows
    ]


def emit(value: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, separators=(",", ":")))
    elif isinstance(value, list):
        for row in value:
            print(f"{row['id']}\t{row['kind']}\t{row['name']}\t{'attached' if row['attached'] else 'detached'}")
    else:
        print(f"{value['id']}\t{value['kind']}\t{value['name']}\t{'attached' if value['attached'] else 'detached'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thea seats", description="attach or detach atlas-declared local seats")
    parser.add_argument("action", nargs="?", choices=("attach", "detach"))
    parser.add_argument("id", nargs="?")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    rows = roster()
    by_id = {row["id"]: row for row in rows}
    path = state_path()
    state, status = read_state(path, set(by_id))
    if not args.action:
        emit({"seats": seat_records(rows, state), "state": status}, args.json)
        return 0
    if args.id not in by_id:
        print(f"seats: unknown id: {args.id}", file=os.sys.stderr)
        return 2
    if status == "unreadable":
        print("seats: state unreadable; refusing to overwrite it", file=os.sys.stderr)
        return 1
    if args.action == "attach":
        state.setdefault(args.id, {"attached_at": dt.datetime.now(dt.timezone.utc).isoformat()})
    else:
        state.pop(args.id, None)
    write_state(path, state)
    emit(seat_records([by_id[args.id]], state)[0], args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
