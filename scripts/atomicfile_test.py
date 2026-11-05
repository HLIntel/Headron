#!/usr/bin/env python3
"""atomicfile: the old bytes survive a failure, the temporary never does, and concurrent writers never tear."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import threading
from pathlib import Path
from types import ModuleType
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import atomicfile
import callshape


def _strays(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir() if p.name != "state.json")


def replaced_whole_case(directory: Path) -> None:
    target = directory / "state.json"
    atomicfile.write_text(target, "first é\n")
    if target.read_bytes() != "first é\n".encode():
        raise SystemExit(f"FAIL text was not written as UTF-8: {target.read_bytes()!r}")
    atomicfile.write_bytes(target, b"second")
    if target.read_bytes() != b"second" or _strays(directory):
        raise SystemExit(f"FAIL replace left {target.read_bytes()!r} and strays {_strays(directory)}")
    if stat.S_IMODE(target.stat().st_mode) != 0o600:
        raise SystemExit(f"FAIL a new file is not private: {oct(target.stat().st_mode)}")
    print("  ok    a write replaces the file whole, private, with no temporary left")


def failure_keeps_old_case(directory: Path) -> None:
    target = directory / "state.json"
    atomicfile.write_bytes(target, b"old")
    for name in ("fsync", "replace"):
        with mock.patch.object(atomicfile.os, name, side_effect=OSError(f"planted {name}")):
            try:
                atomicfile.write_bytes(target, b"new")
            except OSError:
                pass
            else:
                raise SystemExit(f"FAIL a failed {name} was swallowed: the caller would believe the write happened")
        if target.read_bytes() != b"old" or _strays(directory):
            raise SystemExit(f"FAIL failed {name} left {target.read_bytes()!r} and strays {_strays(directory)}")
    print("  ok    a failed fsync or rename keeps the old bytes and removes the temporary")


def synced_before_rename_case(directory: Path) -> None:
    target = directory / "state.json"
    order: list[str] = []
    real_fsync, real_replace = os.fsync, os.replace

    def fsync(fd: int) -> None:
        order.append("fsync")
        real_fsync(fd)

    def replace(source: Path | str, destination: Path | str) -> None:
        order.append("replace")
        real_replace(source, destination)

    with mock.patch.object(atomicfile.os, "fsync", fsync), mock.patch.object(atomicfile.os, "replace", replace):
        atomicfile.write_bytes(target, b"durable")
    if order != ["fsync", "replace", "fsync"]:
        raise SystemExit(f"FAIL want data fsync, rename, directory fsync; got {order}")
    print("  ok    data is fsynced before the rename and the directory after it")


def concurrent_writers_case(directory: Path) -> None:
    target = directory / "state.json"
    payloads = [bytes([65 + n]) * 200_000 for n in range(4)]
    atomicfile.write_bytes(target, payloads[0])
    torn: list[int] = []
    raised: list[OSError] = []
    done = threading.Event()

    def writer(payload: bytes) -> None:
        for _ in range(8):
            try:
                atomicfile.write_bytes(target, payload)
            except OSError as exc:  # a thread's exception otherwise vanishes and the case passes
                raised.append(exc)

    def reader() -> None:
        while not done.is_set():
            seen = target.read_bytes()
            if seen not in payloads:
                torn.append(len(seen))

    watching = threading.Thread(target=reader)
    watching.start()
    writers = [threading.Thread(target=writer, args=(p,)) for p in payloads]
    for thread in writers:
        thread.start()
    for thread in writers:
        thread.join(timeout=60)
    done.set()
    watching.join(timeout=60)
    if torn or raised or _strays(directory):
        raise SystemExit(f"FAIL concurrent writers: torn {torn[:3]}, raised {raised[:2]}, left {_strays(directory)}")
    print("  ok    four writers on one file never show a reader torn bytes")


def move_case(directory: Path) -> None:
    source, target = directory / "job.json", directory / "state.json"
    source.write_bytes(b"claimed")
    atomicfile.move(source, target)
    if target.read_bytes() != b"claimed" or source.exists():
        raise SystemExit("FAIL move did not carry the file")
    try:
        atomicfile.move(source, target)
    except FileNotFoundError:
        print("  ok    move carries the file, and a lost claim race raises FileNotFoundError")
    else:
        raise SystemExit("FAIL moving a missing file passed: two workers would both believe they won the job")


def guard_case(directory: Path) -> None:
    """forbidden_calls/hand_rolled_atomic_write, on planted files: both receivers bite, a string edit never does."""
    row = callshape.rules()["hand_rolled_atomic_write"]
    # Built here so this file's own text plants nothing for a tree-wide scan.
    planted = {
        "os_replace.py": ("os" + ".replace(a, b)", True),
        "os_rename.py": ("os" + ".rename(a, b)", True),
        "path_replace.py": ("scratch" + ".replace(target)", True),
        "path_rename.py": ("hook" + ".rename(legacy)", True),
        "chained.py": ("Path(a)" + ".with_suffix(b).replace(target)", True),
        "string_edit.py": ('text.replace("a", "b")', False),
        "date_edit.py": ("stamp.replace(tzinfo=zone)", False),
        "frame_rename.py": ("table.rename(columns, axis=1)", False),
        "atomicfile.py": ("os" + ".replace(a, b)", False),
        "atlas_cli.py": ("os" + ".replace(a, b)", False),
        "planted_test.py": ("os" + ".replace(a, b)", False),
    }
    paths = [directory / name for name in planted]
    for path, (line, _) in zip(paths, planted.values(), strict=True):
        path.write_text(line + "\n", encoding="utf-8")
    with mock.patch.object(callshape, "ROOT", directory), mock.patch.object(callshape, "_sources", lambda _: paths):
        hit = {path for path, _ in callshape.findings({"row": row})["row"]}
    want = {name for name, (_, bites) in planted.items() if bites}
    if hit != want:
        raise SystemExit(f"FAIL the guard missed {sorted(want - hit)} and wrongly refused {sorted(hit - want)}")
    print("  ok    a hand-rolled rename is refused on either receiver; string edits and the owners are not")


def run(module: ModuleType | None) -> None:
    for case in (
        replaced_whole_case,
        failure_keeps_old_case,
        synced_before_rename_case,
        concurrent_writers_case,
        move_case,
        guard_case,
    ):
        with tempfile.TemporaryDirectory(prefix="atomicfile-") as directory:
            case(Path(directory))


if __name__ == "__main__":
    run(None)
