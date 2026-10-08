#!/usr/bin/env python3
"""Regression case for `identity.py --apply`: a published name skips its own line, never a longer name."""

from __future__ import annotations

import tempfile
from pathlib import Path


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


def private_terms_cases(module) -> None:
    """The owner's private names are refused from a list this tree never carries (3.45.0)."""
    import os

    import leaks

    term = "quux" + "fleetname"  # assembled, so the tree itself never contains the planted term
    with (
        tempfile.TemporaryDirectory() as scratch,
        module.mutated("README.md", lambda s: s.replace("public on purpose", f"public on purpose {term}", 1)),
    ):
        terms = Path(scratch, "terms.txt")
        terms.write_text(f"# the owner's names\n{term.upper()}\n")  # listed in another case: the match is case-blind
        saved = {k: os.environ.pop(k, None) for k in ("THEA_PRIVATE_TERMS", "GIT_CONFIG_COUNT")}

        def errs(env: dict, needle: str) -> list:
            os.environ.update(env)
            try:
                return [e for e in leaks.leak_errors() if needle in e]
            finally:
                [os.environ.pop(k, None) for k in env]

        refused, unset = errs({"THEA_PRIVATE_TERMS": str(terms)}, term.upper()), errs({}, term.upper())
        via_git = errs(
            {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "thea.privateTerms", "GIT_CONFIG_VALUE_0": str(terms)},
            term.upper(),
        )
        blind = errs({"THEA_PRIVATE_TERMS": str(Path(scratch, "absent.txt"))}, "THEA_PRIVATE_TERMS")
        Path(scratch, ".owner-keys.env").touch(), Path(scratch, ".secrets.env").touch()
        os.environ["THEA_PRIVATE_TERMS"] = str(terms)  # the host's names JOIN a declared list
        host = leaks.host_secret_names(scratch) if ".owner-keys.env" in leaks.private_terms(scratch) else ()
        terms.write_text("# a list with no name in it\n")
        empty = errs({"THEA_PRIVATE_TERMS": str(terms)}, "THEA_PRIVATE_TERMS")
        os.environ.update({k: v for k, v in saved.items() if v is not None})
    if not refused or unset or not via_git or host != (".owner-keys.env",) or not blind or not empty:
        raise SystemExit(f"FAIL private terms: {refused=} {unset=} {via_git=} {host=} {blind=} {empty=}")
    module.CASES.append(
        (
            "a declared private-term list that is missing or empty is refused, never read as clean",
            "THEA_PRIVATE_TERMS pointing at a moved file, and every private name passing as no finding",
        )
    )
    module.CASES.append(
        (
            "a list declared in git config binds every shell, and the host's own keys-file names join it",
            "the list set in one agent's settings: a terminal commit passed blind and the keys-file name shipped",
        )
    )
    module.CASES.append(
        (
            "a private name in the tree is refused when the owner's untracked list names it",
            "the owner's projects and routers written into a public atlas, found by a reader first",
        )
    )
    print("  ok    private names are refused from a list the tree never carries")


def run(module) -> None:
    published_token_case(module)
    private_terms_cases(module)
