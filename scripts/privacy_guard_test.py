#!/usr/bin/env python3
"""Each refusal of privacy_guard.py must fire on a seeded leak, and each clean case must pass.

Every case builds a throwaway git repository, so the guard is exercised as the hooks run it.
A mutant of the guard (scripts/privacy_guard_mutants.tsv) must make one of these cases fail.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

GUARD = Path(__file__).resolve().parent / "privacy_guard.py"
FAILED: list[str] = []
TIMEOUT_S = 60

# Split so this file carries no address of its own: the tree sweep and leaks.py read it too.
AT = "@"
BAT = b"@"
# Removed at exit, so a gate that runs on every push leaves no directory per case behind.
SCRATCH = tempfile.TemporaryDirectory()


def own_env() -> dict[str, str]:
    """The environment without git's: a hook exports GIT_DIR, and `git -C <fixture> init` obeys it over -C.

    Inherited, this fixture's init and config rewrote the real repository's core.bare and user.* mid-push.
    """
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        timeout=TIMEOUT_S,
        env={**own_env(), "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
    )


def hook_env_stays_out() -> None:
    """A fixture built under a hook's GIT_DIR must leave the repository that GIT_DIR names untouched."""
    decoy = Path(tempfile.mkdtemp(dir=SCRATCH.name))
    git(decoy, "init", "-q")
    config = decoy / ".git" / "config"
    before = config.read_bytes()
    saved = os.environ.get("GIT_DIR")
    os.environ["GIT_DIR"] = str(decoy / ".git")
    try:
        repo_with({"a.txt": b"ok\n"})
    except subprocess.CalledProcessError as exc:
        FAILED.append(f"fixture under GIT_DIR: {exc}")
    finally:
        if saved is None:
            del os.environ["GIT_DIR"]
        else:
            os.environ["GIT_DIR"] = saved
    if config.read_bytes() != before:
        FAILED.append("fixture under GIT_DIR: it rewrote the config of the repository GIT_DIR names")


def repo_with(files: dict[str, bytes], denylist: str | None = None) -> tuple[Path, dict[str, str]]:
    root = Path(tempfile.mkdtemp(dir=SCRATCH.name))
    git(root, "init", "-q")
    git(root, "config", "user.email", "202" + AT + "users.noreply.github.com")
    git(root, "config", "user.name", "tester")
    for name, data in files.items():
        (root / name).write_bytes(data)
    git(root, "add", "-A")
    env = {**own_env(), "HEADRON_PRIVACY_DENY": str(root.parent / "absent.deny")}
    if denylist is not None:
        deny = root.parent / (root.name + ".deny")
        deny.write_text(denylist, encoding="utf-8")
        env["HEADRON_PRIVACY_DENY"] = str(deny)
    return root, env


def run(mode: str, files: dict[str, bytes], denylist: str | None = None) -> tuple[int, str]:
    root, env = repo_with(files, denylist)
    done = subprocess.run(
        [sys.executable, str(GUARD), mode], cwd=root, env=env, capture_output=True, text=True, timeout=TIMEOUT_S
    )
    return done.returncode, done.stderr + done.stdout


def expect(
    label: str, rc_want: int, mode: str, files: dict[str, bytes], needle: str | None = None, denylist: str | None = None
) -> None:
    rc, out = run(mode, files, denylist)
    ok = rc == rc_want and (needle is None or needle in out)
    if not ok:
        FAILED.append(f"{label}: rc={rc} want={rc_want} out={out[-300:]!r}")


def main() -> int:
    hook_env_stays_out()
    # email: a real-looking address is refused, a placeholder domain is not
    expect("email refused", 1, "--staged", {"a.txt": b"reach jane" + BAT + b"acme.io now\n"}, "email")
    expect("placeholder email clean", 0, "--staged", {"a.txt": b"reach jane" + BAT + b"example.com now\n"})
    # home path: a personal home is refused, the placeholder /home/u is not
    expect("home refused", 1, "--staged", {"a.txt": b"open /Us" + b"ers/alice/x\n"}, "home path")
    expect("placeholder home clean", 0, "--staged", {"a.txt": b"open /home/u/x\n"})
    # secrets: a key shape is refused, and the redaction keeps the tail out of the output
    key = b"k = AKIA" + b"ABCDEFGHIJKLMNOP\n"
    expect("aws key refused", 1, "--staged", {"a.txt": key}, "AWS access key")
    expect("key value redacted", 1, "--staged", {"a.txt": key}, "AKI***")
    expect("pem refused", 1, "--staged", {"a.txt": b"-----BEGIN RSA " + b"PRIVATE KEY-----\n"}, "PEM")
    # the escape marker is the only way past a finding
    expect("escape clean", 0, "--staged", {"a.txt": b"open /Us" + b"ers/alice/x  # privacy: allow\n"})
    # identity: a non-noreply author is refused on the next commit
    root, env = repo_with({"a.txt": b"ok\n"})
    git(root, "config", "user.email", "jane" + AT + "acme.io")
    done = subprocess.run(
        [sys.executable, str(GUARD), "--staged"], cwd=root, env=env, capture_output=True, text=True, timeout=TIMEOUT_S
    )
    if done.returncode != 1 or "identity" not in done.stderr:
        FAILED.append(f"identity refused: rc={done.returncode} out={done.stderr[-200:]!r}")
    # the Co-Authored-By trailer of the coding agent is a noreply address and passes
    expect(
        "noreply trailer clean",
        0,
        "--staged",
        {"a.txt": b"Co-Authored-By: Claude <noreply" + BAT + b"anthropic.com>\n"},
    )
    # a bare noreply local part on any domain is a role address, not a person
    expect("noreply local part clean", 0, "--staged", {"a.txt": b"send to noreply" + BAT + b"acme.io\n"})
    expect("github noreply clean", 0, "--staged", {"a.txt": b"user" + BAT + b"users.noreply.github.com\n"})
    expect("noreply lookalike refused", 1, "--staged", {"a.txt": b"user" + BAT + b"evilnoreply.github.com\n"}, "email")
    # names: a denylisted term is refused, the rule is off without its file (named on stderr)
    expect("name refused", 1, "--staged", {"a.txt": b"written by Zorblax\n"}, "name", denylist="zorblax\n")
    expect("name clean without term", 0, "--staged", {"a.txt": b"written by nobody\n"}, denylist="zorblax\n")
    # binary files are skipped by the tree sweep; the text rules run on text only
    expect("binary skipped", 0, "--tree", {"b.bin": b"\x00\x01AKIA" + b"ABCDEFGHIJKLMNOP"})
    # --help answers and scans nothing: the leak below would refuse if the flag fell through to a mode
    expect("help answers", 0, "--help", {"a.txt": key}, "--staged")
    if FAILED:
        print("privacy_guard_test: FAILED", *FAILED, sep="\n  ")
        return 1
    print("privacy_guard_test: ok (17 cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
