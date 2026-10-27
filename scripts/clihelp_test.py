#!/usr/bin/env python3
"""Planted case: a script that parses no arguments runs its whole program on --help."""

from __future__ import annotations

import pathlib
import tempfile

# `headron` is the shipped entry: atlas_cli only delegates to the argparse in atlas.py, which answers --help
DELEGATES = {"atlas_cli.py"}


def help_errors(folder: pathlib.Path) -> list[str]:
    """Every runnable script (a `__main__` block, not a test) must parse arguments or answer -h/--help itself."""
    found = []
    for path in sorted(folder.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if path.name in DELEGATES or path.name.endswith("_test.py") or '__name__ == "__main__"' not in text:
            continue
        if "argparse" not in text and "--help" not in text:
            found.append(
                f"{path.name}: `--help` would RUN the program (it parses no arguments and never answers -h/--help)"
            )
    return found


def clihelp_case(module) -> None:
    """agentbench.py --help ran 8 paid agent sessions: the flag fell through to the program."""
    here = pathlib.Path(__file__).parent
    real = help_errors(here)
    if real:
        raise SystemExit("FAIL " + "; ".join(real[:3]) + (f" (+{len(real) - 3} more)" if len(real) > 3 else ""))
    with tempfile.TemporaryDirectory() as scratch:
        planted = pathlib.Path(scratch) / "runs_on_help.py"
        planted.write_text('import sys\nif __name__ == "__main__":\n    print(sys.argv)\n', encoding="utf-8")
        if len(help_errors(pathlib.Path(scratch))) != 1:
            raise SystemExit("FAIL help_errors did not catch a script that runs on --help")
    module.CASES.append(
        (
            "every runnable script answers --help instead of running",
            "a --help that executed the program, here eight paid agent sessions",
        )
    )
    print("  ok    every runnable script answers --help instead of running")


def run(module) -> None:
    clihelp_case(module)
