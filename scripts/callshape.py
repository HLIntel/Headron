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

from atlascore import ROOT, atlas


def rules() -> dict:
    """The declared rows. Empty is a defect, not a clean pass."""
    return dict(atlas().get("forbidden_calls") or {})


def _sources(roster: list) -> list:
    """Every Python source in the declared directories, sorted so findings are stable."""
    found = []
    for directory in roster or []:
        found += sorted((ROOT / str(directory)).glob("*.py"))
    return sorted(found)


def matches(name: str, rule: dict) -> list[tuple[str, int]]:
    """(path, line) for every call this row forbids. The AST is the identity; a regex over the line
    cannot tell `subprocess.run(x, timeout=1)` from `subprocess.run(x)  # timeout=1`."""
    aliases = {str(a) for a in rule.get("aliases") or []}
    attrs = {str(a) for a in rule.get("attrs") or []}
    exempt = {str(f) for f in rule.get("exempt_files") or []}
    suffix = str(rule.get("exempt_suffix") or "")
    needs = str(rule.get("requires_keyword") or "")
    found: list[tuple[str, int]] = []
    for source in _sources(rule.get("roster") or []):
        if source.name in exempt or (suffix and source.name.endswith(suffix)):
            continue
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"))
        except SyntaxError:
            continue  # a file that does not parse is the parse check's finding, never this one's
        for node in ast.walk(tree):
            function = getattr(node, "func", None)
            if not (isinstance(node, ast.Call) and isinstance(function, ast.Attribute)
                    and isinstance(function.value, ast.Name)
                    and function.value.id in aliases and function.attr in attrs):
                continue
            if needs and any(k.arg == needs for k in node.keywords):
                continue  # the row forbids the call only when it OMITS this keyword
            found.append((str(source.relative_to(ROOT)), node.lineno))
    return found


def forbidden_call_errors() -> list[str]:
    """forbidden_calls_are_refused — every declared row, over the roster the row itself names."""
    errors: list[str] = []
    declared = rules()
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
                   for path, line in matches(name, rule)]
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
