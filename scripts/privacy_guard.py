#!/usr/bin/env python3
"""Refuse personal data and secrets before they reach a commit, a push, or the shared history.

WHY (contract 3.61.0). The history of this repository carried personal email addresses, a personal name
and home-directory paths from the machine's own git identity, and a third party's name in messages
and filenames. Nothing refused them: the identity came from a global git config, and no rule read
the text. The rewrite that removed them changed every commit hash after it. This guard is the rule
that reads the text, so the leak is refused where it is made.

MODES
  --staged        added lines in the index, and the identity the next commit will carry
  --range A..B    author and committer, message, and added lines of every commit in A..B
                  (no argument: A is the merge-base of origin/main and HEAD)
  --tree          every tracked text file as it stands

RULES (a finding prints file:line and a redacted value, never the whole value)
  identity  an author or committer email that is not a GitHub noreply address
  email     an email address outside the placeholder domains and noreply addresses
  home      a /Users/<name> or /home/<name> path outside the placeholder names
  secret    a key shape: AWS, GitHub, Stripe, Slack, Google, Clerk, or a PEM private key
  name      a term from the personal denylist (see DENYLIST below)

ESCAPE. A line that carries the marker `privacy: allow` is not refused. Use it for a fixture that
must hold the shape. Do not use it to excuse a real value; rotate the value and remove it instead.

DENYLIST. The personal terms are NEVER written into this repository, because a list of them is
itself the leak. They live in the file named by $HEADRON_PRIVACY_DENY, or else
~/.config/headron/privacy-deny.txt: one term per line, `#` for comments. When that file is missing
the name rule is off, and the guard says so on stderr. The other rules always run.

Exit 0 is clean. Exit 1 names every finding. Exit 2 is a usage or git error.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from atlascore import ls_files, text_of

PLACEHOLDER_EMAIL_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "example.invalid",
    "example.test",
    "localhost",
}
PLACEHOLDER_HOMES = {"u", "user", "you", "example", "runner", "home", "name"}
ESCAPE = "privacy: allow"

SECRET_SHAPES = [
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("Stripe key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{10,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Clerk secret", re.compile(r"\bsk_(?:live|test)_[0-9A-Za-z]{20,}\b")),
    ("PEM private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY")),
]
EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]{2,}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
HOME = re.compile(r"/(?:Users|home)/([A-Za-z0-9._-]+)")


GIT_TIMEOUT_S = 60


def git(*args: str, check: bool = True) -> str:
    try:
        done = subprocess.run(["git", *args], capture_output=True, text=True, errors="replace", timeout=GIT_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"privacy_guard: git {' '.join(args)} timed out after {GIT_TIMEOUT_S}s\n")
        raise SystemExit(2)
    if check and done.returncode != 0:
        sys.stderr.write(f"privacy_guard: git {' '.join(args)} failed: {done.stderr.strip()}\n")
        raise SystemExit(2)
    return done.stdout


def redact(value: str) -> str:
    return value[:3] + "***" if len(value) > 3 else "***"


def is_noreply(email: str) -> bool:
    local, _, domain = email.lower().partition("@")
    return (
        (domain == "noreply.github.com" or domain.endswith(".noreply.github.com"))
        or local == "noreply"
        or domain in {"github.com", "anthropic.com", "cursor.com"}
        and local.startswith("noreply")
    )


def email_ok(email: str) -> bool:
    local, _, domain = email.lower().partition("@")
    return (
        is_noreply(email)
        or domain in PLACEHOLDER_EMAIL_DOMAINS
        or domain.endswith(".invalid")
        or domain.endswith(".test")
    )


def load_denylist() -> list[re.Pattern[str]] | None:
    path = Path(os.environ.get("HEADRON_PRIVACY_DENY") or Path.home() / ".config/headron/privacy-deny.txt")
    if not path.is_file():
        return None
    terms = [t.strip() for t in text_of(path).splitlines() if t.strip() and not t.lstrip().startswith("#")]
    return [re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.IGNORECASE) for t in terms]


def scan_line(where: str, text: str, names: list[re.Pattern[str]] | None, findings: list[str]) -> None:
    if ESCAPE in text:
        return
    for m in EMAIL.finditer(text):
        if not email_ok(m.group(0)):
            findings.append(f"{where}: email: {redact(m.group(0))}")
    for m in HOME.finditer(text):
        if m.group(1).lower() not in PLACEHOLDER_HOMES:
            findings.append(f"{where}: home path: {redact(m.group(0))}")
    for label, rx in SECRET_SHAPES:
        for m in rx.finditer(text):
            findings.append(f"{where}: secret ({label}): {redact(m.group(0))}")
    for rx in names or []:
        for m in rx.finditer(text):
            findings.append(f"{where}: name: {redact(m.group(0))}")


def check_identity(where: str, ident: str, findings: list[str]) -> None:
    email = ident.strip()
    if "<" in email:
        email = email.split("<", 1)[1].split(">", 1)[0]
    if email and not is_noreply(email):
        findings.append(f"{where}: identity: {redact(email)} is not a GitHub noreply address")


def added_lines(diff: str):
    """Yield (path, line_no, text) for each added line of a unified diff with -U0."""
    path, line_no = "?", 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) if m else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            yield path, line_no, raw[1:]
            line_no += 1


def mode_staged(names: list[re.Pattern[str]] | None, findings: list[str]) -> None:
    for line in git("var", "GIT_AUTHOR_IDENT", check=False).splitlines()[:1]:
        check_identity("next commit author", line, findings)
    for line in git("var", "GIT_COMMITTER_IDENT", check=False).splitlines()[:1]:
        check_identity("next commit committer", line, findings)
    diff = git("diff", "--cached", "-U0", "--no-color", "--diff-filter=ACMR")
    for path, n, text in added_lines(diff):
        scan_line(f"{path}:{n}", text, names, findings)


def mode_range(base: str, names: list[re.Pattern[str]] | None, findings: list[str]) -> None:
    fields = "%H%x00%an%x00%ae%x00%cn%x00%ce%x00%B%x1e"
    for record in git("log", f"--format={fields}", "--no-color", f"{base}..HEAD").split("\x1e"):
        if not record.strip():
            continue
        sha, an, ae, cn, ce, body = (record.lstrip("\n").split("\x00") + [""] * 6)[:6]
        check_identity(f"{sha[:7]} author", ae, findings)
        check_identity(f"{sha[:7]} committer", ce, findings)
        scan_line(f"{sha[:7]} message", body, names, findings)
    diff = git("log", "-p", "-U0", "--no-color", "--format=", f"{base}..HEAD")
    for path, n, text in added_lines(diff):
        scan_line(f"{path}:{n}", text, names, findings)


def mode_tree(names: list[re.Pattern[str]] | None, findings: list[str]) -> None:
    for path in ls_files(Path.cwd()):
        if not Path(path).is_file():
            continue
        data = Path(path).read_bytes()
        if b"\x00" in data[:8000]:
            continue
        for n, text in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            scan_line(f"{path}:{n}", text, names, findings)


def default_base() -> str | None:
    try:
        done = subprocess.run(
            ["git", "merge-base", "origin/main", "HEAD"], capture_output=True, text=True, timeout=GIT_TIMEOUT_S
        )
    except subprocess.TimeoutExpired:
        return None
    return done.stdout.strip() or None if done.returncode == 0 else None


def main(argv: list[str]) -> int:
    if {"-h", "--help"} & set(argv):  # a script with no parser would RUN on --help
        print(__doc__)
        return 0
    if not argv or argv[0] not in {"--staged", "--range", "--tree"}:
        sys.stderr.write(__doc__ or "usage: privacy_guard.py --staged | --range [A..B] | --tree\n")
        return 2
    names = load_denylist()
    if names is None:
        sys.stderr.write("privacy_guard: name rule OFF (no denylist file; set HEADRON_PRIVACY_DENY)\n")
    findings: list[str] = []
    if argv[0] == "--staged":
        mode_staged(names, findings)
    elif argv[0] == "--range":
        base = argv[1].split("..")[0] if len(argv) > 1 else default_base()
        if not base:
            sys.stderr.write("privacy_guard: no origin/main to diff against; range skipped, tree swept\n")
            mode_tree(names, findings)
        else:
            mode_range(base, names, findings)
    else:
        mode_tree(names, findings)
    for f in findings:
        print(f"privacy_guard: REFUSED {f}", file=sys.stderr)
    if findings:
        print(
            f"privacy_guard: {len(findings)} finding(s). Fix the value, or mark a fixture line `{ESCAPE}`.",
            file=sys.stderr,
        )
        return 1
    print(f"privacy_guard: clean ({argv[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
