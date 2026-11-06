#!/usr/bin/env python3
"""Dead harness code: a top-level function or class that nothing in the tree names but its own definition.

WHY (3.14.0). The contract refused dead files, dead links and unowned instruments, and was blind to a dead
SYMBOL: a function every caller of which was deleted still reads as a capability to the next agent that
greps for it — the refuted-implementation trap, one level down. A name that appears once in the whole
tracked tree (its `def`) has no caller, no test, no doc and no dispatch. It is deleted, or its reason for
living is declared in atlas.yaml/orphan_exemptions — never silently kept.

A test is not a caller. A function only its own test calls passes the word count and ships nothing, and a
module nothing imports or runs is the same thing at file size. Both are found here from the parsed code, so a
name in a comment or a doc keeps nothing alive. A method is not judged here: a class is used or it is not.
A string that is only a name or holds a `x.py` path counts as a reach, because that is how a table dispatches,
so a module named only that way passes: the guard errs toward keeping, never toward a false refusal.

The reverse edge is here too: a name in backticks that no code defines is a stale pointer. `stale_names` reads
comments, docstrings and docs, and a paths twin of it already runs in `generated_errors`.

WHAT IT DOES NOT SEE: a name built at run time (getattr on an f-string) is invisible to a text search, so
such a name is an exemption WITH its reason, which is the point: the indirection is written down.
"""

from __future__ import annotations

import ast
import hashlib
import re
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

from atlascore import ROOT, atlas, parsed_python, tracked, walked
from importgraph import statement_imports

TEXT = (".py", ".yaml", ".yml", ".md", ".json", ".toml", ".txt", ".sh")


WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
DISPATCHED = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:[.:][A-Za-z_][A-Za-z0-9_]*)*")
IMPORTED_NAME = re.compile(r"[a-z_][a-z0-9_]*")
SCRIPT_PATH = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\.py\b")
RUNS_CODE = (
    "atlas.yaml",
    "pyproject.toml",
    "action.yml",
    "install.sh",
    "Makefile",
    "ci/",
    "config/",
    "hooks/",
    ".github/",
    ".githooks/",
    ".claude/",
    "models/",
)
TEST_SIDE = {"edges", "conftest"}
EXEMPTIONS = re.compile(r"^orphan_exemptions:.*?(?=^\S)", re.M | re.S)
DOC_OWNERS = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
SPAN = re.compile(r"`([^`\n]+)`")
DOTTED_SPAN = re.compile(r"([a-z_][a-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)(?:\(.*\))?")
SNAKE_SPAN = re.compile(r"([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?:\(.*\))?")
FILE_KINDS = {"py", "sh", "yaml", "yml", "md", "json", "toml", "txt"}
# Each of these speaks another tool's words: a language's own API, a system's own terms, a host's own tools.
NAMES_OF_OTHERS = ("languages/", "docs/systems/", "skills/system/")


_WORDS: dict[bytes, list[str]] = {}


def _words(rel: str, text: str) -> list[str]:
    """The names a file USES, CACHED BY CONTENT (3.51.0: the planted suite ran this over every file once
    per case, while a case changes one file — 14% of a warm check). The key holds the path and the text."""
    key = hashlib.blake2b(f"{rel}\0{text}".encode(), digest_size=16).digest()
    if key not in _WORDS:
        _WORDS[key] = _uncached_words(rel, text)
    return _WORDS[key]


def _uncached_words(rel: str, text: str) -> list[str]:
    """A comment or docstring that mentions a name is not a caller (3.50.0:
    an argument_report in agentpolicy lived on an atlas.yaml comment claiming it ran) — so Python is read by
    its syntax tree, and a `#` line elsewhere is dropped. A string literal still counts: dispatch by name."""
    if not rel.endswith(".py"):
        return WORD.findall("\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#")))
    tree = parsed_python(text, rel)
    if tree is None:
        return WORD.findall(text)
    docs: set[int] = set()  # ONE walk: breadth-first reaches a docstring's owner before the docstring
    out: list[str] = []
    for n in walked(tree):
        if (
            isinstance(n, DOC_OWNERS)
            and n.body
            and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)
        ):
            docs.add(id(n.body[0].value))
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs:
            out += WORD.findall(n.value)
        else:
            out += [
                v for v in (getattr(n, f, None) for f in ("id", "attr", "name", "asname", "arg")) if isinstance(v, str)
            ]
    return out


def orphans(sources: dict[str, str] | None = None) -> list[str]:
    """`module.name` for each top-level def/class named exactly once across the tree (its definition)."""
    if sources is None:
        sources = {
            str(p.relative_to(ROOT)): p.read_text(encoding="utf-8", errors="ignore")
            for p in tracked()
            if p.suffix in TEXT and p.is_file()
        }
    counts: dict[str, int] = {}
    for word in (w for rel, text in sources.items() for w in _words(rel, text)):
        counts[word] = counts.get(word, 0) + 1
    found = []
    for rel, text in sorted(sources.items()):
        if not (rel.startswith("scripts/") and rel.endswith(".py")):
            continue
        tree = parsed_python(text, rel)
        for node in tree.body if tree else ():  # one that does not parse is atlas.parse_errors' finding, never a crash
            name = getattr(node, "name", None)
            if (
                name
                and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and name != "main"
                and not name.startswith("__")
                and counts.get(name, 0) <= 1
            ):
                found.append(f"{rel[len('scripts/') : -3]}.{name}")
    return found


def _is_test_side(rel: str) -> bool:
    stem = Path(rel).stem
    return stem.endswith("_test") or stem in TEST_SIDE


def _runs_code(rel: str) -> bool:
    """A file that starts code by name. A guide that names a script starts nothing."""
    return rel.startswith(RUNS_CODE) and not rel.endswith(".md")


def _names_used(node: ast.AST, skip: str = "") -> Iterator[str]:
    """Every name this code reads, a string that is only a name (how a dispatch table holds a function), and
    the original of a renamed import (`import x as y` reads x under another name). `from m import x as x` only
    re-exports, so it reads nothing: a re-export nobody takes must not keep x alive."""
    for sub in walked(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
            found = sub.id
        elif isinstance(sub, ast.Attribute):
            found = sub.attr
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str) and DISPATCHED.fullmatch(sub.value):
            found = re.split(r"[.:]", sub.value)[-1]
        elif isinstance(sub, ast.alias) and sub.asname and sub.asname != sub.name:
            found = sub.name
        else:
            continue
        if found != skip:
            yield found


def _shipped_modules(sources: dict[str, str]) -> Iterator[tuple[str, ast.Module]]:
    for rel, text in sorted(sources.items()):
        if rel.startswith("scripts/") and rel.endswith(".py") and not _is_test_side(rel):
            tree = parsed_python(text, rel)
            if tree:
                yield rel, tree


def tested_only(sources: dict[str, str]) -> list[str]:
    """`module.name` for each shipped top-level def or class that no shipped code uses. A definition does not
    use itself, and a decorated one is registered by its decorator."""
    modules = list(_shipped_modules(sources))
    used = {name for _, tree in modules for node in tree.body for name in _names_used(node, getattr(node, "name", ""))}
    used.update(word for rel, text in sources.items() if _runs_code(rel) for word in _words(rel, text))
    return [
        f"{rel[len('scripts/') : -3]}.{node.name}"
        for rel, tree in modules
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name != "main"
        and not node.name.startswith("__")
        and not node.decorator_list
        and node.name not in used
    ]


def _reaches(tree: ast.Module) -> set[str]:
    """The modules one module imports, or names as a path in a string it could run."""
    found: set[str] = set()
    for sub in walked(tree):
        if names := statement_imports(sub, relative=True):
            found.update(name.split(".")[0] for name in names)
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            found.update(SCRIPT_PATH.findall(sub.value))
            if IMPORTED_NAME.fullmatch(sub.value):
                found.add(sub.value)
    return found


def unreached(sources: dict[str, str], declared: Iterable[str] = ()) -> list[str]:
    """Each shipped module no path reaches from what starts code: a declared instrument, or a file that runs one."""
    graph = {Path(rel).stem: _reaches(tree) for rel, tree in _shipped_modules(sources)}
    stack = [Path(script).stem for script in declared]
    for rel, text in sources.items():
        if _runs_code(rel) and rel != "atlas.yaml":
            stack += SCRIPT_PATH.findall(text)
    seen: set[str] = set()
    while stack:
        stem = stack.pop()
        if stem not in seen:
            seen.add(stem)
            stack += graph.get(stem, ())
    return sorted(set(graph) - seen)


def _tree_sources() -> dict[str, str]:
    """The tree's text, less the list of exemptions: naming a symbol there must not read as using it."""
    sources = {
        str(p.relative_to(ROOT)): p.read_text(encoding="utf-8", errors="ignore")
        for p in tracked()
        if p.is_file() and (p.suffix in TEXT or str(p.relative_to(ROOT)).startswith(RUNS_CODE))
    }
    if "atlas.yaml" in sources:
        sources["atlas.yaml"] = EXEMPTIONS.sub("", sources["atlas.yaml"])
    return sources


def stale_names(sources: dict[str, str]) -> list[str]:
    """`file:line span` for each name in backticks that no code defines: the reverse of an orphan, a pointer
    with nothing at its far end. Backticks claim a live name, so history that names a removed one is plain words.
    A code span in a string literal is that literal's own word, so a whole file can be read without parsing it."""
    code = {rel: _words(rel, text) for rel, text in sources.items() if not rel.endswith(".md")}
    modules = {Path(rel).stem: set(w) for rel, w in code.items() if rel.startswith("scripts/") and rel.endswith(".py")}
    known = {word for words in code.values() for word in words} | {Path(rel).stem for rel in sources}

    def dead(span: str) -> bool:
        if dotted := DOTTED_SPAN.fullmatch(span):
            return dotted[1] in modules and dotted[2] not in FILE_KINDS and dotted[2] not in modules[dotted[1]]
        snake = SNAKE_SPAN.fullmatch(span)
        return bool(snake) and snake[1] not in known

    return [
        f"{rel}:{text.count(chr(10), 0, m.start()) + 1} {m[1]}"
        for rel, text in sorted(sources.items())
        if rel.endswith((".py", ".md", ".yaml")) and not rel.startswith(NAMES_OF_OTHERS)
        for m in SPAN.finditer(text)
        if dead(m[1].strip())
    ]


def _declared_scripts() -> list[str]:
    return [i["script"] for i in (atlas().get("instruments") or {}).values() if isinstance(i, dict) and i.get("script")]


def orphan_errors() -> list[str]:
    sources = _tree_sources()
    exempt = atlas().get("orphan_exemptions") or {}
    words = orphans({rel: text for rel, text in sources.items() if rel.endswith(TEXT)})
    tests = [o for o in tested_only(sources) if o not in words]
    modules = [f"scripts/{stem}.py" for stem in unreached(sources, _declared_scripts())]
    found = {*words, *tests, *modules}
    errors = [
        f"{o} is defined and named nowhere else — delete it, or declare why it lives in orphan_exemptions"
        for o in words
        if o not in exempt
    ]
    errors += [
        f"{o} is called by its tests and by nothing that ships — delete both, or declare why in orphan_exemptions"
        for o in tests
        if o not in exempt
    ]
    errors += [
        f"{o} is reached by nothing that ships — delete it, or declare why in orphan_exemptions"
        for o in modules
        if o not in exempt
    ]
    errors += [
        f"{o}: no code defines this name; correct it, or tell the history in plain words" for o in stale_names(sources)
    ]
    errors += [f"orphan_exemptions/{k} names no reason" for k, why in exempt.items() if not str(why or "").strip()]
    errors += [f"orphan_exemptions/{k} is no longer dead — remove the exemption" for k in exempt if k not in found]
    return errors


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):  # a script with no parser would RUN on --help
        print((__doc__ or sys.argv[0]).strip())
        sys.exit(0)
    found = orphans()
    print("\n".join(found) or "no orphaned harness symbol")
    print(f"orphans: {len(found)} symbol(s) named only by their own definition")
    sys.exit(1 if orphan_errors() else 0)
