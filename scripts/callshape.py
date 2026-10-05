#!/usr/bin/env python3
"""forbidden_calls_are_refused: "no module outside X may call Y" is a declared ROW, not a function.

WHY (3.31.0). Three guards in this tree were the same guard: `bare_sleep_errors` and
`yaml_bypass_errors` measured 0.859 similar after AST normalisation, with `subprocess_timeout_errors`
at 0.67 (measured at 3.31.0, by difflib over normalised syntax trees). Each walked a roster of Python sources, skipped an owner file, and matched
`Call -> Attribute` on a `Name` in an alias set with `attr` in a name set. `allowed_duplicate_structures: 0`
missed all three because it requires AST IDENTITY, and these differed only in their literals.

Three copies of one rule is three places for it to drift, and the copies HAD drifted: one exempted
test harnesses by suffix, one exempted a single file, one exempted nothing; two swept `scripts/` and
`fuzz/`, the third only `scripts/`. Two constants that agree because someone typed the same digit
disagree the first time one is edited, and so do two copies of a predicate.

SO THE LOGIC LIVES ONCE AND THE RULES ARE DATA. A new "nothing may call X" rule is now a row in
atlas.yaml/forbidden_calls, reviewed like the declaration it is, and it cannot be added without a
planted case: `forbidden_call_coverage_errors` refuses a row no case exercises, which is how the
denied_commands floor is already held.

WHAT IT DOES NOT PROVE. That the call is wrong at that line — only that it is reachable where the
declaration says it must not be. An exemption carries its reason in the ROW, never in this file, so
the reason travels with the rule instead of ageing in code nobody reads.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

from atlascore import ROOT, atlas, parsed_python, walked


def rules() -> dict:
    """The declared rows. Empty is a defect, not a clean pass."""
    return dict(atlas().get("forbidden_calls") or {})


def _sources(roster: list) -> list:
    """Every Python source in the declared directories, sorted so findings are stable."""
    found = []
    for directory in roster or []:
        found += sorted((ROOT / str(directory)).glob("*.py"))
    return sorted(found)


def _row(rule: dict) -> tuple:
    """A row reduced to what the walk needs, so the declaration is read once and not per file."""
    return ({str(a) for a in rule.get("aliases") or []},
            {str(a) for a in rule.get("attrs") or []},
            {str(f) for f in rule.get("exempt_files") or []},
            str(rule.get("exempt_suffix") or ""),
            str(rule.get("requires_keyword") or ""))


def matches(name: str, rule: dict) -> list[tuple[str, int]]:
    """(path, line) for every call this row forbids. Kept for callers that want one row's findings."""
    return findings({name: rule}).get(name, [])


def findings(rules_by_name: dict) -> dict[str, list[tuple[str, int]]]:
    """name -> [(path, line)] for every row, from ONE parse and ONE walk per file.

    MEASURED at 3.34.0: the per-row version parsed every source once per row — three rows, three full
    passes, 0.89s of a 4.37s contract run. The rows differ only in which names they match, and that is a
    set lookup on a node the walk already holds, so the file is parsed once, walked once, and every row
    is decided on the way past. The tree itself comes from the content-addressed cache, so an instrument
    that already parsed it does not parse it again.

    The AST is the identity, never a regular expression over the line: `subprocess.run(x, timeout=1)` and
    `subprocess.run(x)  # timeout=1` differ only in the tree.
    """
    prepared = {name: _row(rule) for name, rule in rules_by_name.items()}
    out: dict[str, list[tuple[str, int]]] = {name: [] for name in prepared}
    by_source: dict[str, set[str]] = {}
    for name, rule in rules_by_name.items():
        for source in _sources(rule.get("roster") or []):
            by_source.setdefault(str(source), set()).add(name)
    for path, names in sorted(by_source.items()):
        source = Path(path)
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        tree = parsed_python(text, path)
        if tree is None:
            continue  # a file that does not parse is the parse check's finding, never this one's
        rel_name = source.name
        active = [(n, *prepared[n]) for n in names
                  if rel_name not in prepared[n][2]
                  and not (prepared[n][3] and rel_name.endswith(prepared[n][3]))]
        if not active:
            continue
        for node in walked(tree):
            function = getattr(node, "func", None)
            if not (isinstance(node, ast.Call) and isinstance(function, ast.Attribute)
                    and isinstance(function.value, ast.Name)):
                continue
            for name, aliases, attrs, _files, _suffix, needs in active:
                if function.value.id not in aliases or function.attr not in attrs:
                    continue
                if needs and any(k.arg == needs for k in node.keywords):
                    continue  # the row forbids the call only when it OMITS this keyword
                out[name].append((str(source.relative_to(ROOT)), node.lineno))
    return out


def forbidden_call_errors() -> list[str]:
    """forbidden_calls_are_refused — every declared row, over the roster the row itself names."""
    errors: list[str] = []
    declared = rules()
    hits = findings(declared) if declared else {}
    if not declared:
        return ["forbidden_calls declares no row at all — three rules were folded into this table, "
                "so an empty one means the declaration was lost, not that the tree is clean"]
    for name, rule in sorted(declared.items()):
        if not (rule.get("aliases") and rule.get("attrs") and rule.get("roster")):
            errors.append(f"forbidden_calls/{name} must name aliases, attrs and a roster; a row "
                          f"missing any of them matches nothing and reads as enforcement")
            continue
        if (rule.get("exempt_files") or rule.get("exempt_suffix")) and not rule.get("exempt_reason"):
            errors.append(f"forbidden_calls/{name} exempts something and states no exempt_reason — "
                          f"an exemption without its reason inline is a snooze button")
        errors += [f"{path}:{line} {rule.get('message') or f'is forbidden by forbidden_calls/{name}'}"
                   for path, line in (hits.get(name) or [])]
    return errors


_ABSENCE_PREDICATES = {"exists", "is_file", "is_dir"}


def _tests_absence(test: ast.expr) -> bool:
    """`not <path>.exists()` (or is_file / is_dir) — the branch taken when the input is not there."""
    return (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not)
            and isinstance(test.operand, ast.Call) and isinstance(test.operand.func, ast.Attribute)
            and test.operand.func.attr in _ABSENCE_PREDICATES)


def _reports_nothing(stmt: ast.stmt) -> bool:
    """`continue`, or a return of nothing: None, 0, False, an empty string or an empty container."""
    if isinstance(stmt, ast.Continue):
        return True
    if not isinstance(stmt, ast.Return):
        return False
    value = stmt.value
    if value is None or (isinstance(value, ast.Constant) and value.value in (None, 0, "", False)):
        return True
    return isinstance(value, (ast.List, ast.Tuple, ast.Set)) and not value.elts \
        or isinstance(value, ast.Dict) and not value.keys


def blind_skips() -> list[tuple[str, str, int]]:
    """(file, function, line) for every guard that answers a MISSING input with a clean result.

    A guard is a hard-invariant check (`_inv_*`) or an error roster (`*_errors`). Test harnesses are out
    of scope: a plant that skips is plantcheck's finding, and a harness skip is not a verdict.
    """
    found: list[tuple[str, str, int]] = []
    for source in _sources(["scripts"]):
        if source.name.endswith("_test.py"):
            continue
        tree = parsed_python(source.read_text(encoding="utf-8"), str(source))
        for function in (n for n in walked(tree or ast.Module(body=[], type_ignores=[]))
                         if isinstance(n, ast.FunctionDef)):
            if not (function.name.startswith("_inv_") or function.name.endswith("_errors")):
                continue
            found += [(source.name, function.name, node.lineno) for node in walked(function)
                      if isinstance(node, ast.If) and _tests_absence(node.test)
                      and len(node.body) == 1 and _reports_nothing(node.body[0])]
    return sorted(found)


def blind_skip_errors() -> list[str]:
    """guards_see_their_input — a guard that skips a missing input names who refuses the absence.

    A check that `continue`s past a file that is not there prints exactly what it prints when the
    file is there and clean, so deleting the input turns the guard into a pass. The skip is kept only
    where atlas.yaml/absent_input_owners names the function that DOES refuse the absence, resolved
    against the tree, or states why absence is the valid state.
    """
    from agentpolicy import _resolves  # noqa: PLC0415 — agentpolicy imports nothing from here
    owners = dict(atlas().get("absent_input_owners") or {})
    errors: list[str] = []
    hits = blind_skips()
    for key in sorted(set(owners) - {f"{f}:{fn}" for f, fn, _ in hits}):
        errors.append(f"absent_input_owners/{key} names a skip that is no longer in the tree — a stale "
                      f"exemption waits for the next guard to borrow it")
    for file, function, line in hits:
        row = owners.get(f"{file}:{function}")
        if not isinstance(row, dict) or not str(row.get("reason") or "").strip():
            errors.append(f"scripts/{file}:{line} {function} passes when its input is missing — refuse the "
                          f"absence, or name its owner in atlas.yaml/absent_input_owners with a reason")
        elif row.get("owned_by") and not _resolves(str(row["owned_by"])):
            errors.append(f"absent_input_owners/{file}:{function} is owned_by {row['owned_by']}, which is "
                          f"not in this tree — a skip whose owner is gone is a blind pass again")
    return errors


def coverage() -> str:
    """The roster size beside the refusal count: 0 of 0 and 0 of many print the same 0."""
    declared = rules()
    swept = {s for rule in declared.values() for s in _sources(rule.get("roster") or [])}
    return f"{len(declared)} forbidden-call row(s) over {len(swept)} Python source(s)"


def main() -> int:
    errors = forbidden_call_errors()
    for line in errors:
        print(f"- {line}")
    print(coverage())
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
