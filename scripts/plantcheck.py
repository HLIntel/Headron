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
import re
import sys

from atlascore import ROOT, parsed_python, walked


def suites() -> list[str]:
    """Every planted suite, DERIVED from the tree rather than named.

    SIGHTED ON THIS FILE at 3.31.0: the roster was the literal pair
    ("scripts/atlas_test.py", "scripts/atlas_guards_test.py"). A suite split out to stay under the line
    cap was therefore invisible, and the anchor count silently FELL from 78 to 76 while printing a clean
    pass — a roster of enumerated names narrows the moment a sibling is added beside it, which is the
    exact shape this file exists to catch in someone else's code (code-quality §8).

    A suite is any `scripts/*_test.py` that calls `mutated(`: the capability, not the name.
    """
    return sorted(
        str(p.relative_to(ROOT))
        for p in (ROOT / "scripts").glob("*_test.py")
        if "mutated(" in p.read_text(encoding="utf-8")
    )


def anchors() -> list[tuple[str, str, str]]:
    """(suite, target file, anchor text) for every `mutated(<file>, lambda s: s.replace(<anchor>, ...))`.

    Read from the syntax tree, never a regular expression over the source: an anchor is a Python string
    literal that may be implicitly concatenated across lines, and a regex reading one line finds a
    fragment of it and then reports a mismatch that is its own.
    """
    found: list[tuple[str, str, str]] = []
    for rel in suites():
        tree = parsed_python((ROOT / rel).read_text(encoding="utf-8"), rel) or ast.Module([], [])
        for node in walked(tree):
            if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "mutated"):
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            target = node.args[0].value
            for sub in walked(node):
                if (
                    isinstance(sub, ast.Call)
                    and getattr(sub.func, "attr", "") == "replace"
                    and sub.args
                    and isinstance(sub.args[0], ast.Constant)
                    and isinstance(sub.args[0].value, str)
                ):
                    found.append((rel, target, sub.args[0].value))
        found += _table_anchors(rel, tree) + _read_anchors(rel, tree)
    return found


def _table_anchors(rel: str, tree: ast.AST) -> list[tuple[str, str, str]]:
    """Anchors a plant TABLE feeds through a loop: `for name, ..., old, new, needle in plants:` wrapping
    `mutated(<file>, lambda s, o=old: s.replace(o, ...))`. MEASURED at 3.44.0: a stale anchor in such a
    table passed `thea check` and died only in the full suite, because the literal is in the table, not
    in the call — the one shape of plant this checker had never read."""
    found = []
    # SIGHTED at 3.53.0: DECLARATION_PLANTS is a MODULE-level annotated list whose rows carry the file too
    # (`mutated(where, ...)`), and both shapes were invisible — `routes: 36` outlived its text silently.
    module = _tables(tree.body if isinstance(tree, ast.Module) else [])
    for func in (n for n in walked(tree) if isinstance(n, ast.FunctionDef)):
        tables = {**module, **_tables(walked(func))}
        for loop in (
            n
            for n in walked(func)
            if isinstance(n, ast.For)
            and isinstance(n.iter, ast.Name)
            and n.iter.id in tables
            and isinstance(n.target, ast.Tuple)
        ):
            names = [getattr(e, "id", "") for e in loop.target.elts]
            for call in (
                n
                for n in walked(loop)
                if isinstance(n, ast.Call)
                and getattr(n.func, "id", "") == "mutated"
                and n.args
                and (isinstance(n.args[0], ast.Constant) or getattr(n.args[0], "id", "") in names)
            ):
                bound = {
                    a.arg: getattr(d, "id", "")
                    for lam in walked(call)
                    if isinstance(lam, ast.Lambda)
                    for a, d in zip(
                        lam.args.args[-len(lam.args.defaults) :] if lam.args.defaults else [], lam.args.defaults
                    )
                }
                for sub in walked(call):
                    if (
                        isinstance(sub, ast.Call)
                        and getattr(sub.func, "attr", "") == "replace"
                        and sub.args
                        and isinstance(sub.args[0], ast.Name)
                    ):
                        name = bound.get(sub.args[0].id, sub.args[0].id)
                        if name in names:
                            found += [
                                (rel, _target(call.args[0], names, row), row.elts[names.index(name)].value)
                                for row in tables[loop.iter.id].elts
                                if isinstance(row, ast.Tuple)
                                and isinstance(row.elts[names.index(name)], ast.Constant)
                                and _target(call.args[0], names, row)
                            ]
    return found


def _tables(nodes) -> dict:
    """Every `NAME = [...]` or `NAME: T = [...]` list among `nodes`, by name."""
    return {
        a.target.id if isinstance(a, ast.AnnAssign) else a.targets[0].id: a.value
        for a in nodes
        if isinstance(a, (ast.Assign, ast.AnnAssign))
        and isinstance(a.target if isinstance(a, ast.AnnAssign) else a.targets[0], ast.Name)
        and isinstance(a.value, ast.List)
    }


def _target(arg: ast.AST, names: list[str], row: ast.Tuple) -> str | None:
    """The file a plant mutates: a literal in the call, or the row's own column the loop binds it to."""
    if isinstance(arg, ast.Constant):
        return arg.value
    cell = row.elts[names.index(arg.id)] if getattr(arg, "id", "") in names else None
    return cell.value if isinstance(cell, ast.Constant) and isinstance(cell.value, str) else None


def _read_anchors(rel: str, tree: ast.AST) -> list[tuple[str, str, str]]:
    """Anchors a case LOCATES by quoting a file: `text = (ROOT / "<file>").read_text()` then `text.index("<quote>")`.
    SIGHTED at 3.46.0: a README rewrite deleted the sentence a redundancy case quoted, and the full suite died
    on `ValueError: substring not found` after a clean `thea check` — the quote was never read as an anchor."""
    found = []
    for func in (n for n in walked(tree) if isinstance(n, ast.FunctionDef)):
        files = {}
        for a in (n for n in walked(func) if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)):
            call = a.value
            if (
                isinstance(call, ast.Call)
                and getattr(call.func, "attr", "") == "read_text"
                and _read_target(call.func.value)
            ):
                files[a.targets[0].id] = _read_target(call.func.value)
        for call in (n for n in walked(func) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "index"):
            owner = getattr(call.func.value, "id", "")
            if (
                owner in files
                and call.args
                and isinstance(call.args[0], ast.Constant)
                and isinstance(call.args[0].value, str)
            ):
                found.append((rel, files[owner], call.args[0].value))
        # A REGEX that LOCATES an anchor is one too (3.50.0, twice): `re.search(<pattern>, <file text>).group`
        # died with AttributeError minutes into the suite when an edit moved the text it was looking for.
        for call in (
            n
            for n in walked(func)
            if isinstance(n, ast.Call)
            and getattr(n.func, "attr", "") in ("search", "match")
            and getattr(n.func.value, "id", "") == "re"
            and len(n.args) > 1
            and isinstance(n.args[0], ast.Constant)
        ):
            src = call.args[1]
            target = files.get(getattr(src, "id", "")) or (
                _read_target(src.func.value)
                if isinstance(src, ast.Call) and getattr(src.func, "attr", "") == "read_text"
                else None
            )
            if target:
                flags = sum(
                    getattr(re, a.attr, 0) for x in call.args[2:] for a in walked(x) if isinstance(a, ast.Attribute)
                )
                found.append((rel, target, re.compile(call.args[0].value, flags)))
    return found


def hits(text: str, anchor: str | re.Pattern) -> int:
    """How often one anchor matches: a literal by count, a regex-located one by its matches. EVERY reader of
    anchors() counts through here — a second reader assuming str crashed the suite the day patterns joined."""
    return len(anchor.findall(text)) if isinstance(anchor, re.Pattern) else text.count(anchor)


def _read_target(node: ast.AST) -> str | None:
    """`ROOT / "<file>"` → the file, or None."""
    return str(node.right.value) if isinstance(node, ast.BinOp) and isinstance(node.right, ast.Constant) else None


def plant_anchor_errors(rows: list[tuple[str, str, str]] | None = None) -> list[str]:
    """plants_can_still_apply — an anchor that matches nothing is refused, and an empty roster is too.
    Each target is read ONCE however many anchors it carries."""
    errors: list[str] = []
    rows = anchors() if rows is None else rows
    texts: dict[str, str | None] = {}
    for suite, target, anchor in rows:
        if target not in texts:
            texts[target] = (ROOT / target).read_text(encoding="utf-8") if (ROOT / target).exists() else None
        if texts[target] is None:
            errors.append(f"{suite}: plants into {target}, which does not exist")
            continue
        if not hits(texts[target], anchor):
            errors.append(
                f"{suite}: a mutation anchor matches NOTHING in {target} — {getattr(anchor, 'pattern', anchor)[:60]!r}. "
                f"Re-anchor it on the current text; a plant that applies to nothing leaves "
                f"the rule it tests unproven while the case still passes."
            )
    if not rows:
        errors.append(
            "plants_can_still_apply found no mutation anchor at all — the roster has stopped "
            "describing the suites, and an empty pass prints like a clean one"
        )
    return errors


def main() -> int:
    """Coverage beside the refusal count: 0 of 0 and 0 of 77 print the same 0."""
    rows = anchors()
    errors = plant_anchor_errors(rows)
    for line in errors:
        print(f"- {line}")
    print(f"{len(errors)} findings over {len(rows)} mutation anchors in {len(suites())} planted suite(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
