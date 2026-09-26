#!/usr/bin/env python3
"""What the language bar will say, computed from the tree rather than predicted.

WHY (2.18.0). This repository has been wrong about its own language bar twice, in opposite
directions, and both times the error was a BLANKET rule over files that are not the same kind of
thing. At v2.0.0 Linguist reported 100% Python, because Markdown is prose and excluded by default
and the one directory holding code took the whole bar. The correction was `*.md
linguist-detectable=true` everywhere, which put 464 KB of guides and operating cards into the bar
and produced 61% Markdown — a routing table with a contract, described as a documentation
repository.

So the classification is per KIND now, and this computes the consequence. A projection nobody can
run is a guess, and a guess about what a reader sees first is exactly the kind of claim this
repository refuses to leave unmeasured.

WHAT IT DOES NOT PROVE: what GitHub will actually publish. Linguist has heuristics this does not
implement — shebang detection, a size ceiling, vendor paths — so this is the REPOSITORY's reading
of its own `.gitattributes`, and the platform's reading is authoritative. `gh api
repos/OWNER/REPO/languages` is what settles it, and disagreement between the two is a finding.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
from collections import Counter

from atlascore import ROOT, atlas, read, route_targets, routes
from contextcost import generated_attribute_errors

DATA_SUFFIXES = {".yaml", ".yml"}


def suffix_language() -> dict[str, str]:
    """Suffix -> the language Linguist names it, DERIVED from the router rather than enumerated.

    THE ENUMERATED VERSION NARROWED, and its own comment argued it would not: 13 suffixes against
    a tree holding 53 routed ones, so the projection could not see the F#, Haskell and Dockerfile
    bytes the live API was already reporting. Measured at 2.27.0.

    The router already maps every suffix to a pack; `atlas.yaml/linguist_names` maps every pack to
    what Linguist calls it, `null` where Linguist has no entry. `check` asserts that map covers the
    routes exactly, so a new pack cannot enter the tree and leave this instrument behind.
    """
    names = atlas().get("linguist_names") or {}
    return {suffix: str(names[route]) for suffix, route in routes().items()
            if names.get(route)} | {".yaml": "YAML", ".yml": "YAML"}


def linguist_name_errors() -> list[str]:
    """Every route names what Linguist calls it, or declares `null`. Silence is the failure.

    A pack added with no entry would not break the bar — it would quietly drop that pack's bytes
    out of it, which is a roster narrowing with no symptom.
    """
    names = atlas().get("linguist_names")
    if not isinstance(names, dict):
        return ["atlas.yaml declares no linguist_names, so the language bar is projected from an "
                "enumerated suffix table that narrows the day a pack is added beside it"]
    known, declared = set(route_targets()), set(names)
    return ([f"linguist_names is missing {route!r} — a routed pack with no entry drops silently "
             "out of the projected bar, which is a narrowing roster with no symptom"
             for route in sorted(known - declared)]
            + [f"linguist_names declares {route!r}, which is not a route"
               for route in sorted(declared - known)])


def attribute_lines() -> list[str]:
    return [line.strip() for line in read(".gitattributes").splitlines()
            if line.strip() and not line.startswith("#")]


def counted_files() -> list[tuple[str, str, int]]:
    """(path, language, bytes) for every file this repository's attributes make detectable."""
    table = suffix_language()
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT, timeout=600).decode()
    detectable_data = {line.split()[0] for line in attribute_lines()
                       if "linguist-detectable=true" in line}
    undetectable = {line.split()[0] for line in attribute_lines()
                    if "linguist-detectable=false" in line}
    rows: list[tuple[str, str, int]] = []
    for name in (f for f in raw.split("\0") if f):
        path = ROOT / name
        suffix = pathlib.PurePath(name).suffix.lower()
        language = table.get(suffix)
        if not language or not path.is_file() or path.is_symlink():
            continue
        if any(name.endswith(p.lstrip("*")) or p.rstrip("*") in name for p in undetectable):
            continue
        # Data formats are excluded by Linguist unless an attribute makes them detectable.
        if suffix in DATA_SUFFIXES and not any(
                name == p or (p.endswith("tools.yaml") and name.endswith("tools.yaml"))
                for p in detectable_data):
            continue
        rows.append((name, language, path.stat().st_size))
    return rows


def main(argv: list[str] | None = None) -> int:
    rows = counted_files()
    by_language: Counter[str] = Counter()
    for _, language, size in rows:
        by_language[language] += size
    total = sum(by_language.values()) or 1
    print(f"language bar, computed from {len(rows)} detectable files:")
    for language, size in by_language.most_common():
        print(f"  {100 * size / total:>5.1f}%  {language:<12} {size:>8} B")
    prose = sum(page.stat().st_size
                for directory in ("docs", "wiki", "patterns", "systems", "research")
                for page in (ROOT / directory).rglob("*.md") if page.is_file())
    print(f"  excluded as documentation: {prose} B of prose in the indexed directories — present "
          "to read, and not a programming language")
    problems = generated_attribute_errors() + linguist_name_errors()
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: this repository's reading of its own .gitattributes. Linguist has heuristics")
    print("       this does not implement, so `gh api repos/OWNER/REPO/languages` is what settles")
    print("       it, and a disagreement between the two is a finding rather than a rounding.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
