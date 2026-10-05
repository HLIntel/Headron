#!/usr/bin/env python3
"""The public-repository rule, ENFORCED: no private path, address, internal host or runtime store is tracked.

WHY (3.18.0). README and SECURITY state one absolute rule — no secret, credential, private-project path or
internal hostname enters this repository — and nothing checked it. Secrets have their own scanners (the
platform's secret scanning, the commit hook); the details that leak around them do not: an absolute home
path in a doc, a personal address in an example, a LAN address in a config, a log or shell history
committed by accident. Those identify a machine and a person as surely as a key identifies an account.

Each finding is refused unless it is a declared placeholder (atlas.yaml/public_surface/placeholders).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from functools import lru_cache

from atlascore import ROOT, atlas, tracked

PATTERNS = {
    "home path": r"/(?:Users|home)/[A-Za-z0-9._-]+/",
    # A domain ending in a file extension is a path (`@AGENTS.md`), not an address.
    "email address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?!(?:md|py|json|ya?ml|txt|toml|sh)\b)[A-Za-z]{2,}\b",
    "private network address": r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))(?:\.\d{1,3}){2,3}\b",
    # Followed by another dot it is a file name (`settings.local.json`), not a host.
    "internal hostname": r"\b[a-z0-9-]+\.(?:internal|local|lan|corp)\b(?!\.)",
}


@lru_cache(maxsize=1024)  # keyed on whole texts: unbounded in a long-lived MCP process
def _scan(text: str, placeholders: tuple) -> tuple:
    """Every (kind, hit) in one file's TEXT — keyed on the text, never on the path.

    CONTENT-KEYED FOR THE SAME REASON `atlascore.parsed_python` IS: a mutation test plants a defect
    and re-runs this check, so a cache keyed on a NAME would answer from before the plant and the
    case would pass over a defect that was never scanned. Keyed on the bytes, a plant changes the
    key and the planted file is always re-read. MEASURED at 3.38.0: 0.095 s to 0.010 s when the
    tree is unchanged, and 0.020 s when one file moved — ~11 s off a suite.
    """
    found = []
    for kind, pattern in PATTERNS.items():
        for hit in sorted({m.group(0) for m in re.finditer(pattern, text)}):
            if not any(p in hit for p in placeholders):
                found.append((kind, hit))
    return tuple(found)


def private_terms() -> tuple[str, ...]:
    """Names only the owner knows — their projects, routers, fleet — read from the file THEA_PRIVATE_TERMS
    names, one per line (3.45.0). The LIST is never tracked here: a public roster of private names would be
    the leak it exists to stop. Unset or unreadable means no private check ran, and nothing claims it did."""
    path = os.environ.get("THEA_PRIVATE_TERMS", "")
    try:
        lines = open(os.path.expanduser(path), encoding="utf-8").read().splitlines() if path else []  # noqa: SIM115
    except OSError:
        return ()
    return tuple(t.strip() for t in lines if t.strip() and not t.lstrip().startswith("#"))


def leak_errors() -> list[str]:
    spec = atlas().get("public_surface") or {}
    placeholders = [str(p) for p in spec.get("placeholders") or []]
    errors, terms = [], private_terms()
    for path in tracked():
        if not path.is_file() or path.suffix in {".webp", ".png", ".jpg", ".gz", ".lock"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for kind, hit in _scan(text, tuple(placeholders)):
            errors.append(f"{path.relative_to(ROOT)} carries a {kind} ({hit}) — the public tree may not")
        errors += [f"{path.relative_to(ROOT)} names the private term '{term}' — the owner's fleet stays in the "
                   "owner's config, never in this tree" for term in terms
                   if re.search(rf"(?i)(?<![\w-]){re.escape(term)}(?![\w-])", text)]
    # ONE SPAWN, NOT ONE PER ROW. MEASURED at 3.38.0: six `git check-ignore -q` calls cost 0.122 s of
    # a 2.18 s check, and this check runs once per planted case — ~17 s a suite spent starting the
    # same program six times. `--stdin` answers the whole roster in one process and prints the paths
    # that ARE ignored, so the rows missing from its output are the findings.
    stores = [str(s) for s in spec.get("never_tracked") or []]
    if stores:
        done = subprocess.run(["git", "check-ignore", "--stdin"], cwd=ROOT, timeout=600,  # noqa: S603, S607
                              input="\n".join(stores).encode(), capture_output=True, check=False)
        ignored = {line for line in done.stdout.decode().splitlines() if line.strip()}
        for store in stores:
            if store not in ignored:
                errors.append(f"{store} is not gitignored — a runtime store would be committed with what it recorded")
    return sorted(errors)


if __name__ == "__main__":
    found = leak_errors()
    print("\n".join(found) or "no private detail in the public tree")
    sys.exit(1 if found else 0)
