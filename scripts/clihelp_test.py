#!/usr/bin/env python3
"""Planted case: a script that parses no arguments runs its whole program on --help."""

from __future__ import annotations

import importlib
import pathlib
import re
import tempfile
from types import ModuleType

import commands

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


def clihelp_case(module: ModuleType) -> None:
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


def verify_flags_case(module: ModuleType) -> None:
    """`headron verify --receipt` stopped at the parser while verify.py took it: every flag verify.py promises
    parses, and comes back out for verify.py, and a line of shell reads as its own commands."""
    from agreement import documented_commands, named_verbs
    from commands import build_parser, command_table, forwarded_argv
    from verify import __doc__ as usage

    parser = build_parser()[0]
    promised = set(re.findall(r"\[(--[a-z-]+)", next(ln for ln in (usage or "").splitlines() if "verify.py [" in ln)))
    lost = sorted(promised - {flag for a in command_table(parser)["verify"]["arguments"] for flag in a.option_strings})
    if lost:
        raise SystemExit(f"FAIL verify.py promises {lost}, which `headron verify` does not parse")
    given = ["--json", "--changed", "--fresh", "--base", "b", "--change", "c", "--jobs", "2", "--receipt", "r"]
    back = forwarded_argv(parser.parse_args(["verify", *given]), "verify")
    if sorted(back) != sorted(given):
        raise SystemExit(f"FAIL verify flags did not reach verify.py: gave {given}, forwarded {back}")
    read = documented_commands('`headron a --x && headron b "--no" --y -- --z`\n```bash\nhi; headron c --w # --v\n```')
    if read != {("a", ("--x",)), ("b", ("--y",)), ("c", ("--w",))}:
        raise SystemExit(f"FAIL documented_commands misread a line of shell: {sorted(read)}")
    named = named_verbs("use the report verb, then the `gate` verb; a verb alone is no name")
    if named != {("report", ()), ("gate", ())}:
        raise SystemExit(f"FAIL named_verbs misread prose: {sorted(named)}")
    module.CASES.append(("verify's promised flags parse and reach verify.py", "a documented flag that exits 2"))
    print("  ok    verify's promised flags parse and reach verify.py")


def entry_surface_cases(module: ModuleType) -> None:
    """A step that names no real command or flag fails, in a shell fence, in a span and in the text init writes."""
    for where, find, replace, name in (
        ("README.md", "headron proof <file>", "headron proove <file>", "a dead command in a README fence FAILS"),
        ("scripts/onboard.py", "Then `headron proof", "Then `headron proove", "a dead command in init's text FAILS"),
        (
            "README.md",
            "`headron verify --changed`",
            "`headron verify --changedd`",
            "a dead flag in a README span FAILS",
        ),
        (
            "skills/headron/SKILL.md",
            "A chat that cannot edit files",
            "File it with the report verb. A chat that cannot edit files",
            "a dead verb named in an entry surface's prose FAILS",
        ),
    ):
        with module.mutated(where, lambda s, f=find, r=replace: s.replace(f, r, 1)):
            module.case(
                name,
                "the reader's step is a usage error, as `headron report` and `verify --receipt` were",
                True,
                "which this CLI does not have",
                by="agreement.agreement_errors",
            )
    # The enforcer runs in this process and reads the parser already loaded, so load the planted source.
    with module.mutated(
        "scripts/commands.py", lambda s: s.replace('"--receipt", default=None', '"--receiptt", default=None', 1)
    ):
        importlib.reload(commands)
        module.case(
            "a printed flag the parser lost FAILS",
            "a flag the README still prints after the parser dropped it",
            True,
            "which this CLI does not have",
            by="agreement.agreement_errors",
        )
    importlib.reload(commands)


def run(module: ModuleType) -> None:
    clihelp_case(module)
    verify_flags_case(module)
    entry_surface_cases(module)
