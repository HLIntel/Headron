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

from atlascore import ROOT, read
from contextcost import generated_attribute_errors

# Suffix -> the language Linguist names it. Only the ones this tree actually contains: a table of
# every language Linguist knows would be a second roster that narrows the day one is added here.
SUFFIX_LANGUAGE = {
    ".py": "Python", ".go": "Go", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".sh": "Shell", ".bash": "Shell", ".c": "C", ".h": "C", ".cpp": "C++", ".hpp": "C++",
    ".rs": "Rust", ".swift": "Swift", ".sql": "SQL", ".yaml": "YAML", ".yml": "YAML",
}
DATA_SUFFIXES = {".yaml", ".yml"}


def attribute_lines() -> list[str]:
    return [line.strip() for line in read(".gitattributes").splitlines()
            if line.strip() and not line.startswith("#")]


def _flagged(pattern_suffix: str, flag: str) -> set[str]:
    return {line.split()[0] for line in attribute_lines() if flag in line and line.endswith(pattern_suffix)}


def counted_files() -> list[tuple[str, str, int]]:
    """(path, language, bytes) for every file this repository's attributes make detectable."""
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode()
    detectable_data = {line.split()[0] for line in attribute_lines()
                       if "linguist-detectable=true" in line}
    undetectable = {line.split()[0] for line in attribute_lines()
                    if "linguist-detectable=false" in line}
    rows: list[tuple[str, str, int]] = []
    for name in (f for f in raw.split("\0") if f):
        path = ROOT / name
        suffix = pathlib.PurePath(name).suffix.lower()
        language = SUFFIX_LANGUAGE.get(suffix)
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
    problems = generated_attribute_errors()
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: this repository's reading of its own .gitattributes. Linguist has heuristics")
    print("       this does not implement, so `gh api repos/OWNER/REPO/languages` is what settles")
    print("       it, and a disagreement between the two is a finding rather than a rounding.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
