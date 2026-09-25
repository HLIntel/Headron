#!/usr/bin/env python3
"""Who owns this tree, compared against the declaration — and the rename, as one operation.

WHY (2.23.0). Measured before this existed: the owner's name appeared 39 times across 13 files,
and most were LIVE — badge URLs, a CODEOWNERS handle, the `repository:` a reusable workflow checks
out, the target the platform audit points at, the banner's own filename. A rename by
find-and-replace flips all of them in one commit, and every one 404s until the account on the
other side exists. That is not a rename, it is an outage with a commit message.

THE ORDER IS THE WHOLE POINT, and it is the opposite of the intuitive one:

  1. declare the successor here, `applied: false` — reviewable before it is live
  2. `identity.py --plan` — every file that would move, with its line, read by a person
  3. create the account and MOVE the repository on the platform
  4. only then `identity.py --apply`, flip `applied: true`, and re-run the whole ladder

Doing 4 before 3 breaks every badge, the reusable workflow's checkout and the platform audit at
once, and the failure arrives for readers rather than for the person who caused it.

WHAT IT REFUSES TO REWRITE. A licence names a copyright holder at a point in time; it is a legal
record and not a pointer, so `literal_allowed` holds it out and this tool never touches it.
"""
from __future__ import annotations

import re
import sys

from atlascore import ROOT, atlas, rel, tracked

SKIP_SUFFIXES = {".webp", ".png", ".jpg", ".gz", ".zip", ".ico"}


def declared() -> dict:
    return atlas().get("identity") or {}


def _allowed() -> set[str]:
    return {str(p) for p in declared().get("literal_allowed") or []}


def sightings(owner: str) -> list[tuple[str, int, str]]:
    """(file, line number, the line) for every literal use of `owner` outside the allowed set.

    atlas.yaml is excluded because it is the DECLARATION: the one place the name is supposed to
    be written, and counting it would make the roster refuse its own source of truth.
    """
    found: list[tuple[str, int, str]] = []
    # A GENERATED FILE IS THE DECLARATION RENDERED, not an independent mention of it. The staged
    # successor is published to every runtime through the generated bootstrap record, and counting
    # that as a half-applied rename made this guard fire on the correct state — the third guard
    # this session to refuse correct work and be NARROWED rather than exempted. It cannot drift on
    # its own: check() already asserts every generated file equals what the generator produces.
    generated = {str(p) for p in atlas().get("generated_files") or []}
    for path in tracked():
        name = rel(path)
        if (name in _allowed() or name in generated or path.is_symlink()
                or not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # ONLY THE identity: BLOCK IS THE DECLARATION. Excluding all of atlas.yaml hid the chat install
        # block and the install intent at 3.0.0 — both GENERATED into CHAT.md and llms.txt, so every chat
        # was handed the old owner while this check read clean. The rest of atlas.yaml is scanned.
        in_identity = False
        for number, line in enumerate(text.splitlines(), 1):
            if name == "atlas.yaml" and line[:1] not in (" ", "#", ""):
                in_identity = line.startswith("identity:")
            if in_identity:
                continue
            if owner.lower() in line.lower():
                found.append((name, number, line.strip()[:110]))
    return found


def identity_errors() -> list[str]:
    """The declaration is complete, and a staged successor has not been half-applied.

    A half-applied rename is the dangerous state: some files point at the new owner and some at
    the old, so every reader gets a different answer depending on which file they opened.
    """
    errors: list[str] = published_errors()
    spec = declared()
    for field in ("owner", "repository", "display_name"):
        if not str(spec.get(field) or "").strip():
            errors.append(f"identity declares no {field}")
    successor = spec.get("successor") or {}
    if successor:
        for field in ("owner", "display_name", "owner_applied", "blocked_on"):
            if field == "owner_applied":
                if successor.get("owner_applied") and not successor.get("owner_confirmed"):
                    errors.append("identity/successor is applied while owner_confirmed is false — "
                                  "the owner is a URL segment, so applying an unconfirmed guess at "
                                  "an account login breaks every badge and the workflow checkout")
                if not isinstance(successor.get(field), bool):
                    errors.append("identity/successor/owner_applied must be true or false, so the tree's "
                                  "state is declared rather than inferred from whichever file was read")
                continue
            if not str(successor.get(field) or "").strip():
                errors.append(f"identity/successor declares no {field}")
        banner = str(spec.get("banner") or "")
        if banner and not (ROOT / banner).exists():
            errors.append(f"identity/banner names {banner}, which is not in the tree")
        staged_banner = str(successor.get("banner") or "")
        if successor.get("banner_applied") and staged_banner and not (ROOT / staged_banner).exists():
            errors.append(f"identity/successor/banner_applied is true and {staged_banner} is not "
                          "in the tree — an asset cannot be derived from a declaration, so this "
                          "is a claim that a file was added when it was not")
        if successor.get("banner_ready") and not successor.get("banner_applied"):
            errors.append(f"identity/successor/banner is READY and not applied: add {staged_banner} "
                          "and repoint the README's <img src> in the same commit")
        if not successor.get("banner_ready") and not str(successor.get("banner_blocked_on") or "").strip():
            errors.append("identity/successor/banner is not ready and says why nowhere — a pending "
                          "asset with no stated blocker is a stale brand nobody registered as stale")
        # ONCE A HALF IS APPLIED, THE PREVIOUS NAME MUST BE GONE. Before it is applied, the new
        # name must be ABSENT except where the declaration itself stages it — a tree carrying both
        # is the half-applied state, where every reader gets a different answer depending on which
        # file they opened.
        for half, previous in (("owner", str(spec.get("previous_owner") or "")),
                               ("repository", str(spec.get("repository") or ""))):
            done = bool(successor.get(f"{half}_applied"))
            staged = str(successor.get(half) or "")
            # NOTHING CHANGED IS NOT A HALF-APPLIED RENAME. When a staged half is decided against,
            # the successor value equals the current one and every occurrence of it is correct —
            # comparing a name to itself flagged all 64 of them. A cancelled rename is a real
            # outcome and it must not read as a broken one.
            if staged == previous:
                continue
            if done and previous:
                left = sightings(previous)
                if left:
                    errors.append(f"identity: the {half} half is applied and {len(left)} line(s) "
                                  f"still name '{previous}'. First: {left[0][0]}:{left[0][1]}")
            if not done and staged and staged != previous:
                early = sightings(staged)
                if early:
                    errors.append(f"identity: the {half} half is NOT applied and {len(early)} "
                                  f"line(s) already name '{staged}' — a half-applied rename, where "
                                  f"every reader gets a different answer. First: "
                                  f"{early[0][0]}:{early[0][1]}")
    return errors


def published_errors() -> list[str]:
    """A published interface may not be rewritten by a rename, and must still be declared.

    The environment variable is the sharp one: a consumer who keeps setting the old name is not
    told, the CLI falls back to the directory it was installed from, and it RESOLVES SOMETHING.
    A wrong answer that looks like an answer is the failure this whole repository is built around.
    """
    errors: list[str] = []
    published = declared().get("published_interfaces") or {}
    if not published:
        return ["identity declares no published_interfaces, so a rename cannot tell a string "
                "somebody outside depends on from a string only this tree reads"]
    for name, why in published.items():
        if not str(why or "").strip():
            errors.append(f"identity/published_interfaces/{name} states no consequence, which is "
                          "the only field that stops it being rewritten by the next sweep")
    return errors


def rewrite(apply: bool) -> list[str]:
    """Every file that would move, or does move — and never a published interface.

    The rename covers the owner, the display name and the repository in each declared casing. It
    SKIPS any line containing a published interface, because renaming one of those is an API
    change with a compatibility period, not a find-and-replace.
    """
    spec = declared()
    successor = spec.get("successor") or {}
    ready = [half for half in ("owner", "repository")
             if successor.get(f"{half}_ready") and not successor.get(f"{half}_applied")]
    if not successor or not ready:
        return ["no half of the successor is both READY on the platform and unapplied here — "
                "a half that is not ready would rewrite this tree to point at a name nothing serves"]
    pairs: list[tuple[str, str]] = []
    if successor.get("owner_ready") and not successor.get("owner_applied"):
        pairs += [(str(spec.get("owner")), str(successor.get("owner"))),
                  (str(spec.get("display_name")), str(successor.get("display_name")))]
    new_repo = str(successor.get("repository") or "")
    if new_repo and successor.get("repository_ready") and not successor.get("repository_applied"):
        for casing in successor.get("repository_casings") or [spec.get("repository")]:
            replacement = new_repo if str(casing)[:1].isupper() else new_repo.lower()
            pairs.append((str(casing), replacement))
    moved: list[str] = []
    for path in tracked():
        name = rel(path)
        if (name in _allowed() or name == "atlas.yaml" or path.is_symlink()
                or not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES):
            continue
        try:
            before = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        published = list(declared().get("published_interfaces") or {})
        lines = before.splitlines(keepends=True)
        for index, line in enumerate(lines):
            if any(name in line for name in published):
                continue  # an API change, not a rename — it gets a compatibility period
            for old, new in pairs:
                line = re.sub(re.escape(old), new, line)
            lines[index] = line
        after = "".join(lines)
        if after == before:
            continue
        changed = sum(1 for a, b in zip(before.splitlines(), after.splitlines()) if a != b)
        moved.append(f"{name}: {changed} line(s)")
        if apply:
            path.write_text(after, encoding="utf-8")
    return moved


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="identity.py")
    parser.add_argument("--plan", action="store_true", help="what a rename would move; changes nothing")
    parser.add_argument("--apply", action="store_true",
                        help="rewrite the tree from the declaration. Run it only AFTER the account "
                             "and repository exist on the platform — before that, every rewritten "
                             "URL resolves to nothing")
    args = parser.parse_args(argv)
    spec = declared()
    successor = spec.get("successor") or {}
    print(f"declared owner: {spec.get('owner')}/{spec.get('repository')}")
    print(f"  login (what links resolve against): {spec.get('owner')}")
    print(f"  platform display name:              {spec.get('platform_display_name')}")
    print(f"  brand used in this tree's prose:    {spec.get('display_name')}")
    if successor:
        for half in ("owner", "repository", "banner"):
            print(f"  {half:<10} ready={successor.get(f'{half}_ready')} "
                  f"applied={successor.get(f'{half}_applied')} -> {successor.get(half)}")
        print(f"blocked on: {successor.get('blocked_on')}")
    hits = sightings(str(spec.get("owner")))
    print(f"the current owner appears in {len({h[0] for h in hits})} file(s), {len(hits)} line(s); "
          f"{len(_allowed())} file(s) hold it literally by declaration and are never rewritten")
    if args.plan or args.apply:
        for line in rewrite(args.apply):
            print(("moved   " if args.apply else "WOULD MOVE  ") + line)
        if args.apply:
            print("REMEMBER: flip identity/successor/applied to true, regenerate, and run the whole "
                  "ladder. A half-applied rename gives every reader a different answer.")
    problems = identity_errors()
    for problem in problems:
        print(f"- {problem}")
    print("SCOPE: this tree. Whether the platform account exists, and whether the repository has")
    print("       been moved to it, is answered by the platform — never by this file.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
