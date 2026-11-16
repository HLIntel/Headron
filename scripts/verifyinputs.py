"""Content identities for verification evidence."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from atlascore import ROOT, ls_files


def _input_names(root: Path) -> list[bytes]:
    names = ls_files(root, flags=("--cached", "--others", "--exclude-standard"))
    return sorted(name.encode("utf-8", "surrogateescape") for name in names)


def _digest(root: Path, names: list[bytes]) -> str:
    digest = hashlib.sha256(b"headron-verification-inputs-v2\0")
    for raw in names:
        path = root / os.fsdecode(raw)
        try:
            info = path.lstat()
        except FileNotFoundError:
            kind, mode, content = b"missing", 0, b""
        else:
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                kind = b"symlink"
                target = os.fsencode(os.readlink(path))
                if path.is_file():
                    target_bytes = path.read_bytes()
                    content = len(target).to_bytes(8, "big") + target + target_bytes
                    mode = stat.S_IMODE(path.stat().st_mode)
                elif not path.exists():
                    content = len(target).to_bytes(8, "big") + target
                else:
                    raise ValueError(f"unsupported verification symlink target: {path}")
            elif stat.S_ISREG(info.st_mode):
                kind, content = b"file", path.read_bytes()
            else:
                raise ValueError(f"unsupported verification input: {path}")
        for field in (raw, kind, str(mode).encode(), content):
            digest.update(len(field).to_bytes(8, "big"))
            digest.update(field)
    return digest.hexdigest()


def input_digest(root: Path = ROOT) -> str:
    """Bind each path, file kind, mode and bytes with unambiguous lengths."""
    return _digest(root, _input_names(root))
