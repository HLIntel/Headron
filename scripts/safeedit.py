#!/usr/bin/env python3
"""Edits that cannot fail silently: an anchor that must match once, and a write that is read back.

WHY (2.27.0). Three records were lost in one session with zero errors. A test's restore erased a
concurrent edit; the next insert was anchored on the erased record, so `str.replace` did nothing and
the one after that lost its anchor too. Then a key-set check caught an edit that dropped a key line
and re-parented fourteen children under the new key while the file still parsed. Each primitive
here refuses one of those shapes, and every scripted edit to this tree goes through them.

WHY IT DOES NOT SHIP. Nothing a consumer runs edits this repository's files; the harness that does
is development-only, and a primitive with no shipped caller would be weight in every install.
"""
from __future__ import annotations

from pathlib import Path

from atlascore import strict_yaml


def replace_once(text: str, old: str, new: str, where: str) -> str:
    """`str.replace` that REFUSES unless `old` occurs exactly once.

    A plain replace with no match returns its input unchanged and says nothing. MEASURED at 2.27.0,
    and it COMPOUNDED: three failure-mode entries were each anchored on the entry written just
    before it; the first was erased by a concurrent restore, so the second's anchor was gone and
    its insert did nothing, which removed the third's anchor in turn. Three records lost, zero
    errors. Twice-matching is refused too — an edit that lands in the first of two places is a
    guess about which one was meant.
    """
    found = text.count(old)
    if found != 1:
        raise ValueError(f"{where}: the anchor occurs {found} times, not once — REFUSING an edit "
                         f"that would {'do nothing' if not found else 'guess which match was meant'}: "
                         f"{old[:70]!r}")
    return text.replace(old, new, 1)

def write_verified(path: Path, text: str) -> None:
    """Write, then READ IT BACK. A write that did not land is the quietest failure there is."""
    path.write_text(text, encoding="utf-8")
    if path.read_text(encoding="utf-8") != text:
        raise OSError(f"{path}: the bytes read back differ from the bytes written — another "
                      "writer, a full disk or a filesystem that lied; the edit did NOT land")

def write_yaml_verified(path: Path, text: str, added: set[str] = frozenset(),
                        removed: set[str] = frozenset()) -> None:
    """Write YAML, then prove the top-level key set moved EXACTLY as intended — no more.

    Checking only that a new key exists is too weak. MEASURED at 2.27.0: an insert anchored on
    `language_selection:` dropped that key line, its fourteen children were silently re-parented
    under the new key, the file still parsed, and the new-key assertion passed. The contract caught
    it one layer later. The whole key set is the identity; one key is a rendering of it.
    """
    before = set(strict_yaml(path.read_text(encoding="utf-8"), str(path)) or {})
    after = set(strict_yaml(text, str(path)) or {})
    want = (before | set(added)) - set(removed)
    if after != want:
        raise ValueError(f"{path}: top-level keys moved beyond intent — unexpectedly gained "
                         f"{sorted(after - want)}, lost {sorted(want - after)}; nothing written")
    write_verified(path, text)


def yaml_value(text: str) -> str:
    """A YAML value that reads back as exactly `text` — generated, never hand-quoted.

    WHY (3.3.0). Hand-quoting failed three ways in one session: a colon ended a plain value, an
    apostrophe closed a single-quoted one, and an unquoted comma split a flow value, silently
    truncating six declarations. The emitter knows YAML's rules; the round trip below proves it.
    """
    import yaml

    def reads_back(out: str) -> bool:  # SAFE IN BOTH PLACES: a plain value and inside a {flow} mapping
        try:
            return (strict_yaml(f"k: {out}", "yaml_value").get("k") == text
                    and strict_yaml(f"k: {{v: {out}}}", "yaml_value").get("k") == {"v": text})
        except (ValueError, yaml.YAMLError):  # a candidate that does not even parse is simply rejected
            return False
    for style in (None, "'", '"'):  # plain when it is safe, else single quotes, else double
        out = yaml.safe_dump(text, default_style=style, width=10**9, allow_unicode=True).strip()
        out = out.removesuffix("...").strip()
        if reads_back(out):
            return out
    raise ValueError(f"yaml_value: no quoting of {text!r} reads back exactly")


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["quote"] and len(sys.argv) == 3:
        print(yaml_value(sys.argv[2]))
    else:
        raise SystemExit("usage: safeedit.py quote '<text>'   — prints a YAML value that reads back exactly")
