#!/usr/bin/env python3
"""pointers: a path reads what it says, a row refuses in its own sentence, and an unexplained file string surfaces."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pointers

ATLAS = {
    "scopes": {"docs": {"never": ["gone.md", "README.md"]}, "scripts": {"never": []}},
    "packs": {"good": {"role": "lint"}, "bare": None, "blank": {}},
    "named": {"banner": "gone.md"},
}
TESTS = {"tree": lambda value: value in {"", "README.md"}, "role": {"lint"}.__contains__}


def path_case() -> tuple[str, str]:
    reads = {
        "scopes/@": [((), "docs"), ((), "scripts")],
        "scopes/*/never/*": [(("docs", "gone.md"), "gone.md"), (("docs", "README.md"), "README.md")],
        "packs/*/role": [(("good",), "lint"), (("bare",), None), (("blank",), None)],
        "named/banner": [((), "gone.md")],
        "named/left_out": [((), None)],
        "absent/*/role": [],
        "absent/mid/field": [],
    }
    for at, expected in reads.items():
        found = list(pointers.resolve_path(ATLAS, at.split("/")))
        if found != expected:
            raise SystemExit(f"FAIL {at} read {found}, not {expected}")
    return "a path reads keys, items and fields, and a field left out reads as None", "a reader that skips a shape"


def row_case() -> tuple[str, str]:
    never = {"at": "scopes/*/never/*", "is": "tree", "says": "{1} forbids {value}"}
    if pointers.row_errors(never, ATLAS, TESTS) != ["docs forbids gone.md"]:
        raise SystemExit(f"FAIL a stale name refused wrongly: {pointers.row_errors(never, ATLAS, TESTS)}")
    optional = {"at": "named/left_out", "is": "tree", "says": "{value} is stale"}
    if pointers.row_errors(optional, ATLAS, TESTS):
        raise SystemExit("FAIL a path field left out read as stale: an optional pointer points at nothing")
    required = {"at": "packs/*/role", "is": "role", "says": "{1} names '{value}'"}
    if pointers.row_errors(required, ATLAS, TESTS) != ["bare names 'None'", "blank names 'None'"]:
        raise SystemExit(f"FAIL a required name left out passed: {pointers.row_errors(required, ATLAS, TESTS)}")
    return (
        "a row refuses a stale name in its own sentence, and a field left out by its kind",
        "a row that passes a stale name",
    )


def uncovered_case() -> tuple[str, str]:
    data = {
        "a": {"b": "lost.py", "kept": "README.md"},
        "c": ["atlas.py", "words, not a file"],
        "lost_key.md": 1,
        "theirs": {"x": ["pyproject-of-theirs.toml"]},
    }
    found = pointers.uncovered_paths(data, ["theirs/*"])
    if found != [("a/b", "lost.py"), ("", "lost_key.md")]:
        raise SystemExit(f"FAIL an unexplained file string misread: {found}")
    return "a file string resolving nowhere surfaces, unless its place is declared foreign", "a path no row covers"


def drawn_case() -> tuple[str, str]:
    block = pointers.table_block()
    if "flowchart LR" not in block or "`identity/banner` | tree | 1 |" not in block:
        raise SystemExit(f"FAIL the page lost its diagram or a row: {block[:300]}")
    return "the page draws section to kind and lists each row with what it names now", "a page that lost a row"


def run(module: ModuleType | None) -> None:
    for proved in (path_case, row_case, uncovered_case, drawn_case):
        name, kills = proved()
        print(f"  ok    {name}")
        if module is not None:
            module.CASES.append((name, kills))


if __name__ == "__main__":
    run(None)
