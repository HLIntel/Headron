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

import re
import subprocess
import sys

from atlascore import ROOT, atlas, tracked

PATTERNS = {
    "home path": r"/(?:Users|home)/[A-Za-z0-9._-]+/",
    # A domain ending in a file extension is a path (`@AGENTS.md`), not an address.
    "email address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?!(?:md|py|json|ya?ml|txt|toml|sh)\b)[A-Za-z]{2,}\b",
    "private network address": r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))(?:\.\d{1,3}){2,3}\b",
    # Followed by another dot it is a file name (`settings.local.json`), not a host.
    "internal hostname": r"\b[a-z0-9-]+\.(?:internal|local|lan|corp)\b(?!\.)",
}


def leak_errors() -> list[str]:
    spec = atlas().get("public_surface") or {}
    placeholders = [str(p) for p in spec.get("placeholders") or []]
    errors = []
    for path in tracked():
        if not path.is_file() or path.suffix in {".webp", ".png", ".jpg", ".gz", ".lock"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for kind, pattern in PATTERNS.items():
            for hit in {m.group(0) for m in re.finditer(pattern, text)}:
                if not any(p in hit for p in placeholders):
                    errors.append(f"{path.relative_to(ROOT)} carries a {kind} ({hit}) — the public tree may not")
    for store in spec.get("never_tracked") or []:
        if subprocess.run(["git", "check-ignore", "-q", str(store)], cwd=ROOT, timeout=600, check=False).returncode:  # noqa: S603, S607
            errors.append(f"{store} is not gitignored — a runtime store would be committed with what it recorded")
    return sorted(errors)


if __name__ == "__main__":
    found = leak_errors()
    print("\n".join(found) or "no private detail in the public tree")
    sys.exit(1 if found else 0)
