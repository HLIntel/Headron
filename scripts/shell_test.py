"""Planted cases for shell_verdict: the silent shell shapes are refused and correct commands are not.

Split out of atlas_guards_test.py at 3.50.0, which sat at the line cap when the per-statement cases were
added. Run inside atlas_test's counted main, like handoff_test and schedtargets_test.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = CASES = mutated = atlas = None  # bound by run() from the running atlas_test module


def run(module) -> None:
    global ROOT, CASES, mutated, atlas
    ROOT, CASES, mutated, atlas = module.ROOT, module.CASES, module.mutated, module.atlas
    shell_verdict_cases(module)
    plugin_cases()


def shell_verdict_cases(module) -> None:
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
        "a credential passed by name": "set -a; . ~/.secrets.env; set +a",
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


def _plugin_problems() -> list[str]:
    """Run every hook .claude-plugin/plugin.json declares, as Claude Code would, and list what it answers wrong.

    The manifest is read, not restated: a hook command that drifts from the CLI fails here, not in a session.
    """
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(ROOT)}
    problems = []

    def hook(event: str, matcher: str, tool_input: object) -> tuple[int, str]:
        rows = [h for m in manifest["hooks"].get(event, []) if matcher in m["matcher"].split("|") for h in m["hooks"]]
        if len(rows) != 1:
            problems.append(f"{event} {matcher}: {len(rows)} hook(s) declared, not one")
            return 0, ""
        done = subprocess.run(
            rows[0]["command"],
            shell=True,
            cwd="/tmp",
            env=env,
            timeout=600,
            check=False,  # noqa: S602 — the manifest's own string, run as Claude Code runs it
            input=tool_input if isinstance(tool_input, str) else json.dumps({"tool_input": tool_input}),
            capture_output=True,
            text=True,
        )
        if done.returncode:
            problems.append(f"{event} {matcher} exited {done.returncode}: {done.stderr.strip()[-200:]}")
        return done.returncode, done.stdout.strip()

    answer = hook("PreToolUse", "Bash", {"command": "pytest | tail -3; echo $?"})[1]
    decided = (json.loads(answer) if answer.startswith("{") else {}).get("hookSpecificOutput", {})
    if decided.get("permissionDecision") != "ask" or "thea shell" not in decided.get("permissionDecisionReason", ""):
        problems.append(f"a refused shell string was not put to the person as 'ask': {answer!r}")
    for name, tool_input in (("an allowed command", {"command": "ls -la"}), ("an unreadable record", "not json")):
        if hook("PreToolUse", "Bash", tool_input)[1]:
            problems.append(f"{name} drew an answer; it must pass silently")
    for matcher in ("Edit", "Write"):
        answer = hook("PostToolUse", matcher, {"file_path": str(ROOT / "scripts" / "port.py")})[1]
        if "thea gate" not in answer:
            problems.append(f"PostToolUse {matcher} on a routed file returned no plug: {answer!r}")
    for name, path in (
        ("an unrouted file", str(ROOT / "LICENSE")),
        ("a file outside any repository", "/nonexistent/x"),
    ):
        if hook("PostToolUse", "Edit", {"file_path": path})[1]:
            problems.append(f"{name} drew a plug; it must pass silently")
    server = manifest["mcpServers"]["thea"]
    script = Path(server["args"][0].replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT)))
    if script != ROOT / "scripts" / "thea_mcp.py" or not script.is_file():
        problems.append(f"the plugin's MCP server is not this tree's thea_mcp.py: {script}")
    if not (ROOT / "skills" / "thea" / "SKILL.md").is_file():
        problems.append("the plugin's skill skills/thea/SKILL.md is missing")
    # A lane skill is a string the person runs by name: a flag the script stopped answering fails here.
    runs = [
        (skill, rel, flag)
        for skill in sorted((ROOT / "skills").glob("*/SKILL.md"))
        for rel, flag in re.findall(
            r'CLAUDE_PLUGIN_ROOT\}/(scripts/\w+\.py)" (--[\w-]+)', skill.read_text(encoding="utf-8")
        )
    ]
    if not runs:
        problems.append("no plugin skill runs a script: the lane-skill check saw nothing")
    problems += _loader_collisions(atlas.atlas().get("directory_scopes") or {})
    for skill, rel, flag in runs:
        if not (ROOT / rel).is_file() or f'"{flag}"' not in (ROOT / rel).read_text(encoding="utf-8"):
            problems.append(f"{skill.relative_to(ROOT)} runs {rel} {flag}, which that script does not answer")
    return problems


# Claude Code loads EVERY .md in these plugin directories as a component, so the THEA.md a scope generates
# there becomes a /thea:THEA command — the shape agentvocab.py met as a skill named THEA.
PLUGIN_LOADER_DIRS = ("commands", "agents", "output-styles")


def _loader_collisions(scopes: dict) -> list[str]:
    return [
        f"directory_scopes/{name} generates {name}/THEA.md, which Claude Code loads as a plugin component"
        for name in PLUGIN_LOADER_DIRS
        if name in scopes
    ]


def plugin_cases() -> None:
    """The opt-in Claude Code plugin: its hooks advise, never deny; each property planted and refused (3.50.0)."""
    problems = _plugin_problems()
    if problems:
        raise SystemExit("FAIL the Claude Code plugin: " + "; ".join(problems))
    CASES.append(
        (
            "the Claude Code plugin's hooks run the CLI: a refused shell string asks, an edit returns its plug",
            "a plugin manifest whose hooks name a command the CLI no longer answers",
        )
    )
    mutants = (
        ("scripts/knowledge.py", 'permissionDecision="ask"', 'permissionDecision="deny"', "'ask'"),
        ("scripts/knowledge.py", 'if rec["route"] is not None:', "if True:", "unrouted"),
        ("scripts/knowledge.py", "        os.chdir(Path(path).expanduser().resolve().parent)\n", "", "routed file"),
        (".claude-plugin/plugin.json", "shell --hook", "shell", "'ask'"),
        ("skills/land/SKILL.md", 'branchstate.py" --land', 'branchstate.py" --lnd', "does not answer"),
        ("scripts/branchstate.py", '"--rekick" in argv', '"--rekik" in argv', "does not answer"),
    )
    if not _loader_collisions({"commands": {}}):
        raise SystemExit("FAIL a directory_scopes entry for commands/ was not refused")
    for path, old, new, needle in mutants:
        with mutated(path, lambda s, old=old, new=new: s.replace(old, new, 1)):
            planted = _plugin_problems()
        if not any(needle in p for p in planted):
            raise SystemExit(f"FAIL the plugin probe did not notice {old!r} -> {new!r} in {path}: {planted}")
    CASES.append(
        (
            "a plugin hook that denies, plugs an unrouted file, or drops --hook, or a lane skill naming a dead flag, is caught",
            "a probe that passes whatever the manifest says",
        )
    )
    print(f"  ok    claude plugin: hooks answer as declared; {len(mutants)} planted drifts caught")
