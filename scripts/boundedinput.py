"""Bounded UTF-8 stdin for hooks and local decision requests. Oversized input is refused, never truncated."""

import sys
from typing import IO

MAX_INPUT_BYTES = 1024 * 1024


def read_stdin(stream: IO[bytes] | IO[str] | None = None, limit: int = MAX_INPUT_BYTES) -> str:
    source = sys.stdin if stream is None else stream
    reader = getattr(source, "buffer", source)
    raw = reader.read(limit + 1)
    size = len(raw) if isinstance(raw, bytes) else len(raw.encode("utf-8"))
    if size > limit:
        raise SystemExit(f"stdin exceeds {limit} UTF-8 bytes; reduce the hook payload or decision input")
    try:
        return raw.decode("utf-8") if isinstance(raw, bytes) else raw
    except UnicodeDecodeError as exc:
        raise SystemExit("stdin is not valid UTF-8") from exc
