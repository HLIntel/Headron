"""Claude Code PreToolUse adapter: refuses the pushes and bypasses the repository forbids, before they run.

It adds no rule of its own. A `git push` is judged by `.githooks/pre-push`, the same script git runs for
every runtime, fed the ref line git would send, so the rule has one copy. What this adds is the earlier
refusal inside Claude Code, and the two bypasses no git hook can see: `--no-verify` on commit and push,
and `ATLAS_LANDING=` typed by hand. `ATLAS_LANDING` is set only by `branchstate.py --land`, inside its own
process, so a shell that sets it has skipped the landing path.

Payload: Claude Code sends JSON on stdin. Anything that is not a Bash call is not ours, so it passes.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

SEPARATORS = re.compile(r"&&|\|\||;|\||\n")
DRY_RUN = {"-n", "--dry-run"}
ZERO = "0" * 40


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False, timeout=60
    ).stdout.strip()


def _subcommand(words: list[str]) -> tuple[str | None, list[str]]:
    """git's global options (-C dir, -c key=value, --no-pager) come before the subcommand."""
    i = 1
    while i < len(words):
        if words[i] in ("-C", "-c"):
            i += 2
        elif words[i].startswith("-"):
            i += 1
        else:
            return words[i], words[i + 1 :]
    return None, []


def _push_refusal(root: Path, args: list[str]) -> str | None:
    """Judge a push the way git would: build the ref line and run the tracked pre-push on it."""
    positional = [a for a in args if not a.startswith("-")]
    src, dst = "HEAD", ""
    if len(positional) >= 2:
        src, _, dst = positional[1].partition(":")
        src = src or "HEAD"
    dst = dst or src
    branch = dst.removeprefix("refs/heads/")
    if not branch:
        branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    local = ZERO if "--delete" in args else _git(root, "rev-parse", src)
    line = f"refs/heads/{src} {local} refs/heads/{branch} {ZERO}\n"
    env = {k: v for k, v in os.environ.items() if k != "ATLAS_LANDING"}
    run = subprocess.run(
        ["sh", str(root / ".githooks" / "pre-push"), "origin", "origin"],
        input=line,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        cwd=root,
        timeout=120,
    )
    return None if run.returncode == 0 else (run.stderr.strip() or f"pre-push refused '{branch}'")


def refusal(command: str, root: Path) -> str | None:
    """The reason to refuse this shell command, or None. Only git segments are judged."""
    if re.search(r"(^|[\s;&|])ATLAS_LANDING=", command):
        return "ATLAS_LANDING is set by branchstate.py --land only; a shell that sets it skips the landing path."
    for segment in SEPARATORS.split(command):
        try:
            words = shlex.split(segment, comments=True)
        except ValueError:
            if re.search(r"\bgit\b.*\b(push|commit)\b", segment):
                return "unparseable git push or commit refused; write the command plainly."
            continue
        k = 0
        while k < len(words) and "=" in words[k] and not words[k].startswith("-"):
            k += 1
        if k >= len(words) or words[k] != "git":
            continue
        sub, args = _subcommand(words[k:])
        if sub == "commit" and ("--no-verify" in args or "-n" in args):
            return "commit --no-verify skips the fast rungs in .githooks/pre-commit; that bypass is the owner's call."
        if sub == "push":
            if "--no-verify" in args:
                return "push --no-verify skips .githooks/pre-push; land with python scripts/branchstate.py --land."
            if any(a in DRY_RUN for a in args):
                continue
            why = _push_refusal(root, args)
            if why:
                return why
    return None


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("usage: claude_hook.py  (Claude Code PreToolUse adapter: reads the JSON payload on stdin)")
        return 0
    try:
        payload = json.loads(sys.stdin.read())
    except ValueError:
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    cwd = Path(payload.get("cwd") or ".")
    root = Path(_git(cwd, "rev-parse", "--show-toplevel") or cwd)
    if not (root / ".githooks" / "pre-push").is_file():
        return 0  # not a repository this adapter guards
    why = refusal(str((payload.get("tool_input") or {}).get("command", "")), root)
    if why:
        print(why, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
