#!/usr/bin/env python3
"""What this repository HANDS OVER before it is asked anything — measured, and ratcheted.

WHY (2.10.0). Measured on this tree: 159 markdown files, 45% of the bytes. That number alone is
rhetoric in both directions. 78 of those files are language packs no session opens until a route
names one, so "45% prose" describes a library, not a blob — and at the same time nothing here
measured the part that actually costs a reader anything, which is what a runtime loads with no
route resolved and no question asked. An entry path can grow a page at a time while every other
count in this contract stays green.

SO THE INSTRUMENT MEASURES THE ENTRY, NOT THE TREE. Two paths are declared in
`atlas.yaml/context_policy/entry_paths` — what an agent runtime loads automatically, and what a
person opens first — each with a byte budget set to its own measured size. The budget is a
RATCHET: it may fall and never rise, so the only way to add to an entry document is to take
something out of it, and `atlas.py check` refuses a raise rather than leaving it to review.

WHAT IT DOES NOT PROVE: that the bytes on the entry path are the RIGHT bytes. A small entry
document that sends every reader to the wrong place costs more than a large one that routes
correctly, and no byte count can see the difference. That is what the router's own evidence line
and a human reviewer are for.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from atlascore import ROOT, atlas, read, route_for, route_targets, tracked


def tokens(size: int) -> int:
    """The ONE bytes-to-tokens estimate. Two formulas for one number disagreed by a token at 2.28.0
    — the printer floored, a README guard rounded — and each was right by its own lights."""
    return max(size, 0) // 4


def paths() -> dict:
    return ((atlas().get("context_policy") or {}).get("entry_paths")) or {}


def _size(rel_path: object) -> int:
    path = ROOT / str(rel_path)
    return path.stat().st_size if path.exists() else -1


def measure() -> dict[str, dict]:
    """Per declared entry path: its files, their sizes, the total and the budget it is held to."""
    report: dict[str, dict] = {}
    for name, spec in paths().items():
        always = [(str(f), _size(f)) for f in (spec or {}).get("files") or []]
        options = [(str(f), _size(f)) for f in (spec or {}).get("alternatives") or []]
        # `worst_alternative` costs the LARGEST option, not their sum: a runtime reads the one
        # convention it knows. `sum` is for a path where every file really is opened.
        worst = max((size for _, size in options), default=0)
        rows = always + [(f"{f} (one of {len(options)} conventions)", size) for f, size in options]
        report[name] = {
            "files": rows,
            "measure": str((spec or {}).get("measure") or "sum"),
            "bytes": sum(size for _, size in always if size > 0)
                     + (worst if str((spec or {}).get("measure")) == "worst_alternative"
                        else sum(size for _, size in options if size > 0)),
            "budget": int((spec or {}).get("budget_bytes") or 0),
            "slack": int((spec or {}).get("slack_bytes") or 0),
            "raised_for": str((spec or {}).get("raised_for") or ""),
            "why": str((spec or {}).get("why") or ""),
        }
    return report


def lazy_bytes() -> tuple[int, int]:
    """Everything reachable ONLY after a route, so the entry cost has something to be read against."""
    entry = {str(f) for spec in paths().values()
             for f in ((spec or {}).get("files") or []) + ((spec or {}).get("alternatives") or [])}
    total = count = 0
    for path in tracked():
        if path.is_symlink() or not path.is_file() or path.suffix.lower() != ".md":
            continue
        if path.resolve().relative_to(ROOT.resolve()).as_posix() in entry:
            continue
        total += path.stat().st_size
        count += 1
    return total, count


def footprint() -> dict:
    """What an install of the harness weighs: its own modules, and how many things it drags in."""
    declared = ((atlas().get("context_policy") or {}).get("install_footprint")) or {}
    # ONLY WHAT SHIPS. Counting every script made this grow whenever an instrument was added,
    # which measured the repository's verification rather than the consumer's install.
    shipped = set(re.findall(r'"([a-z_][a-z0-9_]*)"', re.search(
        r"py-modules = \[(.*?)\]", read("pyproject.toml"), re.S).group(1)))
    modules = sorted(p for p in (ROOT / "scripts").glob("*.py") if p.stem in shipped)
    requirements = [line.split("#", 1)[0].strip()
                    for line in read("scripts/requirements.txt").splitlines()]
    return {
        "modules": len(modules),
        "development_only": len(list((ROOT / "scripts").glob("*.py"))) - len(modules),
        "bytes": sum(p.stat().st_size for p in modules),
        "dependencies": len([r for r in requirements if r]),
        "declared": declared,
    }


def footprint_errors() -> list[str]:
    """One dependency, bounded bytes, and no slack left lying around for the next import."""
    state = footprint()
    declared = state["declared"]
    errors: list[str] = []
    if not declared:
        return ["context_policy/install_footprint is not declared, so the CLI's weight is bounded "
                "by nothing and arrives one convenient import at a time"]
    if state["dependencies"] != int(declared.get("runtime_dependencies") or -1):
        errors.append(f"the harness declares {declared.get('runtime_dependencies')} runtime "
                      f"dependency/ies and scripts/requirements.txt names {state['dependencies']}")
    ceiling, slack = int(declared.get("module_bytes") or 0), int(declared.get("slack_bytes") or 0)
    if not str(declared.get("raised_for") or "").strip():
        errors.append("context_policy/install_footprint names nothing in raised_for — a ceiling "
                      "that can move without saying what moved it is not a ratchet, it is a number")
    if state["bytes"] > ceiling:
        errors.append(f"the harness is {state['bytes']} bytes against a ceiling of {ceiling} — the "
                      "ratchet only falls; split something out or point at it instead of shipping it")
    elif ceiling - state["bytes"] > slack:
        errors.append(f"the harness measures {state['bytes']} against a ceiling of {ceiling}, "
                      f"{ceiling - state['bytes']} bytes of slack over the declared {slack} — lower "
                      "the ceiling, or the next import is absorbed rather than refused")
    return errors


def example_coverage() -> tuple[list[str], list[str]]:
    """(routes that ship something runnable, routes that ship nothing). Both, always."""
    with_example: set[str] = set()
    for path in (ROOT / "examples").rglob("*"):
        if path.is_file():
            route = route_for(str(path))
            if route:
                with_example.add(route)
    return sorted(with_example), sorted(set(route_targets()) - with_example)


def example_coverage_errors() -> list[str]:
    """The uncovered count may only fall. A pack that ships nothing runnable is DECLARED, not proven."""
    declared = ((atlas().get("context_policy") or {}).get("example_coverage")) or {}
    _, without = example_coverage()
    ceiling = declared.get("routes_without_example")
    if ceiling is None:
        return ["context_policy/example_coverage is not declared, so `exrun` can print a clean "
                "pass over the routes it never looked at — and did"]
    if not str(declared.get("why_not_zero") or "").strip():
        return ["context_policy/example_coverage states no reason it is not zero, which makes it "
                "a number rather than an obligation"]
    if len(without) > int(ceiling):
        return [f"{len(without)} routes ship no runnable example against a declared {ceiling} — the "
                f"ratchet only falls. Uncovered: {', '.join(without)}"]
    if len(without) < int(ceiling):
        return [f"{len(without)} routes ship no example against a stale declaration of {ceiling} — "
                "lower it, so the next pack added without one is refused rather than absorbed"]
    return []


def wheel_import_errors() -> list[str]:
    """No SHIPPED module may import a development-only one, or the wheel does not import at all.

    A hole opened by the packaging split itself: nine instruments were correctly kept out of the
    wheel, and nothing then stopped a shipped module importing one. That failure is invisible from
    a checkout — where every module is present — and appears only for the consumer, at import time.
    """
    import ast as _ast
    shipped = set(re.findall(r'"([a-z_][a-z0-9_]*)"', re.search(
        r"py-modules = \[(.*?)\]", read("pyproject.toml"), re.S).group(1)))
    dev_only = {str(n) for n in ((atlas().get("context_policy") or {})
                                 .get("install_footprint") or {}).get("development_only") or []}
    errors: list[str] = []
    for name in sorted(shipped):
        source = ROOT / "scripts" / f"{name}.py"
        if not source.exists():
            continue
        try:
            parsed = _ast.parse(source.read_text(encoding="utf-8"))
        except SyntaxError:
            # A FILE THAT DOES NOT PARSE IS ALREADY SOMEBODY ELSE'S FINDING. check() asserts that
            # every tracked source file compiles, and it runs FIRST for exactly this reason — so
            # this guard reports nothing here rather than crashing and taking the whole contract
            # with it, which is what it did the first time it met the planted defect.
            continue
        # TOP LEVEL ONLY, and that distinction is the whole rule. A module-level import of a
        # development-only module breaks `import atlas` for every consumer; an import inside a
        # function breaks only the command that needs it, which is the intended trade and the
        # remedy this guard's own message recommends. Walking the whole tree refused the fix.
        for node in parsed.body:
            imported = ([a.name for a in node.names] if isinstance(node, _ast.Import)
                        else [node.module] if isinstance(node, _ast.ImportFrom) and node.module
                        else [])
            for target in imported:
                if str(target).split(".")[0] in dev_only:
                    errors.append(f"shipped module '{name}' imports development-only '{target}' — "
                                  "the wheel would not import for a consumer, and a checkout "
                                  "cannot show that because every module is present here")
    return errors


def generated_attribute_errors() -> list[str]:
    """Every generated file is MARKED generated in .gitattributes, so the two rosters cannot drift.

    Not cosmetic: a generated file read as hand-written is reviewed line by line, and counted as
    source it misreports what the repository is made of — which is how a routing table with a
    contract came to be published as 61% documentation.

    It lives HERE rather than beside the language-bar instrument because that instrument is
    development-only and this check belongs to the contract, which ships. The wheel-import guard
    refused the other arrangement, which is the guard working.
    """
    lines = [line.strip() for line in read(".gitattributes").splitlines()
             if line.strip() and not line.startswith("#")]
    marked = {line.split()[0] for line in lines if "linguist-generated=true" in line}
    return [f".gitattributes does not mark '{name}' as linguist-generated, and atlas.yaml declares "
            "it generated — read as hand-written it is reviewed line by line, and counted as "
            "source it misreports what this repository is made of"
            for name in (atlas().get("generated_files") or []) if str(name) not in marked]


def mechanism_doc_errors() -> list[str]:
    """A document that describes a MECHANISM must name what enforces it.

    Measured at 2.25.0: every pattern and systems document named ZERO of the instruments built to
    implement them. They described mechanisms that had since become real and pointed at none of
    them — advice that outlived its own implementation, which reads as guidance and is actually a
    map of where the enforcement used to be missing.

    The roster is derived from atlas.yaml/instruments rather than typed, so an instrument added
    beside these documents widens what counts automatically. `patterns/` and the mechanism pages
    under `systems/` are in scope; an index page is not, because a page whose job is to link
    elsewhere has no mechanism of its own.
    """
    names = set()
    for label, spec in (atlas().get("instruments") or {}).items():
        names.add(str(label).split()[0].rstrip(":"))
        names.add(Path(str((spec or {}).get("script") or "")).stem)
    names |= {"agent_policy", "governance_tiers", "agent_failure_modes", "staleness_discipline",
              "parser_discipline", "retrieval_policy", "data_classes", "knowledge_layers",
              "language_selection", "gate_tools", "tool_claims", "install_footprint",
              "entry_paths", "example_coverage"}
    names.discard("")
    errors: list[str] = []
    # wiki/ joined after its pages turned out to name nothing either — the same shape in a
    # third directory, which is what makes it a rule rather than two incidents.
    for page in (sorted((ROOT / "patterns").glob("*.md"))
                 + sorted((ROOT / "systems").glob("*.md"))
                 + sorted((ROOT / "wiki").glob("*.md"))):
        if page.name == "README.md":
            continue
        body = page.read_text(encoding="utf-8")
        if not any(name in body for name in names):
            errors.append(f"{page.relative_to(ROOT)} describes a mechanism and names no instrument "
                          "or declaration that enforces it — advice that outlived its own "
                          "implementation reads as guidance and is a map of a gap that closed")
    return errors


def entry_cost_errors() -> list[str]:
    """A budget may only fall, and a path may not name a file the tree does not have."""
    errors: list[str] = []
    if not paths():
        return ["atlas.yaml/context_policy declares no entry_paths — the one cost a reader pays "
                "before asking anything would then be measured by nothing"]
    for name, row in measure().items():
        for rel_path, size in row["files"]:
            if size < 0:
                errors.append(f"context_policy/entry_paths/{name} names {rel_path}, which does not exist")
        if not str(row.get("raised_for") or "").strip():
            errors.append(f"context_policy/entry_paths/{name} names nothing in raised_for — a "
                          "budget that can move without saying what moved it is not a ratchet")
        if not row["budget"]:
            errors.append(f"context_policy/entry_paths/{name} declares no budget_bytes — an entry "
                          "path with no ceiling grows a page at a time and nothing says so")
        elif row["bytes"] > row["budget"]:
            errors.append(f"entry path '{name}' is {row['bytes']} bytes against a budget of "
                          f"{row['budget']} — the ratchet only falls: take something OUT of the "
                          "entry path, or move it behind a route")
        elif row["budget"] - row["bytes"] > row["slack"]:
            errors.append(f"entry path '{name}' measures {row['bytes']} against a budget of "
                          f"{row['budget']} — {row['budget'] - row['bytes']} bytes of slack, over the "
                          f"declared {row['slack']}. Lower the budget to what it now costs, or the "
                          "next addition is absorbed by the gap instead of being refused by it")
    return errors


def main(argv: list[str] | None = None) -> int:
    report = measure()
    for name, row in report.items():
        print(f"entry path '{name}' [{row['measure']}] — {row['why']}")
        for rel_path, size in row["files"]:
            print(f"  {size:>7} B  ~{tokens(size):>6} tok  {rel_path}")
        print(f"  {row['bytes']:>7} B  ~{tokens(row['bytes']):>6} tok  TOTAL — budget {row['budget']}, "
              f"slack {row['budget'] - row['bytes']}/{row['slack']}")
    lazy, files = lazy_bytes()
    handed = sum(r["bytes"] for r in report.values())
    print(f"handed over before a route: {handed} B (~{tokens(handed)} tok)")
    print(f"reachable only through a route: {lazy} B across {files} documents — "
          f"{lazy / max(handed, 1):.1f}x the entry path, and none of it is read unasked")
    weight = footprint()
    print(f"install footprint: {weight['modules']} modules, {weight['bytes']} B "
          f"(~{weight['bytes'] // 1024} KiB), {weight['dependencies']} runtime dependency/ies, "
          f"{weight['development_only']} instruments NOT shipped — the "
          "policy content is POINTED AT, never shipped, so no install carries a copy that ages")
    covered, without = example_coverage()
    print(f"runnable examples: {len(covered)} of {len(route_targets())} routes ship one; "
          f"{len(without)} ship nothing that runs and are DECLARED rather than exercised")
    problems = (entry_cost_errors() + footprint_errors()
                + example_coverage_errors() + wheel_import_errors())
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: bytes, not judgement. A short entry document that sends every reader to the")
    print("       wrong place costs more than a long one that routes correctly, and no byte")
    print("       count can tell them apart — the router's evidence line and a reviewer can.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
