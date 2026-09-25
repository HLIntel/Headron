#!/usr/bin/env python3
"""What was edited longest ago, and which worktrees are hung — computed from git, never typed.

WHY (3.6.0). Drift starts where nobody has looked: a file untouched for many releases still states what
was true when it was written, and a worktree nobody finished still holds work that looks done from its
own terminal. Both are invisible until something reads their age.

  oldest [N]    the N least recently edited tracked files, oldest first, then each top-level area by the
                age of its most recent edit — the parts of the tree that have gone longest unread
  review        after a STRUCTURAL change (atlas.yaml/drift_review/structural): every file older than the
                horizon that references a path this change touched, plus the hot/warm/cold tiers
  repos [root]  every sibling git repository: uncommitted, unpushed and behind counts, age of last commit
  worktrees     every worktree: branch, age of its last commit, uncommitted files, commits not on the
                default branch, and a verdict — active, finished (safe to remove), stale, locked or prunable

Ages are printed, never stored: a stored age is wrong the day after (rule: no calendar date in a
tracked file). WHAT IT DOES NOT PROVE: that an old file is wrong — only that nobody has touched it; the
reader decides whether it is settled or forgotten.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from atlascore import ROOT, atlas, rel, tracked

STALE_DAYS = 14  # a worktree with no commit for this long is named STALE — a bound for review, not a rule


def _git(*args: str, cwd: Path = ROOT) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False, timeout=600)
    return done.stdout


def last_edits() -> dict[str, int]:
    """path -> unix time of the last commit that touched it, in ONE pass over history."""
    seen: dict[str, int] = {}
    stamp = 0
    for line in _git("log", "--format=@%ct", "--name-only").splitlines():
        if line.startswith("@"):
            stamp = int(line[1:])
        elif line and line not in seen:
            seen[line] = stamp
    return seen


def oldest(limit: int) -> int:
    now, edits = time.time(), last_edits()
    names = [rel(p) for p in tracked() if p.is_file()]
    fresh = sorted(n for n in names if n not in edits)  # staged or new: no commit has touched them yet
    files = sorted((edits[n], n) for n in names if n in edits)
    if fresh:
        print(f"never committed ({len(fresh)}): {', '.join(fresh[:6])}{' …' if len(fresh) > 6 else ''}")
    print(f"least recently edited, of {len(files)} committed files:")
    for stamp, name in files[:limit]:
        print(f"  {(now - stamp) / 86400:6.1f} days  {name}")
    areas: dict[str, int] = {}
    for stamp, name in files:
        area = name.split("/", 1)[0] if "/" in name else "(root)"
        areas[area] = max(areas.get(area, 0), stamp)
    print("each area by its most recent edit, longest untouched first:")
    for area, stamp in sorted(areas.items(), key=lambda kv: kv[1])[:limit]:
        print(f"  {(now - stamp) / 86400:6.1f} days  {area}/")
    return 0


def worktrees() -> int:
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    now, rows, current = time.time(), [], {}
    for line in _git("worktree", "list", "--porcelain").splitlines() + [""]:
        if not line:
            if current:
                rows.append(current)
            current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value or True
    stale = 0
    for index, row in enumerate(rows):
        path = Path(str(row["worktree"]))
        branch = str(row.get("branch", "(detached)")).removeprefix("refs/heads/")
        if row.get("prunable"):
            verdict, age, dirty, ahead = "PRUNABLE — its directory is gone", 0.0, 0, 0
        else:
            age = (now - int(_git("log", "-1", "--format=%ct", cwd=path).strip() or now)) / 86400
            dirty = len(_git("status", "--porcelain", cwd=path).splitlines())
            ahead = int(_git("rev-list", "--count", f"origin/{base}..HEAD", cwd=path).strip() or 0)
            # THE MAIN CHECKOUT IS LISTED FIRST and is never "finished": the first draft offered it for removal.
            verdict = ("main checkout" if index == 0 else "LOCKED" if row.get("locked") else
                       "FINISHED — nothing ahead of the base, safe to remove" if ahead == 0 and not dirty else
                       f"STALE — no commit for {STALE_DAYS}+ days" if age > STALE_DAYS else "active")
        stale += verdict.startswith(("STALE", "PRUNABLE", "LOCKED"))
        print(f"  {branch:<42} {age:5.1f}d  dirty {dirty:<3} ahead {ahead:<3} {verdict}  ({path})")
    print(f"{len(rows)} worktree(s); {stale} need attention")
    return 0


def changed_paths() -> list[str]:
    """Paths this lane changed against the default base, committed or not."""
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    names = set(_git("diff", "--name-only", f"origin/{base}...HEAD").split())
    names |= set(_git("diff", "--name-only", "HEAD").split()) | set(_git("diff", "--name-only", "--cached").split())
    return sorted(names)


def vanished() -> set[str]:
    """Identifiers and paths this change REMOVED: in its deleted lines and nowhere in its added lines.

    WHY NOT FILE NAMES (3.6.0): the first draft matched the names of changed files, and `atlas` or
    `enforce` flagged 35 files that merely mention a hub. What goes stale is a reference to something
    that no longer exists — a renamed gate, a moved path, a deleted key — so that is what is searched.
    """
    import re
    base = str((atlas().get("branch_policy") or {}).get("default_base") or "main")
    diff = _git("diff", "-U0", f"origin/{base}") + _git("diff", "-U0", "--cached")
    word = re.compile(r"[A-Za-z_][\w./-]{5,}")
    gone, came = set(), set()
    for line in diff.splitlines():
        found = {w.rstrip("./-") for w in word.findall(line[1:])}  # a sentence's full stop is not a path
        if line.startswith("-") and not line.startswith("---"):
            gone |= found
        elif line.startswith("+") and not line.startswith("+++"):
            came |= found
    candidates = {w for w in gone - came if (any(c in w for c in "_./") or any(c.isupper() for c in w[1:]))
                  and not re.fullmatch(r"v?\d+(\.\d+)+", w)}  # a version stamp moving on is not a rename
    # STILL DECLARED ANYWHERE THE CHANGE TOUCHED = NOT VANISHED: a shortened generated list drops an id
    # that atlas.yaml still defines.
    now = " ".join((ROOT / c).read_text(encoding="utf-8", errors="ignore") for c in changed_paths() if (ROOT / c).is_file())
    return {w for w in candidates if w not in now}


def review() -> int:
    spec = atlas().get("drift_review") or {}
    horizon = float(spec.get("horizon_hours") or 24) * 3600
    changed = changed_paths()
    structural = [c for c in changed if any(c == s or c.startswith(s) for s in spec.get("structural") or [])]
    if not structural:
        print(f"drift review: {len(changed)} changed path(s), none structural — no review triggered")
        return 0
    now, edits = time.time(), last_edits()
    keys = vanished()
    stale = [(edits[n], n) for n in (rel(p) for p in tracked() if p.is_file())
             if n in edits and now - edits[n] > horizon and n not in changed]
    flagged = []
    for stamp, name in sorted(stale):
        text = (ROOT / name).read_text(encoding="utf-8", errors="ignore")
        hits = sorted(k for k in keys if k in text)
        if hits:
            flagged.append((stamp, name, hits))
    print(f"drift review: {len(structural)} structural path(s) changed, {len(keys)} identifier(s) removed or renamed; "
          f"{len(stale)} file(s) older than {horizon / 3600:.0f}h, {len(flagged)} still name a vanished one"
          + (" — review these now:" if flagged else ""))
    for stamp, name, hits in flagged:
        print(f"  {(now - stamp) / 3600:6.0f}h  {name}  (mentions {', '.join(hits[:3])})")
    ordered = sorted(edits.values(), reverse=True)
    tiers = spec.get("tiers") or {}
    if ordered:
        hot = ordered[max(int(len(ordered) * float(tiers.get("hot", 0.15))) - 1, 0)]
        cold = ordered[min(int(len(ordered) * (1 - float(tiers.get("cold", 0.15)))), len(ordered) - 1)]
        print(f"tiers: hot = edited within {(now - hot) / 3600:.0f}h (load first) · cold = older than "
              f"{(now - cold) / 3600:.0f}h (reach by search, not by default)")
    return 0


def repos(root: Path) -> int:
    """Sibling repositories: which need a look before a structural session ends."""
    rows = 0
    for git_dir in sorted(root.glob("*/.git")):
        repo = git_dir.parent
        dirty = len(_git("status", "--porcelain", cwd=repo).splitlines())
        ahead = _git("rev-list", "--count", "@{u}..HEAD", cwd=repo).strip() or "?"
        behind = _git("rev-list", "--count", "HEAD..@{u}", cwd=repo).strip() or "?"
        age = (time.time() - int(_git("log", "-1", "--format=%ct", cwd=repo).strip() or time.time())) / 3600
        flag = "LOOK" if dirty or ahead not in ("0", "?") or behind not in ("0", "?") else "ok"
        print(f"  {flag:<4} {repo.name:<40} dirty {dirty:<3} unpushed {ahead:<3} behind {behind:<3} last commit {age:6.0f}h ago")
        rows += 1
    print(f"{rows} repositories under {root}")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["oldest"]:
        return oldest(int(argv[1]) if len(argv) > 1 else 15)
    if argv[:1] == ["review"]:
        return review()
    if argv[:1] == ["repos"]:
        return repos(Path(argv[1]) if len(argv) > 1 else ROOT.parent)
    if argv[:1] == ["worktrees"]:
        return worktrees()
    print(__doc__.split("\n\n", 1)[0])
    print("usage: staleness.py oldest [N] | review | repos [root] | worktrees")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
