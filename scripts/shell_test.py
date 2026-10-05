"""Planted cases for shell_verdict: the silent shell shapes are refused and correct commands are not.

Split out of atlas_guards_test.py at 3.50.0, which sat at the line cap when the per-statement cases were
added. Run inside atlas_test's counted main, like handoff_test and schedtargets_test.
"""

from __future__ import annotations


def run(module) -> None:
    """The silent shell shapes are refused, and correct commands are NOT (3.27.0).

    Specificity first: a guard that fires on a deliberate subshell or an honest message gets switched off,
    and these five standing verdicts existed precisely because nothing in this tree could judge a shell.
    """
    from agentpolicy import policy, shell_verdict

    tick = chr(96)  # built at run time: a literal backtick here would be substituted in this very file
    refused = {
        "sourced file in a pipeline": "source .venv/bin/activate | tee log",
        "$? after a filter": "make test | grep -q ok; echo $?",
        "$? after a `command` filter": "make test | command grep -q ok; echo $?",
        "backtick in a -m value": f'git commit -m "fix {tick}the thing{tick}"',
        "a verdict piped into tail": "python scripts/atlas.py check 2>&1 | tail -5",
        "a test run piped into grep": "pytest -q | grep passed",
        "a credential in the command": "printf '%s' '" + "KGAT" + "_" + "0123456789abcdef0123" + "' >> keys.env",
    }
    allowed = {
        "a plain message": 'git commit -m "plain message"',
        "a deliberate subshell": "( cd x && make ) | tee log",
        "single quotes keep a backtick": f"git commit -m 'literal {tick}x{tick}'",
        "no pipeline at all": "python scripts/verify.py",
        "a verdict under pipefail": "set -o pipefail; pytest -q | tail -20",
        "$? under pipefail": "set -o pipefail; make test | grep -q ok; echo $?",
        "a `command grep` reader": "command grep -rn check scripts | head",
        "a reader that greps for a verdict word": "grep -rn check scripts | head",
        "git output through a filter": "git log --oneline | head -5",
        "a credential passed by name": "set -a; . ~/.claude-keys.env; set +a",
        "$? after a later unpiped command": "du -sh * | sort -h && make lint; echo $?",
        # 3.50.0: each pipeline rule reads ONE top-level statement, heredoc bodies removed — every case
        # below was refused before, measured in seven days of one owner's agent shells.
        "a verdict word in an EARLIER statement": "python scripts/verify.py; ls | head -3",
        "$? after `||` with no pipe": "make lint || true\necho rc=$?",
        "a pipe inside a heredoc body": "cat > note.sh <<'EOF'\nmake test | tail -1\necho $?\nEOF\nzsh note.sh",
        "$? two statements after the filter": "ls | head -1; make lint; echo $?",
        "$? after a later unpiped python": "ls x | grep y ; python3 foo.py >/dev/null; printf 'rc=%s\\n' $?",
        "a verdict file NAME read by a reader": "wc -l guards.test.sh | tail -1",
    }
    refused.update(
        {
            "$? in the statement right after a filter": "cd x && make test | head -3; echo rc=$?",
            "a verdict after a cd": "cd repo && python scripts/atlas.py check 2>&1 | grep -c FAIL",
            "a heredoc does not hide the pipeline after it": "cat > n <<'EOF'\nx\nEOF\npytest -q | tail -2",
        }
    )
    for row in policy().get("shell_shapes") or []:  # each row carries its plant and near-miss (3.49.0)
        if not row.get("refuses") and not row["reason"].startswith("a credential"):  # literal key: built above
            raise SystemExit(f"FAIL a shell_shapes row plants nothing it refuses: {row['reason'][:60]}")
        for cmd in row.get("refuses") or []:  # on linux, where an `exempt_platforms` row still applies
            if shell_verdict(cmd, platform="linux").reason != row["reason"]:
                raise SystemExit(f"FAIL its own row did not refuse {cmd!r}: {shell_verdict(cmd).reason[:70]}")
        if row.get("exempt_platforms"):  # exempt where the shape cannot occur, refused again over ssh
            for platform in row["exempt_platforms"]:
                cmd = row["refuses"][0]
                if not shell_verdict(cmd, platform=platform).allowed:
                    raise SystemExit(f"FAIL an exempt row still refused on {platform}: {cmd!r}")
                if shell_verdict(f"ssh vps '{cmd}'", platform=platform).allowed:
                    raise SystemExit(f"FAIL an exempt row let the remote shape through on {platform}: {cmd!r}")
            continue
        refused.update({cmd: cmd for cmd in row.get("refuses") or []})
        allowed.update({cmd: cmd for cmd in row.get("allows") or []})
    for name, cmd in refused.items():
        if shell_verdict(cmd).allowed:
            raise SystemExit(f"FAIL shell_verdict allowed a silent shape: {name} -> {cmd}")
    for name, cmd in allowed.items():
        if not shell_verdict(cmd).allowed:
            raise SystemExit(f"FAIL shell_verdict fired on correct code: {name} -> {cmd}")
    module.CASES.append(
        (
            f"shell_verdict refuses {len(refused)} silent shell shapes and allows {len(allowed)} correct commands",
            "a command whose verdict or effect is not the one its writer reads — and a guard that "
            "fires on a deliberate subshell, which is how a guard gets switched off",
        )
    )
    print("  ok    shell_verdict refuses the silent shell shapes and allows correct commands")
