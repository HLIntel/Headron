#!/usr/bin/env python3
"""The tool a project installed for itself, found where its package manager put it.

A project's tsc or eslint lives in node_modules/.bin and its pytest or ruff in .venv/bin, and neither is on
PATH. Looking on PATH alone read them as "not installed here", or ran a global copy at some other version than
the one the project pinned. So a project-local copy wins, the way npx and uv run choose.

TRUST: a commit hook runs what this returns, so a clone must not be able to choose it. A directory counts only
inside a git repository, and only when git tracks nothing that is the same directory on disk, so what it holds
came from this machine's own install. The comparison is by file identity, not by name: on a case-folding disk
a tracked Node_Modules IS node_modules. gradlew and mvnw are always tracked, so they are not handled here.

proves: a project-local tool is found first, and a tracked directory is never trusted
does_not_prove: that the local copy matches the lockfile, or anything about Windows Scripts directories
closed_by: localtools_test.py, which plants a tracked directory, a tracked symlink and a case-variant name
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from atlascore import ls_files

LOCAL_DIRS = ("node_modules/.bin", ".venv/bin", "venv/bin", "vendor/bin")


def _untracked(base: Path, name: str) -> bool:
    """git tracks nothing that is base/name on disk. An answer git cannot give is not trust."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        listed = ls_files(base, env=env)
    except (SystemExit, OSError, subprocess.TimeoutExpired):
        return False
    tops = {path.split("/", 1)[0] for path in listed}
    here = base / name
    return not any((base / top).exists() and os.path.samefile(base / top, here) for top in tops)


def local_bin_dirs(start: Path) -> list[Path]:
    """Trusted tool directories from start up to its repository's top, nearest first; none outside a repository."""
    here = start.resolve()
    if not here.is_dir():
        here = here.parent
    chain = [here, *here.parents]
    tops = [index for index, place in enumerate(chain) if (place / ".git").exists()]
    if not tops:
        return []
    found = []
    for base in chain[: tops[0] + 1]:
        for local in LOCAL_DIRS:
            candidate = base / local
            if candidate.is_dir() and _untracked(base, local.split("/", 1)[0]):
                found.append(candidate)
    return found


def find_tool(name: str, start: Path | str | None = None) -> str | None:
    """Where name runs from for a file or directory at start: its project's copy, else PATH's, else None."""
    local = local_bin_dirs(Path(start) if start else Path.cwd())
    return shutil.which(name, path=os.pathsep.join([*map(str, local), os.environ.get("PATH", os.defpath)]))
