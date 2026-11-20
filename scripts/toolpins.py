#!/usr/bin/env python3
"""Drift guard: a tool the done set pins by version is pinned to that one version everywhere.

The done set names its tools as `uvx --from ruff==X` or `uvx zizmor@X`. The same tool is pinned again in
the native CI steps (scripts/cipipeline.py), the land pre-check (scripts/branchstate.py), the hosted
workflows and the lockfiles — five hand-typed copies. Before this guard uv.lock resolved ruff 0.17.3 while
every gate ran 0.16.8, so a `uv sync --extra quality` lint and the gate's lint were two different rulers.

Every `name==V` or `name@V` for a done-set-pinned tool in the files below must name the same V; uv.lock's
resolved version counts as one more copy. Test modules are not read: a planted case may carry a stale pin.

  python scripts/toolpins.py     exit 0 when every copy agrees, 1 with each disagreeing copy named
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from atlascore import strict_yaml, text_of

ROOT = Path(__file__).resolve().parent.parent
PIN = re.compile(r"^([A-Za-z][A-Za-z0-9_.-]*)(?:==|@)(\d[\w.]*)$")
LOCKED = re.compile(r'^name = "([^"]+)"\nversion = "([^"]+)"', re.M)


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def done_pins(done_set: list[dict]) -> dict[str, dict[str, str]]:
    """tool -> {where: version} for every `name==V` / `name@V` argument a done-set gate passes."""
    pins: dict[str, dict[str, str]] = {}
    for row in done_set:
        for arg in row.get("argv") or []:
            if m := PIN.match(str(arg)):
                pins.setdefault(norm(m.group(1)), {})[f"done_set {row['id']}"] = m.group(2)
    return pins


def sources(root: Path) -> list[Path]:
    """The files that pin a gate tool by hand: harness scripts (not their cases), workflows, lockfiles."""
    found = [p for p in sorted((root / "scripts").glob("*.py")) if not p.name.endswith("_test.py")]
    found += sorted((root / ".github" / "workflows").glob("*.y*ml"))
    return found + sorted((root / "scripts").glob("*requirements*.lock.txt"))


def copies(text: str, tools: set[str]) -> list[tuple[str, str]]:
    """(tool, version) for each pinned mention of a known tool in free text."""
    names = "|".join(sorted({re.escape(t) for t in tools} | {re.escape(t.replace("-", "_")) for t in tools}))
    found = re.findall(rf"(?<![\w.-])({names})(?:==|@)(\d[\w.]*)", text, re.I) if names else []
    return [(norm(name), version) for name, version in found]


def pin_errors(done_set: list[dict], root: Path = ROOT) -> list[str]:
    """One line per tool whose copies disagree, naming every copy and its version."""
    pins = done_pins(done_set)
    for path in sources(root):
        rel = path.relative_to(root).as_posix()
        for tool, version in copies(text_of(path), set(pins)):
            pins[tool].setdefault(rel, version)
            if pins[tool][rel] != version:
                pins[tool][f"{rel} (again)"] = version
    lock = root / "uv.lock"
    for name, version in LOCKED.findall(text_of(lock) if lock.is_file() else ""):
        if norm(name) in pins:
            pins[norm(name)]["uv.lock"] = version
    return [
        f"tool pin drift: {tool} — " + ", ".join(f"{where} {v}" for where, v in sorted(seen.items()))
        for tool, seen in sorted(pins.items())
        if len(set(seen.values())) > 1
    ]


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        print((__doc__ or "").strip())
        sys.exit(0)
    policy = strict_yaml(text_of(ROOT / "atlas.yaml"), "atlas.yaml")["verification_policy"]
    errors = pin_errors(policy["done_set"])
    print("\n".join(errors) or f"toolpins: {len(done_pins(policy['done_set']))} pinned gate tools, every copy agrees")
    sys.exit(1 if errors else 0)
