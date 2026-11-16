#!/usr/bin/env python3
"""`headron ci`: run THIS checkout's CI, the jobs its own scripts/cipipeline.py declares.

A TRAMPOLINE, NOT A RUNNER: an installed `headron` runs its own root's scripts, so a runner here would judge a
lane by the jobs main declares. This finds the checkout the caller stands in and hands every argument to that
tree's .github/ci-local.sh, which runs the tree's own scripts/cilocal.py over the tree's own declaration.

proves: `headron ci` runs the CI the current checkout declares, or refuses with what to do; it never runs another tree's
does_not_prove: that any job passes; that is .github/ci-local.sh and the steps it runs
closed_by: cilocal_test.py, which runs it outside a checkout and in one that declares no native CI
"""

from __future__ import annotations

import itertools
import os
import subprocess
import sys
from pathlib import Path

from atlascore import text_of


def shim(cwd: str | Path = ".") -> Path | str:
    """The checkout's .github/ci-local.sh, or why there is none."""
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True, check=False, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"git could not answer: {exc}"
    if top.returncode:
        return "not inside a git checkout; cd into a Headron checkout, then run `headron ci`"
    tree = Path(top.stdout.strip())
    script = tree / ".github" / "ci-local.sh"
    if not (script.is_file() and (tree / "scripts" / "cipipeline.py").is_file()):
        return f"{tree} declares no native CI (no .github/ci-local.sh beside scripts/cipipeline.py); run it in a Headron checkout"
    return script


def usage(found: Path | str) -> str:
    """The shim's own USAGE block, so the forms it accepts have one home; else this module's summary."""
    head = (__doc__ or "").split("\n\n", 1)[0]
    if isinstance(found, str):
        return f"{head}\n{found}"
    lines = text_of(found).splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "# USAGE"), len(lines))
    block = [line[2:] for line in itertools.takewhile(lambda line: line.startswith("#   "), lines[start + 1 :])]
    return "\n".join([head, "", "usage (headron ci passes every argument on):", *block])


def main(argv: list[str]) -> int:
    found = shim()
    if argv[:1] in (["-h"], ["--help"]):  # answered here: the shim would run the jobs
        print(usage(found))
        return 0
    if isinstance(found, str):
        print(f"ci: {found}", file=sys.stderr)
        return 2
    sys.stdout.flush()
    os.execv(found, [str(found), *argv])
    return 2  # unreachable: execv replaces this process or raises


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
