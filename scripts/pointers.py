#!/usr/bin/env python3
"""The pointer table: every name in atlas.yaml that points at something else, in one place, read by one engine.

An instrument used to carry its own three lines: walk a section, ask whether the name resolves, append a sentence.
A row in `atlas.yaml/pointers` now says all three, the way a decision table says a verdict: where the names sit,
what they must be, and what the reader is told when one is not. A new pointer is a row and not a loop.

A row's `at` is a path into atlas.yaml. `*` is every key of a mapping or every item of a list, and a final `@`
reads the keys of a mapping where the name is the key. `says` is a sentence with `{value}` and `{1}`, `{2}` for
what each `*` matched. `is` names a resolver in RESOLVERS.

proves: every name a row covers resolves to what the row says it must be, and any other file-shaped string in
  atlas.yaml resolves in this tree unless its place is declared to name a file in a consuming project
does_not_prove: that a pointer is the RIGHT one, only that it lands on something real of the declared kind
closed_by: pointers_test.py, which plants a stale name under a row and a stale path in an uncovered section
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Callable, Iterator
from typing import Any

from atlascore import ROOT, atlas, route_targets

FILE_SHAPED = re.compile(r"[\w./-]+\.(?:py|md|yaml|yml|json|sh|toml|tsv|go|rs|txt)")
OPTIONAL_KINDS = frozenset({"tree", "file", "directory", "script"})  # a path field left out points at nothing


def _authority_roles() -> set[str]:
    from packmanifest import manifest_schema  # noqa: PLC0415 - packmanifest loads after the atlas it validates

    return set(manifest_schema()["properties"]["authority"]["properties"])


def _done_gates() -> set[str]:
    return {str(row.get("id")) for row in (atlas().get("verification_policy") or {}).get("done_set") or []}


def _decisions() -> set[str]:
    from knowledge import decision_records  # noqa: PLC0415 - knowledge loads after this instrument

    return set(decision_records())


# name -> what builds a test of one value. A set-valued resolver is built once per run of `pointer_errors`.
RESOLVERS: dict[str, Callable[[], Callable[[str], bool]]] = {
    "tree": lambda: lambda value: (ROOT / value).exists(),
    "file": lambda: lambda value: (ROOT / value).is_file(),
    "directory": lambda: lambda value: (ROOT / value).is_dir(),
    "script": lambda: lambda value: (ROOT / "scripts" / value).exists(),
    "route": lambda: set(route_targets()).__contains__,
    "role": lambda: _authority_roles().__contains__,
    "gate_role": lambda: (_authority_roles() | {"none"}).__contains__,
    "done_gate": lambda: _done_gates().__contains__,
    "decision": lambda: _decisions().__contains__,
}


def resolve_path(data: Any, parts: list[str], matched: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    """Each (what the stars matched, value) at `parts` under `data`. A place absent from the atlas yields nothing
    for `*`, and a named final field left out yields None, so a row can refuse the omission."""
    if not parts:
        yield matched, data
        return
    head, rest = parts[0], parts[1:]
    if head == "@":
        yield from ((matched, key) for key in (data if isinstance(data, dict) else ()))
    elif head == "*" and isinstance(data, dict):
        for key, value in data.items():
            yield from resolve_path(value, rest, (*matched, str(key)))
    elif head == "*":
        for value in data if isinstance(data, list) else ():
            yield from resolve_path(value, rest, (*matched, str(value)))
    elif not rest:
        yield matched, data.get(head) if isinstance(data, dict) else None
    elif isinstance(data, dict):
        yield from resolve_path(data.get(head), rest, matched)


def row_errors(row: dict[str, Any], data: dict[str, Any], tests: dict[str, Callable[[str], bool]]) -> list[str]:
    """What one row refuses, each in the sentence the row declares."""
    errors: list[str] = []
    for matched, value in resolve_path(data, str(row["at"]).split("/")):
        name = "" if value is None and row["is"] in OPTIONAL_KINDS else str(value)
        if not tests[row["is"]](name):
            fields = {str(index): text for index, text in enumerate(matched, 1)} | {"value": str(value)}
            errors.append(re.sub(r"\{(\w+)\}", lambda m: fields.get(m[1], m[0]), str(row["says"])))
    return errors


def uncovered_paths(data: dict[str, Any], foreign: list[str]) -> list[tuple[str, str]]:
    """Every file-shaped string in the atlas that resolves nowhere, with where it sits, leaving out the places
    declared to name a file in a consuming project."""
    found: list[tuple[str, str]] = []

    def visit(value: Any, where: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                visit(key, where)
                visit(item, f"{where}/{key}" if where else str(key))
        elif isinstance(value, list):
            for item in value:
                visit(item, where)
        elif (
            isinstance(value, str)
            and FILE_SHAPED.fullmatch(value)
            and not (ROOT / value).exists()
            and not (ROOT / "scripts" / value).exists()
            and not any(fnmatch.fnmatchcase(where, place) for place in foreign)
        ):
            found.append((where, value))

    visit(data, "")
    return found


def pointer_errors() -> list[str]:
    """Every stale pointer in the atlas: the declared rows, then any file-shaped string no row or place explains."""
    data = atlas()
    table = data.get("pointers") or {}
    rows = table.get("rows") or []
    tests = {name: build() for name, build in RESOLVERS.items()}
    errors = [
        f"pointers/rows names resolver '{row.get('is')}', which does not exist"
        for row in rows
        if row.get("is") not in tests
    ]
    for row in rows:
        if row.get("is") in tests:
            errors += row_errors(row, data, tests)
    errors += [
        f"{where} names {value}, which is not in the tree; correct it, or declare the place in "
        "pointers/foreign when it names a file in a consuming project"
        for where, value in uncovered_paths(data, [str(place) for place in table.get("foreign") or []])
    ]
    return errors


def table_block() -> str:
    """docs/POINTERS.md: which section points at what kind of thing, drawn and then listed row by row."""
    data = atlas()
    rows = (data.get("pointers") or {}).get("rows") or []
    edges = sorted({(str(row["at"]).split("/", 1)[0], str(row["is"])) for row in rows})
    lines = ["```mermaid", "flowchart LR"]
    lines += [f"    {section}[{section}] --> {kind}(({kind}))" for section, kind in edges]
    lines += ["```", "", "| where in atlas.yaml | must be | names now |", "|---|---|---:|"]
    lines += [
        f"| `{row['at']}` | {row['is']} | {sum(1 for _ in resolve_path(data, str(row['at']).split('/')))} |"
        for row in rows
    ]
    return "\n".join(lines)
