#!/usr/bin/env python3
"""Replace one file whole: a reader sees the old bytes or the new ones, never a torn file.

WHY. Six writers rolled this by hand and only one had the whole shape. `githubapp._write_atomic` wrote to a FIXED
scratch name, so two workers on one job could rename each other's half-written bytes into place, and five skipped
the fsync, so a rename could land ahead of its data after a crash. Forbidden_calls/hand_rolled_atomic_write holds
the line now: this module owns `os.replace`.

THE SHAPE. A private temporary beside the destination (same filesystem, or the rename is a copy), written, flushed
and fsynced, renamed over the destination, then the directory fsynced. The temporary never outlives the call unless
the process is killed, and the `.tmp` suffix leaves that orphan to the sweeps that already look for it. New files
are 0600: nothing here is read by another user.

WHAT IT DOES NOT PROVE. That concurrent writers are serialised: last rename wins, and an update can still be lost.
Or that the bytes reached the platter: on macOS fsync stops at the drive cache, and F_FULLFSYNC is not used.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def _sync_directory(directory: Path) -> None:
    """Make the rename itself durable. Best effort: some filesystems refuse to fsync a directory."""
    with contextlib.suppress(OSError):
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def write_bytes(path: Path | str, data: bytes) -> None:
    """Replace `path` with exactly `data`. Its directory must exist; a failure leaves the old file untouched."""
    target = Path(path)
    descriptor, name = tempfile.mkstemp(dir=target.parent, prefix=".atomic-", suffix=".tmp")
    scratch = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(scratch, target)
        _sync_directory(target.parent)
    finally:
        scratch.unlink(missing_ok=True)


def write_text(path: Path | str, text: str) -> None:
    """`write_bytes` for UTF-8 text."""
    write_bytes(path, text.encode("utf-8"))


def move(source: Path | str, target: Path | str) -> None:
    """Rename `source` onto `target`, durably. A missing source raises FileNotFoundError: a lost claim race says so."""
    os.replace(source, target)
    _sync_directory(Path(target).parent)
