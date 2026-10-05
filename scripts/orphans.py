#!/usr/bin/env python3
"""Dead harness code: a top-level function or class that nothing in the tree names but its own definition.

WHY (3.14.0). The contract refused dead files, dead links and unowned instruments, and was blind to a dead
SYMBOL: a function every caller of which was deleted still reads as a capability to the next agent that
greps for it — the refuted-implementation trap, one level down. A name that appears once in the whole
tracked tree (its `def`) has no caller, no test, no doc and no dispatch. It is deleted, or its reason for
living is declared in atlas.yaml/orphan_exemptions — never silently kept.

WHAT IT DOES NOT SEE: a name built at run time (getattr on an f-string) is invisible to a text search, so
such a name is an exemption WITH its reason, which is the point: the indirection is written down.
"""
from __future__ import annotations

import ast
import re
import sys

from atlascore import ROOT, atlas, tracked

TEXT = (".py", ".yaml", ".yml", ".md", ".json", ".toml", ".txt", ".sh")


WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
DOC_OWNERS = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _words(rel: str, text: str) -> list[str]:
    """The names a file USES. A comment or docstring that mentions a name is not a caller (3.50.0:
    `agentpolicy.argument_report` lived on an atlas.yaml comment claiming it ran) — so Python is read by
    its syntax tree, and a `#` line elsewhere is dropped. A string literal still counts: dispatch by name."""
    if not rel.endswith(".py"):
        return WORD.findall("\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#")))
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return WORD.findall(text)
    docs = {id(n.body[0].value) for n in ast.walk(tree) if isinstance(n, DOC_OWNERS) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    out: list[str] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            out += WORD.findall(n.value)
        else:
            out += [v for v in (getattr(n, f, None) for f in ("id", "attr", "name", "asname", "arg")) if isinstance(v, str)]
    return out


def orphans(sources: dict[str, str] | None = None) -> list[str]:
    """`module.name` for each top-level def/class named exactly once across the tree (its definition)."""
    if sources is None:
        sources = {str(p.relative_to(ROOT)): p.read_text(encoding="utf-8", errors="ignore")
                   for p in tracked() if p.suffix in TEXT and p.is_file()}
    counts: dict[str, int] = {}
    for word in (w for rel, text in sources.items() for w in _words(rel, text)):
        counts[word] = counts.get(word, 0) + 1
    found = []
    for rel, text in sorted(sources.items()):
        if not (rel.startswith("scripts/") and rel.endswith(".py")):
            continue
        try:
            body = ast.parse(text).body
        except SyntaxError:
            continue  # a file that does not parse is atlas.parse_errors' finding, reported first — never a crash here
        for node in body:
            name = getattr(node, "name", None)
            if name and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and name != "main" and not name.startswith("__") and counts.get(name, 0) <= 1:
                found.append(f"{rel[len('scripts/'):-3]}.{name}")
    return found


def orphan_errors() -> list[str]:
    exempt, found = atlas().get("orphan_exemptions") or {}, orphans()
    errors = [f"{o} is defined and named nowhere else — delete it, or declare why it lives in orphan_exemptions"
              for o in found if o not in exempt]
    errors += [f"orphan_exemptions/{k} names no reason" for k, why in exempt.items() if not str(why or "").strip()]
    errors += [f"orphan_exemptions/{k} is no longer an orphan — remove the exemption" for k in exempt if k not in found]
    return errors


if __name__ == "__main__":
    found = orphans()
    print("\n".join(found) or "no orphaned harness symbol")
    print(f"orphans: {len(found)} symbol(s) named only by their own definition")
    sys.exit(1 if orphan_errors() else 0)
