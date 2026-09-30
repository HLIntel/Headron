#!/usr/bin/env python3
"""plants_can_still_apply: every mutation anchor in the planted suites still matches the file it aims at.

WHY (3.28.0). A planted defect is the only reason to believe a rule bites. When an anchor stops matching
— because the text it quoted was edited — the suite does not report a missing rule; it either crashes
mid-run with the tree mutated, or (worse, and sighted here) the plant silently applies to nothing and the
case passes while the rule it tests is unproven. The same shape has now cost four separate debugging
rounds in this repository: `install_writes`, `unit_tests: {role: test}`, a `*.log` glob that matched a
different line first, and a quoted sentence that was rewritten.

The cure is not more care. It is reading the anchors STATICALLY, in under a second, instead of finding
out five minutes into a mutating suite: this file parses both suites with `ast` and counts each anchor
in its target.

ZERO is the only defect. Several matches is the deliberate, documented form — `s.replace(x, y, 1)`
mutates the FIRST occurrence on purpose, and a rule refusing that would fire on correct code and be
switched off. Run `python scripts/plantcheck.py` for the current counts; it prints the anchor total and
the number of suites beside every verdict, so a clean pass is never read as full coverage.
"""
from __future__ import annotations

import ast
import sys

from atlascore import ROOT


def suites() -> list[str]:
    """Every planted suite, DERIVED from the tree rather than named.

    SIGHTED ON THIS FILE at 3.31.0: the roster was the literal pair
    ("scripts/atlas_test.py", "scripts/atlas_guards_test.py"). A suite split out to stay under the line
    cap was therefore invisible, and the anchor count silently FELL from 78 to 76 while printing a clean
    pass — a roster of enumerated names narrows the moment a sibling is added beside it, which is the
    exact shape this file exists to catch in someone else's code (code-quality §8).

    A suite is any `scripts/*_test.py` that calls `mutated(`: the capability, not the name.
    """
    return sorted(str(p.relative_to(ROOT)) for p in (ROOT / "scripts").glob("*_test.py")
                  if "mutated(" in p.read_text(encoding="utf-8"))


def anchors() -> list[tuple[str, str, str]]:
    """(suite, target file, anchor text) for every `mutated(<file>, lambda s: s.replace(<anchor>, ...))`.

    Read from the syntax tree, never a regular expression over the source: an anchor is a Python string
    literal that may be implicitly concatenated across lines, and a regex reading one line finds a
    fragment of it and then reports a mismatch that is its own.
    """
    found: list[tuple[str, str, str]] = []
    for rel in suites():
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "mutated"):
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            target = node.args[0].value
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and getattr(sub.func, "attr", "") == "replace" \
                        and sub.args and isinstance(sub.args[0], ast.Constant) \
                        and isinstance(sub.args[0].value, str):
                    found.append((rel, target, sub.args[0].value))
        found += _table_anchors(rel, tree) + _read_anchors(rel, tree)
    return found


def _table_anchors(rel: str, tree: ast.AST) -> list[tuple[str, str, str]]:
    """Anchors a plant TABLE feeds through a loop: `for name, ..., old, new, needle in plants:` wrapping
    `mutated(<file>, lambda s, o=old: s.replace(o, ...))`. MEASURED at 3.44.0: a stale anchor in such a
    table passed `thea check` and died only in the full suite, because the literal is in the table, not
    in the call — the one shape of plant this checker had never read."""
    found = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        tables = {a.targets[0].id: a.value for a in ast.walk(func) if isinstance(a, ast.Assign)
                  and isinstance(a.targets[0], ast.Name) and isinstance(a.value, ast.List)}
        for loop in (n for n in ast.walk(func) if isinstance(n, ast.For) and isinstance(n.iter, ast.Name)
                     and n.iter.id in tables and isinstance(n.target, ast.Tuple)):
            names = [getattr(e, "id", "") for e in loop.target.elts]
            for call in (n for n in ast.walk(loop) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "mutated"
                         and n.args and isinstance(n.args[0], ast.Constant)):
                bound = {a.arg: getattr(d, "id", "") for lam in ast.walk(call) if isinstance(lam, ast.Lambda)
                         for a, d in zip(lam.args.args[-len(lam.args.defaults):] if lam.args.defaults else [], lam.args.defaults)}
                for sub in ast.walk(call):
                    if isinstance(sub, ast.Call) and getattr(sub.func, "attr", "") == "replace" and sub.args \
                            and isinstance(sub.args[0], ast.Name):
                        name = bound.get(sub.args[0].id, sub.args[0].id)
                        if name in names:
                            found += [(rel, call.args[0].value, row.elts[names.index(name)].value)
                                      for row in tables[loop.iter.id].elts if isinstance(row, ast.Tuple)
                                      and isinstance(row.elts[names.index(name)], ast.Constant)]
    return found


def _read_anchors(rel: str, tree: ast.AST) -> list[tuple[str, str, str]]:
    """Anchors a case LOCATES by quoting a file: `text = (ROOT / "<file>").read_text()` then `text.index("<quote>")`.
    SIGHTED at 3.46.0: a README rewrite deleted the sentence a redundancy case quoted, and the full suite died
    on `ValueError: substring not found` after a clean `thea check` — the quote was never read as an anchor."""
    found = []
    for func in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        files = {}
        for a in (n for n in ast.walk(func) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)):
            call = a.value
            if isinstance(call, ast.Call) and getattr(call.func, "attr", "") == "read_text" \
                    and isinstance(call.func.value, ast.BinOp) and isinstance(call.func.value.right, ast.Constant):
                files[a.targets[0].id] = str(call.func.value.right.value)
        for call in (n for n in ast.walk(func) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "index"):
            owner = getattr(call.func.value, "id", "")
            if owner in files and call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
                found.append((rel, files[owner], call.args[0].value))
    return found


def plant_anchor_errors() -> list[str]:
    """plants_can_still_apply — an anchor that matches nothing is refused, and an empty roster is too."""
    errors: list[str] = []
    rows = anchors()
    for suite, target, anchor in rows:
        path = ROOT / target
        if not path.exists():
            errors.append(f"{suite}: plants into {target}, which does not exist")
            continue
        if path.read_text(encoding="utf-8").count(anchor) == 0:
            errors.append(f"{suite}: a mutation anchor matches NOTHING in {target} — {anchor[:60]!r}. "
                          f"Re-anchor it on the current text; a plant that applies to nothing leaves "
                          f"the rule it tests unproven while the case still passes.")
    if not rows:
        errors.append("plants_can_still_apply found no mutation anchor at all — the roster has stopped "
                      "describing the suites, and an empty pass prints like a clean one")
    return errors


def main() -> int:
    """Coverage beside the refusal count: 0 of 0 and 0 of 77 print the same 0."""
    rows, errors = anchors(), plant_anchor_errors()
    for line in errors:
        print(f"- {line}")
    print(f"{len(errors)} findings over {len(rows)} mutation anchors in {len(suites())} planted suite(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
