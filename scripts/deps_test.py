#!/usr/bin/env python3
"""Planted third-party import cases (3.54.0): every import from outside the stdlib and the tree is declared by role."""

from __future__ import annotations

import tempfile
from pathlib import Path

DECLARED = {"yaml": "runtime", "jsonschema": "optional"}
EXTRAS = '[project.optional-dependencies]\ncrosscheck = ["jsonschema>=4"]\n\n[build-system]\n'
CLEAN = "import yaml\ntry:\n    import jsonschema\nexcept ImportError:\n    jsonschema = None\n"
PLANTS = (
    (
        "an import declared nowhere is refused at its file:line",
        "jsonschema imported by four scripts and declared nowhere",
        CLEAN + "import requests\n",
        DECLARED,
        EXTRAS,
        "scripts/mod.py:6 imports requests",
    ),
    (
        "an optional import outside a try that catches ImportError is refused",
        "an optional module whose absence crashes the run",
        "import yaml\nimport jsonschema\n",
        DECLARED,
        EXTRAS,
        "imports optional jsonschema outside a try",
    ),
    (
        "a declared module imported nowhere is refused",
        "a stale declaration that pre-approves the next import",
        CLEAN,
        {**DECLARED, "toml": "optional"},
        EXTRAS + 'x = ["toml"]\n',
        "declares toml, imported nowhere",
    ),
    (
        "an optional module missing from pyproject's extras is refused",
        "an optional dependency nothing can install on request",
        CLEAN,
        DECLARED,
        "[project.optional-dependencies]\nquality = []\n\n[build-system]\n",
        "not in pyproject's optional",
    ),
)


def run(module) -> None:
    from contextcost import third_party_errors

    for name, kills, source, declared, pyproject, needle in (
        ("the clean twin passes", "", CLEAN, DECLARED, EXTRAS, ""),
        *PLANTS,
    ):
        with tempfile.TemporaryDirectory(prefix="thea-deps-") as scratch:
            root = Path(scratch)
            (root / "scripts").mkdir()
            (root / "scripts" / "mod.py").write_text(source, encoding="utf-8")
            (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
            found = third_party_errors(root, declared)
        if needle and not any(needle in e for e in found) or not needle and found:
            raise SystemExit(f"FAIL {name}: want {needle or 'nothing'!r}, got {found}")
        if needle:
            module.CASES.append((name, kills))
        print(f"  ok    {name}")
