"""Planted cases for shell_verdict: the silent shell shapes are refused and correct commands are not.

Split out of atlas_guards_test.py at 3.50.0, which sat at the line cap when the per-statement cases were
added. Run inside atlas_test's counted main, like handoff_test and schedtargets_test.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType
from typing import Any, cast

ROOT = CASES = mutated = atlas = cast(Any, None)  # bound by run() from the running atlas_test module


def run(module: ModuleType) -> None:
    global ROOT, CASES, mutated, atlas
    ROOT, CASES, mutated, atlas = module.ROOT, module.CASES, module.mutated, module.atlas
    shell_verdict_cases(module)
    plugin_cases()
    edited_links_cases()
    termination_cases()


def _cleared_by_does_the_work(row: dict) -> None:
    """Mutation: every form a row's `cleared_by` clears is the raw shape, so the field, not the pattern, allows it."""
    cleared = [cmd for cmd in row.get("allows") or [] if re.search(str(row["cleared_by"]), cmd)]
    if not cleared:
        raise SystemExit(f"FAIL a cleared_by row plants no form it clears: {row['reason'][:60]}")
    for cmd in cleared:
        if not re.search(str(row["pattern"]), cmd):
            raise SystemExit(f"FAIL cleared_by is not what allows {cmd!r}: its pattern never matched")


def shell_verdict_cases(module: ModuleType) -> None:
    """The silent shell shapes are refused, and correct commands are NOT (3.27.0).

    Specificity first: a guard that fires on a deliberate subshell or an honest message gets switched off,
    and these five standing verdicts existed precisely because nothing in this tree could judge a shell.
    """
    from agentpolicy import CODED_SHELL_SHAPES, policy, shell_verdict

    tick = chr(96)  # built at run time: a literal backtick here would be substituted in this very file
    refused = {
        "sourced file in a pipeline": "source .venv/bin/activate | tee log",
        "$? after a filter": "make test | grep -q ok; echo $?",
        "$? after a `command` filter": "make test | command grep -q ok; echo $?",
        "backtick in a -m value": f'git commit -m "fix {tick}the thing{tick}"',
        "backtick in a --body value": f'gh pr create --title t --body "run {tick}make{tick} first"',
        "backtick in a --title= value": f'gh pr edit 1 --title="fix {tick}x{tick}"',
        "backtick after a quoted heredoc closes": f"cat <<'EOF' > n\nit's\nEOF\necho \"a {tick}b{tick}\"",
        "backtick in an unquoted heredoc": f"git commit -F - <<EOF\nfix {tick}the thing{tick}\nEOF",
        "a verdict piped into tail": "python scripts/atlas.py check 2>&1 | tail -5",
        "a test run piped into grep": "pytest -q | grep passed",
        "a credential in the command": "printf '%s' '" + "KGAT" + "_" + "0123456789abcdef0123" + "' >> keys.env",
    }
    allowed = {
        "a plain message": 'git commit -m "plain message"',
        "a deliberate subshell": "( cd x && make ) | tee log",
        "single quotes keep a backtick": f"git commit -m 'literal {tick}x{tick}'",
        "a quoted heredoc keeps a backtick": f"git commit -F - <<'EOF'\nfix {tick}x{tick} \"q\"\nEOF\ngit log -1",
        "an escaped backtick in double quotes": f'echo "a \\{tick}b\\{tick}"',
        "a deliberate bare substitution": f"echo {tick}date{tick}",
        "a heredoc inside a quoted substitution": f"git commit -m \"$(cat <<'EOF'\nfix {tick}x{tick}\nEOF\n)\"",
        "a single quote inside a quoted heredoc": f"cat <<'EOF' > n.md\nit's {tick}x{tick}\nEOF",
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
            "$? read from a non-verdict filter": "ls src | grep -c py; echo rc=$?",
            "a verdict after a cd": "cd repo && python scripts/atlas.py check 2>&1 | grep -c FAIL",
            "a heredoc does not hide the pipeline after it": "cat > n <<'EOF'\nx\nEOF\npytest -q | tail -2",
        }
    )
    for row in policy().get("shell_shapes") or []:  # each row carries its plant and near-miss (3.49.0)
        if not row.get("refuses") and not row["reason"].startswith("a credential"):  # literal key: built above
            raise SystemExit(f"FAIL a shell_shapes row plants nothing it refuses: {row['reason'][:60]}")
        home = "darwin" if "linux" in (row.get("exempt_platforms") or []) else "linux"  # a platform the row applies on
        for cmd in row.get("refuses") or []:
            if shell_verdict(cmd, platform=home).reason != row["reason"]:
                raise SystemExit(
                    f"FAIL its own row did not refuse {cmd!r}: {shell_verdict(cmd, platform=home).reason[:70]}"
                )
        if row.get("exempt_platforms"):  # exempt where the shape cannot occur, refused again over ssh
            for platform in row["exempt_platforms"]:
                cmd = row["refuses"][0]
                if not shell_verdict(cmd, platform=platform).allowed:
                    raise SystemExit(f"FAIL an exempt row still refused on {platform}: {cmd!r}")
                if shell_verdict(f"ssh vps '{cmd}'", platform=platform).allowed:
                    raise SystemExit(f"FAIL an exempt row let the remote shape through on {platform}: {cmd!r}")
            continue
        if row.get("cleared_by"):
            _cleared_by_does_the_work(row)
        refused.update({cmd: cmd for cmd in row.get("refuses") or []})
        allowed.update({cmd: cmd for cmd in row.get("allows") or []})
    rows, seen = {str(r["reason"]) for r in policy().get("shell_shapes") or []}, set()
    for name, cmd in refused.items():
        verdict = shell_verdict(cmd)
        if verdict.allowed:
            raise SystemExit(f"FAIL shell_verdict allowed a silent shape: {name} -> {cmd}")
        coded = [k for k, opens in CODED_SHELL_SHAPES.items() if verdict.reason.startswith(opens)]
        if verdict.reason not in rows and len(coded) != 1:
            raise SystemExit(f"FAIL a coded refusal CODED_SHELL_SHAPES does not name once: {verdict.reason[:60]}")
        seen.update(coded if verdict.reason not in rows else [])
    if seen != set(CODED_SHELL_SHAPES):
        raise SystemExit(
            f"FAIL CODED_SHELL_SHAPES names a shape no planted case refuses: {set(CODED_SHELL_SHAPES) - seen}"
        )
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

    def rows(event: str, matcher: str) -> list[dict]:
        return [h for m in manifest["hooks"].get(event, []) if matcher in m["matcher"].split("|") for h in m["hooks"]]

    def call(key: tuple[str, str, str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            rows(key[0], key[1])[0]["command"],
            shell=True,
            cwd="/tmp",
            env=env,
            timeout=600,
            check=False,  # noqa: S602 — the manifest's own string, run as Claude Code runs it
            input=key[2],
            capture_output=True,
            text=True,
        )

    def key(event: str, matcher: str, tool_input: object) -> tuple[str, str, str]:
        return event, matcher, tool_input if isinstance(tool_input, str) else json.dumps({"tool_input": tool_input})

    # MEASURED (3.56.0): 16 cold CLI starts per probe, 9 probes per suite, was 77 of 258 s run one by one.
    # Each hook is a read-only subprocess, so they run at once; a call not listed here still runs inline.
    port_py, files = str(ROOT / "scripts" / "port.py"), [str(ROOT / t) for t in ("atlas.yaml", "AGENTS.md")]
    planned = [
        ("PreToolUse", "Bash", {"command": "pytest | tail -3; echo $?"}),
        ("PreToolUse", "Bash", {"command": "ls -la"}),
        ("PreToolUse", "Bash", "not json"),
        ("PreToolUse", "Bash", {"command": "python scripts/safeedit.py quote 'a: b'"}),
        *[("PostToolUse", m, {"file_path": port_py}) for m in ("Edit", "Write")],
        *[("PreToolUse", m, {"file_path": f}) for m in ("Edit", "Write", "MultiEdit") for f in files],
        *[("PreToolUse", "Edit", {"file_path": f}) for f in (port_py, "/nonexistent/atlas.yaml")],
        *[("PostToolUse", "Edit", {"file_path": f}) for f in (str(ROOT / "LICENSE"), "/nonexistent/x")],
    ]
    keys = [k for k in dict.fromkeys(key(*c) for c in planned) if len(rows(k[0], k[1])) == 1]
    with ThreadPoolExecutor(int(os.environ.get("HEADRON_SLOT_WORKERS") or 2)) as pool:
        answered = dict(zip(keys, pool.map(call, keys), strict=True))

    def hook(event: str, matcher: str, tool_input: object) -> tuple[int, str]:
        if len(rows(event, matcher)) != 1:
            problems.append(f"{event} {matcher}: {len(rows(event, matcher))} hook(s) declared, not one")
            return 0, ""
        k = key(event, matcher, tool_input)
        done = answered.get(k) or call(k)
        if done.returncode:
            problems.append(f"{event} {matcher} exited {done.returncode}: {done.stderr.strip()[-200:]}")
        return done.returncode, done.stdout.strip()

    answer = hook("PreToolUse", "Bash", {"command": "pytest | tail -3; echo $?"})[1]
    decided = (json.loads(answer) if answer.startswith("{") else {}).get("hookSpecificOutput", {})
    if decided.get("permissionDecision") != "deny" or "headron shell" not in decided.get(
        "permissionDecisionReason", ""
    ):
        problems.append(f"a refused shell string was not denied: {answer!r}")
    for name, tool_input in (("an allowed command", {"command": "ls -la"}), ("an unreadable record", "not json")):
        if hook("PreToolUse", "Bash", tool_input)[1]:
            problems.append(f"{name} drew an answer; it must pass silently")
    for matcher in ("Edit", "Write"):
        answer = hook("PostToolUse", matcher, {"file_path": str(ROOT / "scripts" / "port.py")})[1]
        if "headron gate" not in answer:
            problems.append(f"PostToolUse {matcher} on a routed file returned no plug: {answer!r}")
    for matcher in ("Edit", "Write", "MultiEdit"):
        for target in ("atlas.yaml", "AGENTS.md"):
            answer = hook("PreToolUse", matcher, {"file_path": str(ROOT / target)})[1]
            decided = (json.loads(answer) if answer.startswith("{") else {}).get("hookSpecificOutput", {})
            if decided.get("permissionDecision") != "ask" or "headron edit" not in decided.get(
                "permissionDecisionReason", ""
            ):
                problems.append(f"a direct {matcher} of {target} was not put to the person as 'ask': {answer!r}")
    for name, tool_input in (
        ("a hand edit of a source file", {"file_path": str(ROOT / "scripts" / "port.py")}),
        ("an edit in another repository", {"file_path": "/nonexistent/atlas.yaml"}),
    ):
        if hook("PreToolUse", "Edit", tool_input)[1]:
            problems.append(f"{name} drew an answer from the edit guard; it must pass silently")
    if hook("PreToolUse", "Bash", {"command": "python scripts/safeedit.py quote 'a: b'"})[1]:
        problems.append("the safeedit route drew an answer; it is the declared way to change atlas.yaml")
    for name, path in (
        ("an unrouted file", str(ROOT / "LICENSE")),
        ("a file outside any repository", "/nonexistent/x"),
    ):
        if hook("PostToolUse", "Edit", {"file_path": path})[1]:
            problems.append(f"{name} drew a plug; it must pass silently")
    server = manifest["mcpServers"]["headron"]
    script = Path(server["args"][0].replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT)))
    if script != ROOT / "scripts" / "headron_mcp.py" or not script.is_file():
        problems.append(f"the plugin's MCP server is not this tree's headron_mcp.py: {script}")
    if not (ROOT / "skills" / "headron" / "SKILL.md").is_file():
        problems.append("the plugin's skill skills/headron/SKILL.md is missing")
    problems += _skill_problems()
    problems += _loader_collisions(atlas.atlas().get("directory_scopes") or {})
    return problems


def _skill_problems() -> list[str]:
    # A lane skill is a string the person runs by name: a flag the script stopped answering fails here.
    runs = [
        (skill, rel, flag)
        for skill in sorted((ROOT / "skills").glob("*/SKILL.md"))
        for rel, flag in re.findall(
            r'CLAUDE_PLUGIN_ROOT\}/(scripts/\w+\.py)" (--[\w-]+)', skill.read_text(encoding="utf-8")
        )
    ]
    problems = []
    if not runs:
        problems.append("no plugin skill runs a script: the lane-skill check saw nothing")
    for skill, rel, flag in runs:
        if flag not in _string_constants(ROOT / rel):
            problems.append(f"{skill.relative_to(ROOT)} runs {rel} {flag}, which that script does not answer")
    return problems


def _string_constants(script: Path) -> set[str]:
    """Every string the script's CODE holds: a flag named only in a comment or inside a longer string is not one."""
    from atlascore import parsed_python, walked

    try:
        tree = parsed_python(script.read_text(encoding="utf-8"), str(script))
    except (OSError, ValueError):
        return set()
    nodes = walked(tree) if tree else ()
    return {node.value for node in nodes if isinstance(node, ast.Constant) and isinstance(node.value, str)}


# Claude Code loads EVERY .md in these plugin directories as a component, so the HEADRON.md a scope generates
# there becomes a /headron:HEADRON command — the shape agentvocab.py met as a skill named HEADRON.
PLUGIN_LOADER_DIRS = ("commands", "agents", "output-styles")


def _loader_collisions(scopes: dict) -> list[str]:
    return [
        f"directory_scopes/{name} generates {name}/HEADRON.md, which Claude Code loads as a plugin component"
        for name in PLUGIN_LOADER_DIRS
        if name in scopes
    ]


def plugin_cases() -> None:
    """The opt-in Claude Code plugin: a refused shell denies, while edit hooks advise; each property is planted."""
    problems = _plugin_problems()
    if problems:
        raise SystemExit("FAIL the Claude Code plugin: " + "; ".join(problems))
    CASES.append(
        (
            "the Claude Code plugin's hooks run the CLI: a refused shell string denies, an edit returns its plug",
            "a plugin manifest whose hooks name a command the CLI no longer answers",
        )
    )
    mutants = (
        ("scripts/knowledgecli.py", 'permissionDecision="deny"', 'permissionDecision="ask"', "not denied", False),
        ("scripts/knowledgecli.py", 'if rec["route"] is not None:', "if True:", "unrouted", False),
        ("scripts/knowledgecli.py", "        os.chdir(source.resolve().parent)\n", "", "routed file", False),
        (".claude-plugin/plugin.json", "shell --hook", "shell", "PreToolUse Bash exited 3", False),
        ("scripts/port.py", 'if rel == "atlas.yaml":', "if False:", "atlas.yaml was not", False),
        (".claude-plugin/plugin.json", "port --guard", "port", "PreToolUse Edit exited", False),
        ("skills/land/SKILL.md", 'branchstate.py" --land', 'branchstate.py" --lnd', "does not answer", True),
        ("scripts/branchstate.py", '"--rekick" in argv', '"--rekik" in argv', "does not answer", True),
        # SIGHTED (review): the flag survived in a comment and a substring probe still called it answered.
        (
            "scripts/branchstate.py",
            '"--rekick" in argv:',
            '"--rekik" in argv:  # was "--rekick"',
            "does not answer",
            True,
        ),
    )
    if not _loader_collisions({"commands": {}}):
        raise SystemExit("FAIL a directory_scopes entry for commands/ was not refused")
    for path, old, new, needle, skill_only in mutants:
        with mutated(path, lambda s, old=old, new=new: s.replace(old, new, 1)):
            planted = _skill_problems() if skill_only else _plugin_problems()
        if not any(needle in p for p in planted):
            raise SystemExit(f"FAIL the plugin probe did not notice {old!r} -> {new!r} in {path}: {planted}")
    with mutated(
        "agreement.lock",
        # derived, not a literal hash: every atlas.yaml edit to that section re-stamps the lock
        lambda s: re.sub(r'"absent_input_owners": "[0-9a-f]+"', '"absent_input_owners": "0"', s, count=1),
    ):
        drifted = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "atlas.py"), "port", "--hook"],
            input=json.dumps({"tool_input": {"file_path": str(ROOT / "scripts" / "port.py")}}),
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(ROOT)},
        )  # noqa: S602
    if "agreement.lock drift: section/absent_input_owners" not in drifted.stdout:
        raise SystemExit(
            f"FAIL the edit hook did not surface a planted lock drift: {drifted.stdout!r} {drifted.stderr[-200:]}"
        )
    CASES.append(
        (
            "a plugin hook that denies, plugs an unrouted file, or drops --hook, or a lane skill naming a dead flag, is caught",
            "a probe that passes whatever the manifest says",
        )
    )
    print(f"  ok    claude plugin: hooks answer as declared; {len(mutants)} planted drifts caught")


def edited_links_cases() -> None:
    """Exercise the post-edit hook against untracked files in a separate consumer repository."""
    import tempfile  # noqa: PLC0415
    from contextlib import redirect_stdout  # noqa: PLC0415
    from io import StringIO  # noqa: PLC0415
    from unittest.mock import patch  # noqa: PLC0415

    import knowledgecli  # noqa: PLC0415
    import linkcheck  # noqa: PLC0415

    old_cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as directory:
        tree = Path(directory)
        subprocess.run(["git", "init", "-q", str(tree)], check=True, timeout=30, capture_output=True)
        source = tree / "draft.md"
        with patch.object(linkcheck, "tracked", return_value=[tree / "missing.md"]):
            if not linkcheck.link_errors(root=tree)[0]:
                raise SystemExit("FAIL missing tracked Markdown was silently skipped")
        target = tree / "target.md"
        target.write_text("# Present\n", encoding="utf-8")
        (tree / "with space.md").write_text("# Present\n", encoding="utf-8")
        payload = json.dumps({"tool_input": {"file_path": str(source)}})

        def output() -> str:
            result = StringIO()
            try:
                with redirect_stdout(result):
                    knowledgecli.port_hook(payload)
            finally:
                os.chdir(old_cwd)
            return result.getvalue()

        source.write_text("[missing](absent.md) [anchor](target.md#absent)\n", encoding="utf-8")

        def assert_defects() -> None:
            actual = output()
            if "broken local link" not in actual or "broken anchor" not in actual:
                raise AssertionError(f"edited Markdown defects were not reported: {actual!r}")

        assert_defects()
        with patch.object(atlas, "link_errors", return_value=([], {}, 0)):
            try:
                assert_defects()
            except AssertionError:
                pass
            else:
                raise SystemExit("FAIL disabling link validation did not kill the planted case")
        source.write_text(r"Escaped \` then [broken](missing.md) then \`", encoding="utf-8")
        if "broken local link" not in output():
            raise SystemExit("FAIL escaped backticks hid a broken link")
        for content in (
            r"`x\` [bad](absent.md) `",
            "` stray\n\n[bad](absent.md)\n\n` stray",
            "` stray\n# Heading [bad](absent.md)\n` stray\n",
            "` stray\nHeading [bad](absent.md)\n===\n` stray\n",
            "` stray\n- [bad](absent.md)\n` stray\n",
            "` stray\n> [bad](absent.md)\n` stray\n",
        ):
            source.write_text(content, encoding="utf-8")
            if "broken local link" not in output():
                raise SystemExit(f"FAIL code delimiters hid a broken link: {content!r}")
        source.write_text("- `literal\n  [example](missing.md)`\n", encoding="utf-8")
        if "broken local link" in output():
            raise SystemExit("FAIL multiline inline code in a list was interpreted as a link")
        source.write_text("- ```md\n  [example](missing.md)\n  ```\n[bad](absent.md)\n", encoding="utf-8")
        answer = output()
        if "absent.md" not in answer or "missing.md" in answer:
            raise SystemExit(f"FAIL list fence or following link was misread: {answer!r}")
        nested = tree / "nested"
        nested.mkdir()
        relative = nested / "draft.md"
        relative.write_text("[missing](absent.md)\n", encoding="utf-8")
        try:
            os.chdir(tree)
            result = StringIO()
            with redirect_stdout(result):
                knowledgecli.port_hook(json.dumps({"tool_input": {"file_path": "nested/draft.md"}}))
        finally:
            os.chdir(old_cwd)
        if "broken local link" not in result.getvalue():
            raise SystemExit(f"FAIL nested relative edit was not checked: {result.getvalue()!r}")
        source.write_text(
            "[ok](target.md#present) [mail](mailto:user@example.com) [encoded](with%20space.md#present) `[example](missing.md)` `multiline\n[example](missing.md)`\n```md\n[example](missing.md)\n```\n",
            encoding="utf-8",
        )
        actual = output()
        if "broken local link" in actual or "broken anchor" in actual:
            raise SystemExit(f"FAIL valid consumer link was reported broken: {actual!r}")
    CASES.append(
        ("edited Markdown reports broken local links and anchors in a consumer tree", "disabled link validation")
    )


def termination_cases() -> None:
    """Termination escapes the group while ordinary fixture exits remain reported."""
    import inspect  # noqa: PLC0415
    from types import SimpleNamespace  # noqa: PLC0415
    from unittest.mock import patch  # noqa: PLC0415

    import testgroups  # noqa: PLC0415

    def probe(run_group: Any) -> None:
        module = SimpleNamespace()

        def terminate(_module: Any) -> None:
            raise testgroups.SuiteTerminated(143)

        try:
            run_group(module, "termination", terminate)
        except testgroups.SuiteTerminated as exc:
            if exc.code != 143:
                raise AssertionError(f"wrong termination status: {exc.code}") from exc
        else:
            raise AssertionError("termination was swallowed")
        run_group(module, "fixture", lambda _: (_ for _ in ()).throw(SystemExit("fixture failure")))
        if not any("fixture failure" in row for row in module.SUITE_ERRORS):
            raise AssertionError("fixture failure was not recorded")

    with (
        patch.object(testgroups.impact, "enter"),
        patch.object(testgroups.impact, "leave"),
        patch.object(testgroups, "repo_settings", return_value=""),
    ):
        probe(testgroups.run_group)
        source = inspect.getsource(testgroups.run_group)
        mutant = source.replace("    except SuiteTerminated:\n        raise\n", "", 1)
        if mutant == source:
            raise SystemExit("FAIL termination mutation did not apply")
        namespace = dict(vars(testgroups))
        exec(mutant, namespace)  # noqa: S102
        try:
            probe(namespace["run_group"])
        except AssertionError:
            pass
        else:
            raise SystemExit("FAIL termination mutation survived")
    CASES.append(("termination escapes a group while fixture exits are recorded", "swallowed suite termination"))
