#!/usr/bin/env python3
"""claude_hook: what pre-push refuses, plus the two bypasses git cannot see and the payload it cannot read."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claude_hook


def run(module: ModuleType | None) -> None:
    """The Claude Code adapter refuses what the pre-push refuses, plus the two bypasses git cannot see."""
    cases = getattr(module, "CASES", [])
    table = [
        ("git push origin feat/x", True),  # the bare push
        ("git push --force origin feat/x", True),  # a force is a lane push, refused the same way
        ("git push --force-with-lease origin feat/x", True),
        ("git push --no-verify origin feat/x", True),  # skips the hook itself
        ("git commit --no-verify -m wip", True),  # skips the fast rungs
        ("ATLAS_LANDING=1 git push origin feat/x", True),  # a hand-set landing is not a landing
        ("ls -la && git push -u origin feat/x", True),  # refused inside a chain
        ("python scripts/branchstate.py --land", False),  # the only lane path
        ("git push --dry-run origin feat/x", False),
        ("git status && ls -la", False),
    ]
    for command, refused in table:
        got = claude_hook.refusal(command, Path(claude_hook.__file__).resolve().parents[1])
        assert bool(got) == refused, f"{command!r}: refused={bool(got)}, wanted {refused}: {got}"
    cases.append(
        (
            f"claude hook: {sum(r for _, r in table)} bypasses and bare pushes refused, "
            f"{sum(not r for _, r in table)} legitimate commands admitted",
            "an agent runtime that pushes a lane bare or skips the hook with --no-verify",
        )
    )
    print("  ok    claude hook: bare, forced, --no-verify and hand-set landings refused; --land admitted")

    # Exit 1 is a pass to Claude Code, so the stdin the adapter cannot read must exit 2, and what is simply not ours 0.
    stdin = sys.stdin
    try:
        for raw, wanted in (
            (b" " * (1024 * 1024 + 1), 2),
            (b"\xff", 2),
            (b"not json", 0),
            (b'{"tool_name": "Read"}', 0),
        ):
            sys.stdin = io.TextIOWrapper(io.BytesIO(raw))
            assert claude_hook.main() == wanted, f"{raw[:12]!r}: wanted exit {wanted}"
    finally:
        sys.stdin = stdin
    cases.append(
        (
            "claude hook: a payload it cannot read blocks with exit 2; one that is not ours passes",
            "a push hidden in an oversized payload, which read_stdin's exit 1 would let through",
        )
    )
    print("  ok    claude hook: unreadable stdin blocks; other tools pass")


if __name__ == "__main__":
    run(None)
