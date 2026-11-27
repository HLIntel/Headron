#!/usr/bin/env python3
"""The dependency-closure invariant: a dependency count is the CLOSURE an install pulls in.

proves: the hash lock's pinned set and the installed metadata walked transitively agree, so a
printed dependency count is what an install pays and not the lines someone typed.
does_not_prove: that the locked versions are free of vulnerabilities; the scanners own that.
closed_by: atlas_test's invariant cases and `headron check`.
"""

from __future__ import annotations

import importlib.metadata as md
import re
import sys

from atlascore import atlas, read


def _inv_dependency_count_is_the_closure() -> str | None:
    """A dependency count is the CLOSURE an install pulls in, never the lines someone typed.

    ADDED AT 2.28.0 on the owner's ask: "1 runtime dependency" was counted from requirements.txt,
    so a dependency that grew forty of its own would still print 1 — a false minimum. Two readings
    must agree: the hash lock (what CI installs; pip refuses anything unpinned) and the metadata of
    what is installed, walked transitively. The walk catches a new upstream requirement BEFORE the
    locked install refuses it, and the lock catches a count typed to look small.
    """

    def norm(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()

    def holds(marker: str) -> bool:
        # A pin or requirement gated on another interpreter is not part of THIS install: uv.lock gates
        # typing-extensions on python < 3.13, so on 3.13 it is locked yet rightly absent. Python
        # version clauses are evaluated; any other clause is assumed to hold (strict, never skips).
        def clause(c: str) -> bool:
            m = re.fullmatch(r"\s*(python_(?:full_)?version)\s*(<=|>=|==|!=|<|>)\s*[\"']([\d.]+)[\"']\s*", c)
            if not m:
                return True
            have = sys.version_info[:3] if m.group(1) == "python_full_version" else sys.version_info[:2]
            want = tuple(int(p) for p in m.group(3).split("."))
            have = tuple(have[: len(want)]) if m.group(1) == "python_version" else tuple(have)
            want = want + (0,) * (len(have) - len(want))
            return {
                "<": have < want,
                "<=": have <= want,
                ">": have > want,
                ">=": have >= want,
                "==": have == want,
                "!=": have != want,
            }[m.group(2)]

        return any(all(clause(c) for c in alt.split(" and ")) for alt in marker.split(" or "))

    lock = re.findall(r"^([A-Za-z0-9_.-]+)==[^\s;\\]*\s*(?:;([^\\\n]*))?", read("scripts/requirements.lock.txt"), re.M)
    pinned = {norm(p) for p, _ in lock}
    absent_ok = {norm(p) for p, marker in lock if marker and not holds(marker)}
    declared = ((atlas().get("context_policy") or {}).get("install_footprint") or {}).get("resolved_closure")
    if declared is None or len(pinned) != int(declared):
        return (
            f"install_footprint/resolved_closure says {declared} but the hash lock pins {len(pinned)} "
            f"({', '.join(sorted(pinned))}) — the count an install pays is the closure"
        )
    seen: set[str] = set()
    queue = sorted(pinned)
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        try:
            requires = md.requires(name) or []
        except md.PackageNotFoundError:
            if name in pinned and name not in absent_ok:
                return f"{name} is locked but not installed, so its closure cannot be read — install the lock first"
            continue  # required upstream and absent here: still outside the lock, reported below
        queue += [
            norm(re.split(r"[\s;<>=!~\[(]", r, maxsplit=1)[0])
            for r in requires
            if "extra ==" not in r and holds(r.partition(";")[2] or "")
        ]
    unpinned = sorted(seen - pinned)
    return (
        f"the installed closure pulls in {len(unpinned)} package(s) the lock does not pin: {', '.join(unpinned)}"
        if unpinned
        else None
    )
