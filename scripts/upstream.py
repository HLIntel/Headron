#!/usr/bin/env python3
"""THE UPSTREAM COUNT (3.53.0): commits on the default branch that a lane does not carry.

`unpushed_bound` caps work a lane holds that the remote lacks; nothing capped the other direction.
One lane met it twice in one landing: the default branch moved two commits, then one more, between
its verify and its push, and each move was a hand rebase of generated files. The rebase cost grows
with the count, so the count is held to a declared bound like every other lane number.

It reads the LAST FETCH, never the network: a stale `origin/<base>` under-counts, and the row says
which ref it read. No such ref is NOT RUN — a blind check must refuse, never pass.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def upstream_count(repo: Path, base: str) -> int | None:
    """Commits on origin/<base> missing from HEAD, from the last fetch; None when that ref is absent."""
    ref = f"origin/{base}"
    git = ["git", "-C", str(repo)]
    if subprocess.run(
        [*git, "rev-parse", "--verify", "--quiet", ref], capture_output=True, check=False, timeout=30
    ).returncode:
        return None
    out = subprocess.run(
        [*git, "rev-list", "--count", f"HEAD..{ref}"], capture_output=True, text=True, check=False, timeout=30
    )
    return int(out.stdout) if out.returncode == 0 else None


def upstream_errors(repo: Path, policy: dict) -> tuple[list[str], int | None]:
    """Breaches of branch_policy/upstream_bound and the count read; a None count means NOT RUN."""
    bound = policy.get("upstream_bound") or {}
    if not bound.get("max_behind_commits") or not bound.get("why"):
        return ["branch_policy/upstream_bound is not declared with max_behind_commits and why"], None
    base = policy.get("default_base") or "main"
    count = upstream_count(repo, base)
    limit = int(bound["max_behind_commits"])
    if count is not None and count > limit:
        return [
            f"upstream count {count} against a bound of {limit}: origin/{base} carries {count} commit(s) "
            f"this lane lacks — `git fetch origin && git rebase origin/{base}`, then verify again"
        ], count
    return [], count


def main() -> int:
    from atlascore import atlas  # noqa: PLC0415

    policy = atlas().get("branch_policy") or {}
    problems, count = upstream_errors(Path.cwd(), policy)
    base = policy.get("default_base") or "main"
    print(f"upstream count: {'NOT RUN, no origin/' + base if count is None else count} (read from the last fetch)")
    for problem in problems:
        print(f"  FAIL {problem}")
    return 2 if count is None and not problems else 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
