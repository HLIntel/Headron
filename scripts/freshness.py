#!/usr/bin/env python3
"""Which parts of this tree have not been re-examined lately — measured in CONTRACT VERSIONS.

WHY (2.26.0). A directory listing shows a last-touched date per path, and reading it is how this
gap was noticed: several directories had not been opened since a contract many versions back,
while the rules they encode had moved underneath them. Nothing measured that, so "which sections
am I forgetting" was answered by scrolling — which finds the ones you happen to look at.

MEASURED IN VERSIONS, NOT DAYS, and that is the whole design. A date says when somebody typed; a
contract version says which tree the path was last true of, and only the second can be compared
against what the contract now says. A path untouched for a week during a quiet week is fine; a
path untouched across eleven minor versions has been left behind by eleven changes to the rules.

WHY IT IS NOT PART OF `check`. It reads git history, which is a fact about THIS repository's
maintenance rather than about the contract a consumer runs — the same reason `ghaudit` and
`packprobe` stand alone. It also measures COMMITTED state, so editing a file does not clear its
flag until the edit lands, and a contract gate that a correct edit cannot satisfy is a gate that
gets worked around. It runs in CI and in the ladder as its own step.

WHAT IT DOES NOT PROVE. That a stale path is WRONG. Some paths genuinely should not change —
a licence, an example whose language did not move. So the horizon is a prompt to look, the
declaration carries an `exempt` list with a reason per entry, and a path that is simply correct
stays correct. What it refuses is the silent case: a path nobody has opened and nobody noticed.
"""
from __future__ import annotations

import re
import subprocess
import sys

from atlascore import ROOT, atlas, read

VERSION_RE = re.compile(r"\b(\d+)\.(\d+)\.(\d+)\b")


def horizon() -> dict:
    return ((atlas().get("context_policy") or {}).get("review_horizon")) or {}


def _parts(text: str) -> tuple[int, int, int] | None:
    found = VERSION_RE.search(text)
    return (int(found.group(1)), int(found.group(2)), int(found.group(3))) if found else None


def last_contract(path: str) -> tuple[str, str]:
    """(contract version at the newest commit touching `path`, that commit's subject).

    The version is read from the commit SUBJECT, which this repository stamps with the contract
    version it shipped. That is a convention rather than a guarantee, so a subject with no version
    reports as unknown instead of being guessed at — a fabricated freshness is worse than none.
    """
    subject = subprocess.run(["git", "log", "-1", "--format=%s", "--", path],
                             cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()
    found = _parts(subject)
    return (".".join(str(n) for n in found) if found else "unknown", subject[:70])


def survey() -> list[dict]:
    """One row per tracked top-level path, newest-contract-first."""
    current = _parts(read("VERSION")) or (0, 0, 0)
    exempt = {str(k): str(v) for k, v in (horizon().get("exempt") or {}).items()}
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode()
    tops = sorted({name.split("/")[0] if "/" in name else name for name in raw.split("\0") if name})
    rows: list[dict] = []
    for top in tops:
        version, subject = last_contract(top)
        seen = _parts(version) if version != "unknown" else None
        behind = (current[1] - seen[1]) if seen and seen[0] == current[0] else None
        rows.append({"path": top, "contract": version, "minors_behind": behind,
                     "subject": subject, "exempt": exempt.get(top)})
    return sorted(rows, key=lambda r: (r["minors_behind"] is None, -(r["minors_behind"] or 0)))


def freshness_errors() -> list[str]:
    """A path past the horizon must be looked at, or exempted WITH a reason.

    The exemption is the load-bearing half. Without it the horizon becomes a list everyone learns
    to scroll past, which is a silenced guard wearing a number.
    """
    limits = horizon()
    if not limits:
        return ["context_policy/review_horizon is not declared, so 'which section am I forgetting' "
                "is answered by scrolling a directory listing, which finds the ones you look at"]
    cap = int(limits.get("max_minors_behind") or 0)
    if not cap:
        return ["context_policy/review_horizon declares no max_minors_behind"]
    errors: list[str] = []
    for row in survey():
        if row["exempt"] or row["minors_behind"] is None:
            continue
        if row["minors_behind"] > cap:
            errors.append(f"{row['path']}/ was last touched at contract {row['contract']}, "
                          f"{row['minors_behind']} minor versions behind — look at it, or exempt "
                          "it in review_horizon/exempt WITH the reason it should not change")
    for name, why in (limits.get("exempt") or {}).items():
        if not str(why or "").strip():
            errors.append(f"review_horizon/exempt/{name} states no reason, which makes the "
                          "exemption a snooze button rather than a decision")
    return errors


def main(argv: list[str] | None = None) -> int:
    rows = survey()
    cap = int(horizon().get("max_minors_behind") or 0)
    print(f"contract {read('VERSION').strip()} — how far behind each path was last touched, "
          f"horizon {cap} minor version(s)")
    for row in rows:
        behind = "?" if row["minors_behind"] is None else str(row["minors_behind"])
        mark = "EXEMPT" if row["exempt"] else ("LOOK  " if (row["minors_behind"] or 0) > cap else "      ")
        print(f"  {mark} {row['path']:<22} contract {row['contract']:<9} {behind:>3} behind  "
              f"{row['subject']}")
    problems = freshness_errors()
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: versions, not days, and it does not prove a stale path is WRONG. Some paths")
    print("       should not change; that is what the exemption and its reason are for. What it")
    print("       refuses is the silent case — a path nobody opened and nobody noticed.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
