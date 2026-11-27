#!/usr/bin/env python3
"""Merge generated text by regenerating it, never by hand.

MEASURED ON 14 LANE MERGES: 22 file conflicts, 18 of them in generated text (README.md 7,
.agent/facts.json 5, docs/MODULES.md 2, four more one each), 3 in hand-set shard pins, 1 in real
code. A conflict inside text a generator writes has one right answer, the generator's, and a hand
resolution of it is a second way to be wrong. So git is told, through .gitattributes, which paths
hold generated text, and this driver takes the generated parts out of the merge:

- `merge=headron-generated` (a whole generated file): keep ours; the merge commit regenerates it.
- `merge=headron-blocks` (a document with generated blocks): every block's body on the base and
  theirs side is set to ours before `git merge-file`, so only hand-written lines can conflict.
  A real conflict outside a block still stops the merge.

The regeneration is `regen`: `atlas.py index --write`, then only the generated paths it changed
are staged. pre-commit runs it while MERGE_HEAD exists. pre-merge-commit runs `regen --stop`, which
refuses the merge commit when it staged anything, because git writes a merge commit from the index
as it stood BEFORE that hook (measured: the staged regeneration was left out of the commit). The
merge stops with MERGE_HEAD set, and `git commit --no-edit` concludes it through pre-commit, whose
index git does re-read. A clone whose hooks are off gets ours-side bodies, which `atlas.py check`
reports as stale: never silent.

STDLIB ONLY, ON PURPOSE: the driver runs mid-merge, when any module of this tree may hold conflict
markers. Importing the generator here would make a code conflict break the merge of every document.
The path lists live in .gitattributes; `atlasgen.merge_attribute_errors` checks them against the
generator's own registries, so the two cannot drift.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

WHOLE, BLOCKS = "headron-generated", "headron-blocks"
DRIVERS = {
    WHOLE: ("generated file: keep ours, regenerate", "uv run --frozen python scripts/mergegen.py ours %A"),
    BLOCKS: (
        "generated blocks: merge prose only, regenerate",
        "uv run --frozen python scripts/mergegen.py blocks %O %A %B %P",
    ),
}
BLOCK = re.compile(r"(<!-- BEGIN generated: (\S+)[^>]*-->)(.*?)(<!-- END generated: \2 -->)", re.S)


def _git(*args: str, check: bool = True, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check, timeout=600, cwd=cwd).stdout


def bodies(text: str) -> dict[str, str]:
    return {m.group(2): m.group(3) for m in BLOCK.finditer(text)}


def with_bodies(text: str, wanted: dict[str, str]) -> str:
    """Set every block named in `wanted` to that body; blocks it does not name are left alone."""
    return BLOCK.sub(lambda m: m.group(1) + wanted.get(m.group(2), m.group(3)) + m.group(4), text)


def merge_blocks(base: Path, ours: Path, theirs: Path, label: str) -> int:
    """Three-way merge of the hand-written lines; ours keeps the result. Exit 0 = clean."""
    mine = bodies(ours.read_text(encoding="utf-8"))
    for side in (base, theirs):
        side.write_text(with_bodies(side.read_text(encoding="utf-8"), mine), encoding="utf-8")
    run = subprocess.run(
        [
            "git",
            "merge-file",
            "-L",
            f"ours:{label}",
            "-L",
            "base",
            "-L",
            f"theirs:{label}",
            str(ours),
            str(base),
            str(theirs),
        ],
        capture_output=True,
        timeout=600,
    )
    return 0 if run.returncode == 0 else 1


def install() -> int:
    """Define both drivers in this clone's config. An undefined driver is a silent plain merge."""
    for name, (title, command) in DRIVERS.items():
        for key, value in (("name", title), ("driver", command)):
            if _git("config", "--get", f"merge.{name}.{key}", check=False).strip() != value:
                _git("config", f"merge.{name}.{key}", value)
    return 0


ATTRIBUTE = re.compile(r"^/(\S+)\s+merge=(\S+)\s*$")


def declared(root: Path) -> dict[str, str]:
    """Path -> driver, read from the anchored `/path merge=driver` lines of .gitattributes.

    No listing and no import: regen runs right after a conflicted merge. atlasgen.merge_attribute_errors
    checks these lines against git check-attr over every tracked path, so a glob line cannot hide here.
    """
    attributes = root / ".gitattributes"
    text = attributes.read_text(encoding="utf-8") if attributes.exists() else ""
    return {m[1]: m[2] for line in text.splitlines() if (m := ATTRIBUTE.match(line)) and m[2] in DRIVERS}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def regen(stop: bool = False) -> int:
    """Regenerate inside a merge and stage only the generated paths that changed; 3 = staged, stop."""
    root = Path(_git("rev-parse", "--show-toplevel").strip())
    paths = sorted(declared(root))
    before = {p: _digest(root / p) for p in paths}
    run = subprocess.run(
        [sys.executable, "scripts/atlas.py", "index", "--write"], cwd=root, capture_output=True, text=True, timeout=600
    )
    if run.returncode:
        print(f"mergegen: index --write failed:\n{run.stdout[-1500:]}{run.stderr[-1500:]}", file=sys.stderr)
        return 1
    changed = [p for p in paths if _digest(root / p) != before[p]]
    if changed:
        _git("add", "--", *changed)
        print(f"mergegen: regenerated {len(changed)} generated path(s) for the merge commit", file=sys.stderr)
        if stop:
            print(
                "mergegen: git leaves them out of a merge commit it writes itself; "
                "conclude the merge with `git commit --no-edit`",
                file=sys.stderr,
            )
            return 3
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["ours"] and len(args) == 2:
        return 0  # %A already holds ours: the merge commit's regeneration writes the right text
    if args[:1] == ["blocks"] and len(args) == 5:
        return merge_blocks(Path(args[1]), Path(args[2]), Path(args[3]), args[4])
    if args == ["install"]:
        return install()
    if args[:1] == ["regen"] and args[1:] in ([], ["--stop"]):
        return regen(stop=args[1:] == ["--stop"])
    print("usage: mergegen.py ours %A | blocks %O %A %B %P | install | regen [--stop]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
