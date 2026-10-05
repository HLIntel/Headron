#!/usr/bin/env python3
"""mdshape — every Markdown file has a class, and each class has a rule: bounded, preserved, or reachable.

WHY (3.44.0). Markdown is what every agent reads, so a bloated note is a per-session cost and a stale one
teaches the wrong thing. Two opposite disciplines both hold, and a file must say which one it is under:

  living     rewritten in place — no narration ("was X, now Y", ~~struck~~ text, UPDATE: blocks), a byte
             cap, and reachable: linked from an entry chain or named by path in another tracked file
  record     preserved — dated notes, archives, ledgers, changelogs: APPEND-ONLY, never edited back, and
             rotated into an archive when it outgrows its own cap, because unbounded growth is still a defect
  generated  owned by a generator, whose declaration is the thing to change; never hand-edited

The class comes from the path (atlas.yaml/markdown_policy, overridable by a consumer's own .atlas.yaml),
first matching pattern wins, and anything unmatched is LIVING — the strict default, so a new file is
bounded until someone declares it a record.

    mdshape.py [<repo>]            size, narration and flow over every tracked .md in the caller's tree
    mdshape.py --staged            the commit gate: a staged record may only GROW (no deleted line)
    mdshape.py --base <ref>        the same, against a ref: a branch may not rewrite a record

WHAT IT DOES NOT PROVE: that a living note is CORRECT, or that a record was right when written. It proves
the shape a reader relies on — a living note is current by construction, a record is exactly what was seen.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from atlascore import ROOT, atlas, ls_files, strict_yaml

NARRATION = re.compile(
    r"(?<!~)~~(?!~)[^~\n]+~~(?!~)|^\s*(?:UPDATE|EDIT|Update|Edit)\b[^:\n]{0,40}:|\((?:was|formerly) [^)]{1,60}\)", re.M
)
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def policy(tree: Path) -> dict:
    """Thea's declaration, with a consumer's `.atlas.yaml/markdown_policy` keys laid over it."""
    base = dict(atlas().get("markdown_policy") or {})
    if tree == ROOT.resolve():  # this tree's generated files are declared once, in generated_files
        base["generated"] = [
            *(base.get("generated") or []),
            *(f"^{re.escape(str(g))}$" for g in atlas().get("generated_files") or []),
        ]
    own = tree / ".atlas.yaml"
    if tree != ROOT.resolve() and own.is_file():
        local = (strict_yaml(own.read_text(encoding="utf-8"), ".atlas.yaml") or {}).get("markdown_policy") or {}
        base.update(local)
    return base


def md_class(rel: str, spec: dict) -> str:
    for name in ("generated", "record"):
        if any(re.search(p, rel) for p in spec.get(name) or []):
            return name
    return "living"


def tracked_md(tree: Path) -> list[str]:
    return sorted(ls_files(tree, "*.md"))


def size_errors(tree: Path, files: list[str], spec: dict) -> list[str]:
    """A living note over its cap is split; a record over its cap is rotated. The oversize map is a
    ratchet: it names today's bytes, may only fall, and refuses a number the file no longer needs."""
    errors: list[str] = []
    living, record = int(spec.get("living_max_bytes") or 16384), int(spec.get("record_max_bytes") or 131072)
    oversize = {str(k): int(v) for k, v in (spec.get("oversize") or {}).items()}
    for rel in files:
        size, kind = (tree / rel).stat().st_size, md_class(rel, spec)
        if kind == "living" and rel in oversize:
            if size > oversize[rel]:
                errors.append(
                    f"{rel}: {size} B grew past its oversize ratchet {oversize[rel]} B — split it into its subtree"
                )
            elif size < oversize[rel]:
                errors.append(f"{rel}: {size} B — lower markdown_policy/oversize to {size} (a ratchet only falls)")
        elif kind == "living" and size > living:
            errors.append(
                f"{rel}: {size} B is a bloated living note (cap {living} B) — split it into linked files "
                "under its own directory, or declare it a record if it is history"
            )
        elif kind == "record" and size > record:
            errors.append(f"{rel}: {size} B record over {record} B — rotate the oldest entries into an archive file")
    errors += [
        f"markdown_policy/oversize names {rel}, which is not a tracked living note"
        for rel in oversize
        if rel not in files or md_class(rel, spec) != "living"
    ]
    return errors


def narration_errors(tree: Path, files: list[str], spec: dict) -> list[str]:
    """A living note is current: no struck text, no UPDATE blocks, no "(was X)". Git holds the history."""
    errors = []
    for rel in files:
        if md_class(rel, spec) != "living":
            continue
        text = re.sub(r"(?ms)^(```|~~~).*?^\1", "", (tree / rel).read_text(encoding="utf-8", errors="replace"))
        hit = NARRATION.search(text)
        if hit:
            errors.append(
                f"{rel}: narration in a living note ({hit.group(0).strip()[:50]!r}) — rewrite the "
                "line as it is now; the past belongs to git"
            )
    return errors


def flow_errors(tree: Path, files: list[str], spec: dict) -> list[str]:
    """Every living note is reachable: linked from an entry chain, or named by path in another tracked file.
    An unreachable note is read by nobody and still costs whoever greps the tree."""
    entries = [e for e in spec.get("entries") or ["README.md"] if (tree / e).is_file()]
    loaded = tuple(spec.get("loaded_by_harness") or [])
    edges: dict[str, set[str]] = {}
    for rel in files:
        found = set()
        for target in LINK.findall((tree / rel).read_text(encoding="utf-8", errors="replace")):
            q = (tree / rel).parent / target
            q = next((q / e for e in ("THEA.md", "README.md", "INDEX.md") if (q / e).is_file()), q) if q.is_dir() else q
            try:
                found.add(q.resolve().relative_to(tree).as_posix())
            except (ValueError, OSError):
                continue
        edges[rel] = found
    seen, stack = set(entries), list(entries)
    while stack:
        for nxt in edges.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    unreached = [r for r in files if r not in seen and md_class(r, spec) == "living" and not r.startswith(loaded)]
    if not unreached:
        return []
    named = subprocess.run(
        ["git", "grep", "-l", "-F", *[a for r in unreached for a in ("-e", r)]],
        cwd=tree,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    ).stdout.split()
    mentioned = {r for r in unreached for n in named if n != r and r in (tree / n).read_text(errors="replace")}
    return [
        f"{r}: a living note no entry reaches and no tracked file names — link it from its directory's "
        "entry, or delete it"
        for r in unreached
        if r not in mentioned
    ]


def preservation_errors(tree: Path, spec: dict, base: str | None) -> list[str]:
    """A record only grows. Staged (or since `base`), a record with a removed line is refused — except the
    one line atlas.yaml/version_sites declares for it, which every release rewrites by design."""
    diff = ["git", "diff", "-U0", "--no-renames"] + (["--cached"] if base is None else [base])
    out = subprocess.run(
        [*diff, "--", "*.md"], cwd=tree, capture_output=True, text=True, check=False, timeout=600
    ).stdout
    sites = (
        {str(k): re.compile(str(v)) for k, v in (atlas().get("version_sites") or {}).items()}
        if tree == ROOT.resolve()
        else {}
    )
    removed: dict[str, int] = {}
    rel = ""
    for line in out.splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            rel = line[6:] if line.startswith("--- a/") else rel
            continue
        if (
            line.startswith("-")
            and md_class(rel, spec) == "record"
            and not (rel in sites and sites[rel].search(line[1:]))
        ):
            removed[rel] = removed.get(rel, 0) + 1
    return [
        f"{rel}: {n} line(s) removed from a record — records are append-only; add a correcting entry "
        "instead of editing history"
        for rel, n in removed.items()
    ]


def tree_errors(tree: Path) -> list[str]:
    spec, files = policy(tree), tracked_md(tree)
    if not files:
        return ["no tracked Markdown — the sweep found nothing, which is a broken probe, not a clean tree"]
    return size_errors(tree, files, spec) + narration_errors(tree, files, spec) + flow_errors(tree, files, spec)


def main(argv: list[str]) -> int:
    from atlascore import worktree  # noqa: PLC0415

    base = argv[argv.index("--base") + 1] if "--base" in argv else None
    paths = [a for a in argv if not a.startswith("--") and a != base]
    tree = Path(paths[0]).resolve() if paths else worktree()
    problems = preservation_errors(tree, policy(tree), base) if "--staged" in argv or base else tree_errors(tree)
    for p in problems:
        print(f"  {p}")
    print(f"mdshape: {len(tracked_md(tree))} Markdown file(s) in {tree.name}, {len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
