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
    module.CASES.append(
        (
            "identity --apply skips a published name as a whole token, never inside a longer one",
            "an owner move that rewrote five files and left every URL on the old owner",
        )
    )
    print("  ok    identity: a URL holding `thea-software` moves; `thea` itself does not")


def run(module) -> None:
    published_token_case(module)
