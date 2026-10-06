#!/usr/bin/env python3
"""Regression case for `identity.py --apply`: a published name skips its own line, never a longer name."""

from __future__ import annotations


def published_token_case(module) -> None:
    """`thea` is published, so its line is kept; `thea-software` in a URL is not `thea` and must move."""
    from identity import publishes

    published = ["thea", "thea-software-wt", "THEA_ROOT"]
    url = 'Homepage = "https://github.com/OldOwner/thea-software"'
    if publishes(url, published):
        raise SystemExit("FAIL a repository URL was skipped as if it were the published command `thea`")
    for kept in ("run `thea check`", "../thea-software-wt beside a clone", "export THEA_ROOT=x"):
        if not publishes(kept, published):
            raise SystemExit(f"FAIL a published interface was rewritten: {kept!r}")
    from identity import rename_line

    mixed = "run `thea check` against https://github.com/OldOwner/thea-software"
    moved = rename_line(mixed, published, [("OldOwner", "NewOrg")])
    if moved != "run `thea check` against https://github.com/NewOrg/thea-software":
        raise SystemExit(f"FAIL a line naming `thea` kept its old URL or lost its command: {moved!r}")
    chained = rename_line("Old/Old-Repo", [], [("Old", "New-Repo"), ("New-Repo", "Wrong")])
    if chained != "New-Repo/New-Repo-Repo":
        raise SystemExit(f"FAIL a later pair renamed what an earlier pair wrote: {chained!r}")
    from identity import _without

    slug = "oldowner-thea-software-abc123"
    if "oldowner" in _without(f"badge https://m8ven.ai/mcp/{slug}", [slug]).lower():
        raise SystemExit("FAIL a declared third-party record still counts as a stale owner")
    beside = f"https://m8ven.ai/mcp/{slug} and https://github.com/OldOwner/thea-software"
    if "oldowner" not in _without(beside, [slug]).lower():
        raise SystemExit("FAIL a record hid the whole line, so a stale owner beside it went unseen")
    from identity import names_owner

    if names_owner("https://github.com/NewOrg/old-repo", "Old-Repo", "old-repo", []):
        raise SystemExit("FAIL an owner named like its repository counted every repository URL as itself")
    if not names_owner("https://github.com/Old-Repo/old-repo", "Old-Repo", "old-repo", []):
        raise SystemExit("FAIL the old owner, in its declared casing, went unseen beside its repository")
    if not names_owner("https://github.com/oldowner/x", "OldOwner", "x", []):
        raise SystemExit("FAIL an owner unlike its repository stopped matching ignoring case")
    module.CASES.append(
        (
            "identity --apply skips a published name as a whole token, never inside a longer one",
            "an owner move that rewrote five files and left every URL on the old owner",
        )
    )
    print("  ok    identity: a URL holding `thea-software` moves; `thea` itself does not")


def run(module) -> None:
    published_token_case(module)
