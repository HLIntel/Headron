#!/usr/bin/env python3
"""Git's object identity, computed in this process: no `git` is spawned, so a hook can answer with zero shell calls.

WHY. A Git blob is named by the hash of `blob <byte length>\\0<content>`. That is a dozen lines of hashlib, and it
costs 17 microseconds on a small file where spawning `git hash-object` costs a median 9.79 ms (docs/GIT-OBJECTS.md).
The same module owns what an object id LOOKS like: forty zeros written by hand made pre-push refuse a new lane and a
delete in a SHA-256 repository as "non-fast-forward", because an absent object there is sixty-four zeros.

WHAT A MATCH PROVES. The bytes hashed are the bytes named: accidental corruption and a plain edit are caught.

WHAT IT DOES NOT PROVE.
- Who wrote the bytes. A hash carries no author: anyone can hash anything. Authorship is a signature's job.
- That a SHA-1 name is unique. SHA-1 is not collision-resistant, and hashlib has no collision detection, so two
  crafted files can share a name here that a sha1dc build of Git would refuse. A SHA-256 repository does not have this.
- That Git would store these bytes. `path_oid` is `git hash-object --no-filters`: a clean filter or text conversion
  changes content before Git hashes it, so a working file can differ from its blob and be unchanged. `verify_staged`
  reads stored objects, so no filter touches it; a caller comparing a working file must handle this itself.
- Anything about an object in a pack or an alternate: those are counted as unchecked, and a caller must read the count.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import struct
import sys
import zlib
from pathlib import Path
from typing import NamedTuple

OID_HEX = {"sha1": 40, "sha256": 64}
OID = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
GITLINK = 0o160000
_CHUNK = 1 << 20


def is_oid(value: object) -> bool:
    """A full object id in either format. Abbreviations and upper case are not ids: git never prints them as one."""
    return isinstance(value, str) and OID.fullmatch(value) is not None


def is_absent(oid: str) -> bool:
    """Git's "no object here" name: all zeros, as long as the repository's hash is."""
    return is_oid(oid) and not oid.strip("0")


def absent(object_format: str) -> str:
    return "0" * OID_HEX[object_format]


class BlobIdentity:
    """Mixin: any class that knows its `object_format` can name blobs the way that repository does."""

    object_format: str = "sha1"

    def _hasher(self, size: int) -> hashlib._Hash:
        # NOT usedforsecurity: this is Git's content address, and FIPS builds refuse SHA-1 otherwise.
        hasher = hashlib.new(self.object_format, usedforsecurity=False)
        hasher.update(b"blob %d\0" % size)
        return hasher

    def blob_oid(self, data: bytes) -> str:
        hasher = self._hasher(len(data))
        hasher.update(data)
        return hasher.hexdigest()

    def path_oid(self, path: Path | str) -> str:
        """The blob for what is at `path`, unfiltered. A symlink's blob is its target text, never what it points at."""
        info = os.lstat(path)
        if stat.S_ISLNK(info.st_mode):
            return self.blob_oid(os.fsencode(os.readlink(path)))
        hasher = self._hasher(info.st_size)
        with open(path, "rb") as handle:
            while chunk := handle.read(_CHUNK):
                hasher.update(chunk)
        return hasher.hexdigest()


class IndexEntry(NamedTuple):
    path: str
    mode: int
    oid: str
    stage: int


class Unsupported(Exception):
    """A shape this reader will not guess at. The caller falls back to `git`, and never reads this as a pass."""


class Staged(NamedTuple):
    checked: int
    mismatched: list[str]
    unchecked: int


class Repo(BlobIdentity):
    """One repository's files, found the way Git finds them: the environment first, then the `.git` entry."""

    def __init__(self, git_dir: Path, common_dir: Path, index: Path, objects: Path, object_format: str) -> None:
        self.git_dir, self.common_dir, self.index, self.objects = git_dir, common_dir, index, objects
        self.object_format = object_format

    @classmethod
    def discover(cls, start: Path | str = ".") -> Repo:
        """A hook runs with GIT_DIR, GIT_INDEX_FILE and, while a push is in quarantine, GIT_OBJECT_DIRECTORY set."""
        base = Path(start).resolve()
        named = os.environ.get("GIT_DIR")
        git_dir = (base / named).resolve() if named else _find_git_dir(base)
        common = os.environ.get("GIT_COMMON_DIR")
        pointer = git_dir / "commondir"
        if common:
            common_dir = (base / common).resolve()
        elif pointer.is_file():  # a linked worktree keeps its config and objects in the main .git
            common_dir = (git_dir / pointer.read_text(encoding="utf-8").strip()).resolve()
        else:
            common_dir = git_dir
        index = os.environ.get("GIT_INDEX_FILE")
        objects = os.environ.get("GIT_OBJECT_DIRECTORY")
        return cls(
            git_dir,
            common_dir,
            (base / index).resolve() if index else git_dir / "index",
            (base / objects).resolve() if objects else common_dir / "objects",
            _object_format(common_dir / "config"),
        )

    def entries(self) -> list[IndexEntry]:
        """The index, read directly. v4 path compression and a split index raise Unsupported, not a short list."""
        raw = self.index.read_bytes()
        size = OID_HEX[self.object_format] // 2
        if len(raw) < 12 + size or raw[:4] != b"DIRC":
            raise Unsupported(f"{self.index} is not a Git index")
        version, count = struct.unpack(">II", raw[4:12])
        if version not in (2, 3):
            raise Unsupported(f"index version {version}")
        trailer = raw[-size:]
        whole = hashlib.new(self.object_format, raw[:-size], usedforsecurity=False).digest()
        if trailer != whole and trailer.strip(b"\0"):  # all zero: index.skipHash, Git's own way of not checking
            raise Unsupported("the index checksum does not match its bytes")
        at, out = 12, []
        for _ in range(count):
            mode = struct.unpack(">I", raw[at + 24 : at + 28])[0]
            flags = struct.unpack(">H", raw[at + 40 + size : at + 42 + size])[0]
            name_at = at + 42 + size + (2 if flags & 0x4000 else 0)
            end = raw.index(b"\0", name_at)
            out.append(
                IndexEntry(os.fsdecode(raw[name_at:end]), mode, raw[at + 40 : at + 40 + size].hex(), (flags >> 12) & 3)
            )
            at += (end - at + 8) & ~7  # NUL-padded to a multiple of eight, always at least one NUL
        if b"link" == raw[at : at + 4]:
            raise Unsupported("a split index keeps its entries in another file")
        return out

    def loose_matches(self, oid: str) -> bool | None:
        """Re-hash one stored blob. None: it is not loose here, so nothing was proved. False: it is damaged or lying."""
        try:
            handle = (self.objects / oid[:2] / oid[2:]).open("rb")
        except FileNotFoundError:
            return None
        hasher = hashlib.new(self.object_format, usedforsecurity=False)
        inflater, head, total = zlib.decompressobj(), b"", 0
        with handle:
            try:
                while chunk := handle.read(_CHUNK):
                    plain = inflater.decompress(chunk)
                    hasher.update(plain)
                    total += len(plain)
                    head = head or plain[:64]
                if not inflater.eof:
                    return False
            except zlib.error:
                return False
        kind = head.partition(b"\0")[0]
        declared = re.fullmatch(rb"blob (\d+)", kind)
        return declared is not None and total == int(declared[1]) + len(kind) + 1 and hasher.hexdigest() == oid

    def verify_staged(self) -> Staged:
        """Every staged blob stored loose is re-hashed. A gitlink names a commit elsewhere and a pack is not read."""
        checked, unchecked, mismatched = 0, 0, []
        for entry in self.entries():
            if entry.mode == GITLINK or stat.S_ISDIR(entry.mode):
                continue
            verdict = self.loose_matches(entry.oid)
            if verdict is None:
                unchecked += 1
                continue
            checked += 1
            if not verdict:
                mismatched.append(entry.path)
        return Staged(checked, mismatched, unchecked)


def _find_git_dir(base: Path) -> Path:
    for directory in (base, *base.parents):
        dot_git = directory / ".git"
        if dot_git.is_dir():
            return dot_git
        if dot_git.is_file():  # a linked worktree or a submodule: one line, `gitdir: <path>`
            target = dot_git.read_text(encoding="utf-8").strip().removeprefix("gitdir:").strip()
            return (directory / target).resolve()
    raise Unsupported(f"no .git at or above {base}")


def _object_format(config: Path) -> str:
    """`extensions.objectformat` from the common config. Absent means SHA-1, and an unknown value is refused."""
    section = ""
    for line in config.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            section = stripped.strip("[]").strip().lower()
        elif section == "extensions" and stripped.lower().replace(" ", "").startswith("objectformat="):
            value = stripped.split("=", 1)[1].strip().lower()
            if value not in OID_HEX:
                raise Unsupported(f"object format {value!r}")
            return value
    return "sha1"


def main(argv: list[str]) -> int:
    """`gitobject.py verify-staged`: exit 1 on damage, 2 when this reader cannot judge. Unchecked is printed, not hidden."""
    if argv in (["-h"], ["--help"]):
        print("usage: gitobject.py verify-staged")
        return 0
    if argv != ["verify-staged"]:
        print("usage: gitobject.py verify-staged", file=sys.stderr)
        return 2
    try:
        report = Repo.discover().verify_staged()
    except (Unsupported, OSError) as exc:
        print(f"gitobject: NOT RUN — {exc}; use git fsck", file=sys.stderr)
        return 2
    print(f"gitobject: {report.checked} staged blob(s) re-hashed, {report.unchecked} in a pack or absent (NOT checked)")
    for path in report.mismatched:
        print(f"gitobject: DAMAGED {path}", file=sys.stderr)
    return 1 if report.mismatched else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
