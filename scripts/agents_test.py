"""Planted agent-registry cases (3.51.0), every one killing a named wrong implementation.

Run inside atlas_test's counted main, like handoff_test and schedtargets_test.
"""

from __future__ import annotations

import atexit
import contextlib
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def pin_suite_home() -> None:
    """THE SUITE NEVER WRITES THE OWNER'S LEDGER (3.54.0): planted refusals and a planted bad.py verify
    reached ~/.headron/field, where the README's field line would have counted them as use."""
    os.environ["HEADRON_HOME"] = tempfile.mkdtemp(prefix="headron-suite-home-")
    atexit.register(shutil.rmtree, os.environ["HEADRON_HOME"], True)


def run(module) -> None:
    """Each planted registry state is refused or counted as the design says, beside its clean twin."""
    import agents

    # Run first, under the suite's own home: a suite that leaks to the owner's ledger fails here.
    name = "the planted suite writes its field ledger under its own home, never the owner's"
    if Path.home() / ".headron" in agents.field_stream().parents:
        raise SystemExit(f"FAIL {name}\n  kills: the suite's planted refusals counted as field use")
    module.CASES.append((name, "the suite's planted refusals counted as field use"))
    print(f"  ok    {name}")
    saved = os.environ.get("HEADRON_HOME")
    with tempfile.TemporaryDirectory(prefix="headron-agents-") as home:
        os.environ["HEADRON_HOME"] = home
        try:
            rows = _rows(agents, home)
        finally:
            if saved is None:
                del os.environ["HEADRON_HOME"]
            else:
                os.environ["HEADRON_HOME"] = saved
    for name, kills, ok in rows:
        if not ok:
            raise SystemExit(f"FAIL {name}\n  kills: {kills}")
        module.CASES.append((name, kills))
        print(f"  ok    {name}")
    shown_cases(module)


def _shown_problems(module) -> list[str]:
    """`failures --shown` seals a field_lesson the field summary counts, and refuses an unknown id unsealed."""
    problems = []
    with tempfile.TemporaryDirectory() as home:
        env = {**os.environ, "HEADRON_HOME": home}

        def headron(*argv: str) -> tuple[int, str]:
            out = subprocess.run(
                [sys.executable, "scripts/atlas.py", *argv],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
                env=env,
            )
            return out.returncode, out.stdout

        known = next(iter(module.atlas.atlas().get("agent_failure_modes") or {}))
        rc, _ = headron("failures", "--shown", "not_a_recorded_shape", "--route", "python")
        if rc != 2:
            problems.append(f"an unknown id was not refused: rc={rc}")
        rc, said = headron("failures", "--shown", known, "--route", "python")
        if rc != 0 or "sealed" not in said:
            problems.append(f"a known id was not sealed: rc={rc} {said[:120]!r}")
        rc, said = headron("agents", "--field", "--json")
        try:
            shown = json.loads(said).get("lessons_shown")
        except ValueError:
            shown = None
        if shown != 1:
            problems.append(f"agents --field counted lessons_shown={shown}, want 1 (the refused call sealed nothing)")
    return problems


def shown_cases(module) -> None:
    """A lesson a hook shows an agent reaches the field ledger, so `lessons_shown` is measured (3.54.0)."""
    problems = _shown_problems(module)
    if problems:
        raise SystemExit("FAIL failures --shown:\n  " + "\n  ".join(problems))
    module.CASES.append(
        (
            "`failures --shown` seals a lesson the field summary counts, and refuses an unknown id",
            "lessons printed before every edit while the field ledger reads lessons_shown 0",
        )
    )
    print("  ok    failures --shown seals what it counts and refuses an unknown id")
    for old, new_ in (
        ('if unknown:\n        print(f"refused', 'if False:\n        print(f"refused'),
        ('field("field_lesson", {"route": route, "failures": keys})', "None"),
    ):
        with module.mutated("scripts/agents.py", lambda s, o=old, n=new_: s.replace(o, n, 1)):
            if not _shown_problems(module):
                raise SystemExit(f"FAIL the shown guard missed a planted defect: {old!r} -> {new_!r}")
    print("  ok    2 planted shown defects each caught")
    headline_cases(module)


def _headline_problems(module) -> list[str]:
    """The headline only rises: a lost stream is refused against the mark, a pinned break stays green, a new
    break is red, an unreadable mark is never reset, and `--record` never writes a lower snapshot.

    Loaded fresh from disk under its own name, so a planted defect reaches `_record` too, and the suite's
    own `agents` module is never left holding a mutated copy."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("agents_headline_probe", Path(__file__).with_name("agents.py"))
    if spec is None or spec.loader is None:
        return ["agents.py did not load as a module"]
    agents = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agents)

    problems = []
    saved = os.environ.get("HEADRON_HOME")
    with tempfile.TemporaryDirectory() as home:
        os.environ["HEADRON_HOME"] = home
        env = {**os.environ, "HEADRON_HOME": home}

        def report(*flags: str) -> tuple[int, dict]:
            out = subprocess.run(
                [sys.executable, "scripts/atlas.py", "agents", "--field", *flags],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
                env=env,
            )
            try:
                return out.returncode, json.loads(out.stdout)
            except ValueError:
                return out.returncode, {}

        try:
            for kind in ("field_refused", "field_refused", "field_landed"):
                agents.field(kind, {"shape": "x"})
            mark = agents.headline_mark()
            rc, said = report()
            high = json.loads(mark.read_text(encoding="utf-8"))["high"] if mark.exists() else {}
            if rc != 0 or said.get("headline", {}).get("refusals") != 2 or high.get("refusals") != 2:
                problems.append(f"the baseline was not set: rc={rc} high={high}")
            stream = agents.field_stream()
            aside = Path(home) / "aside.jsonl"
            stream.rename(aside)
            agents.field("field_landed", {"shape": "x"})  # a split home: one fresh event, the history gone
            rc, said = report()
            kept = json.loads(mark.read_text(encoding="utf-8"))["high"]
            if (
                rc != agents.HEADLINE_DROPPED
                or kept.get("refusals") != 2
                or "refusals" not in said.get("headline_dropped", {})
            ):
                problems.append(f"a lost stream was shown as the new number: rc={rc} mark={kept}")
            stream.unlink()
            aside.rename(stream)
            with stream.open("a", encoding="utf-8") as handle:
                handle.write("not an event\n")
            if report()[0] != 1:
                problems.append("a new broken chain read green")
            pinned = subprocess.run(
                [sys.executable, "scripts/atlas.py", "agents", "--field", "--accept-breaks"],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
                env=env,
            )
            rc, said = report()
            if pinned.returncode != 0 or rc != 0 or said.get("accepted_broken_chains") != 1:
                problems.append(f"a pinned break still read red: accept={pinned.returncode} rc={rc}")
            archived = stream.parent / "archive" / f"{stream.name}.gz"
            archived.parent.mkdir(exist_ok=True)
            archived.write_bytes(gzip.compress(stream.read_bytes()))
            stream.unlink()
            rc, said = report()
            if rc != 0 or said.get("accepted_broken_chains") != 1:
                problems.append(f"a pinned break turned red once its month was archived: rc={rc}")
            stream.write_bytes(gzip.decompress(archived.read_bytes()))
            archived.unlink()
            other = stream.with_name("2099-01.jsonl")
            other.write_text("not an event\n", encoding="utf-8")
            rc, said = report()
            if rc != 1 or said.get("new_broken_chains") != 1:
                problems.append(f"a break beside a pinned one read green: rc={rc}")
            other.unlink()
            mark.write_text("{torn", encoding="utf-8")
            if report()[0] != 2 or mark.read_text(encoding="utf-8") != "{torn":
                problems.append("an unreadable mark was reset, which lets any drop pass")
            snapshot = Path(home) / "field-latest.json"
            snapshot.write_text(json.dumps({"refusals": 5}), encoding="utf-8")
            summary = dict.fromkeys(agents.HEADLINE.values(), 1)
            with contextlib.redirect_stderr(io.StringIO()):
                fell = agents._record_snapshot(summary, snapshot)
            if fell != agents.HEADLINE_DROPPED or "5" not in snapshot.read_text():
                problems.append("--record wrote a snapshot lower than the committed one")
            if agents._record_snapshot(summary | {"refusals": 6}, snapshot) != 0:
                problems.append("--record refused a snapshot that rose")
        finally:
            if saved is None:
                del os.environ["HEADRON_HOME"]
            else:
                os.environ["HEADRON_HOME"] = saved
    return problems


def headline_cases(module) -> None:
    """THE HEADLINE ONLY RISES (3.62.0): verifications, refusals, landings, lessons and sessions."""
    problems = _headline_problems(module)
    if problems:
        raise SystemExit("FAIL the headline ratchet:\n  " + "\n  ".join(problems))
    module.CASES.append(
        (
            "a lost stream is refused against the headline mark; only a break not pinned is red",
            "a split home or lost month shown as the new, lower headline number",
        )
    )
    print("  ok    the headline refuses a drop, pins a legacy break, and reds a new one")
    for old, new_ in (
        ('if now < int(mark["high"].get(name) or 0)', "if False"),
        ("if _break_id(b) not in pinned", "if True"),
        ('.removesuffix(".gz")', ""),
        ("if isinstance(prior.get(key), int) and summary[key] < prior[key]", "if False"),
        (
            "        return 2\n    summary = field_summary(streams) |",
            '        mark = {"high": {}, "accepted_breaks": []}\n    summary = field_summary(streams) |',
        ),
    ):
        with module.mutated("scripts/agents.py", lambda s, o=old, n=new_: s.replace(o, n, 1)):
            if not _headline_problems(module):
                raise SystemExit(f"FAIL the headline guard missed a planted defect: {old!r} -> {new_!r}")
    print("  ok    5 planted headline defects each caught")


def _clear(home: str) -> None:
    for path in (Path(home) / "sessions").glob("*"):
        path.unlink()


def _count(agents, now: float) -> list[tuple[str, str]]:
    return [(r["agent"], r["source"]) for r in agents.live(agents.records(now)[0], now)]


def _nested_reads(agents, planted: Path) -> tuple[list[str], list[str]]:
    """network_modules over a tree holding a nested worktree (a `.git` FILE) — first outside git, then as a repo."""
    tree = planted / "nested-tree"
    (tree / ".claude" / "worktrees" / "lane").mkdir(parents=True)
    (tree / ".claude" / "worktrees" / "lane" / ".git").write_text("gitdir: /elsewhere\n", encoding="utf-8")
    (tree / ".claude" / "worktrees" / "lane" / "copy.py").write_text("import socket\n", encoding="utf-8")
    (tree / "leak.py").write_text("import urllib.request\n", encoding="utf-8")
    saved = os.environ.get("GIT_DIR")
    stray = planted / "stray"
    subprocess.run(["git", "init", "-q", str(stray)], capture_output=True, check=True, timeout=60)
    (stray / ".git" / "info" / "exclude").write_text("leak.py\n", encoding="utf-8")
    os.environ["GIT_DIR"] = str(stray / ".git")  # a stray repository must not answer for this tree
    try:
        outside = agents.network_modules(tree)
    finally:
        if saved is None:
            del os.environ["GIT_DIR"]
        else:
            os.environ["GIT_DIR"] = saved
    subprocess.run(["git", "init", "-q", str(tree)], capture_output=True, check=True, timeout=60)
    return outside, agents.network_modules(tree)


def _lifecycle(agents, home: str, now: float) -> dict:
    """End, resume, the field ledger and the unnamed MCP client, each read back from disk."""
    import agentaudit
    import headron_mcp
    import knowledge

    _clear(home)
    agents.beat("codex", "e1", "hook", "/w/e", now=now)
    agents.end("codex", "e1", "hook", "/w/e", now=now)
    rows = agents.records(now)[0]
    out = {"ended": agents.status(rows[0], now), "live_after_end": _count(agents, now)}
    agents.beat("codex", "e1", "hook", "/w/e", now=now + 1)
    out["resumed"] = agents.status(agents.records(now + 1)[0][0], now + 1)
    stream = agents.field_stream()
    out["kinds"] = [e["event"] for e in agentaudit.read_events(stream)]
    out["chain"] = agentaudit.verify(stream)
    secret = "git reset --hard # planted-token-0xfeed"
    with contextlib.redirect_stdout(io.StringIO()):
        knowledge.shell_check(secret, as_json=True)
    tail = agentaudit.read_events(stream)[-1]
    out["refused"] = tail["event"] == "field_refused" and tail["body"]["command"] == agentaudit.digest(secret)
    out["leaked"] = "planted-token" in stream.read_text(encoding="utf-8")
    import atlas

    with contextlib.redirect_stdout(io.StringIO()):
        out["gate_code"] = atlas.gate("planted.nosuchext", "formatter", as_json=True)
    row = agentaudit.read_events(stream)[-1]
    out["gate_row"] = row["event"] == "field_gate_refused" and row["body"]["gate"] == "formatter"
    out["joins"] = _joins(agents, stream)
    _clear(home)
    saved = headron_mcp.CLIENT["name"]
    headron_mcp.CLIENT["name"] = None
    try:
        headron_mcp._beat()
        headron_mcp._beat(ended=True)
    finally:
        headron_mcp.CLIENT["name"] = saved
    out["unnamed"] = list((Path(home) / "sessions").glob("*.json"))
    return out


def _joins(agents, stream: Path) -> dict:
    """Two sessions: one re-fires a shape and recovers a failed verify, one does neither."""
    stream.unlink()
    saved = os.environ.get("CLAUDE_CODE_SESSION_ID")
    try:
        for session, kinds in (
            (
                "a",
                [
                    ("field_refused", {"shape": "x"}),
                    ("field_refused", {"shape": "x"}),
                    ("field_verify", {"exit": 1}),
                    ("field_verify", {"exit": 0}),
                ],
            ),
            ("b", [("field_refused", {"shape": "x"}), ("field_verify", {"exit": 1})]),
            ("c", [("field_verify", {"exit": 0}), ("field_verify", {"exit": 1})]),
            ("d", [("field_verify", {"exit": 2})]),
        ):
            os.environ["CLAUDE_CODE_SESSION_ID"] = session
            for kind, body in kinds:
                agents.field(kind, body)
    finally:
        if saved is None:
            os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        else:
            os.environ["CLAUDE_CODE_SESSION_ID"] = saved
    s = agents.field_summary([stream])
    return {
        k: s[k]
        for k in (
            "refusals",
            "refires",
            "sessions_failed",
            "sessions_recovered",
            "broken_chains",
            "verify_other_nonzero",
        )
    }


def _rows(agents, home: str) -> list[tuple[str, str, bool]]:
    now = 1_000_000.0
    agents.beat("claude-code", "s1", "hook", "/w/a", now=now)
    agents.beat("claude-code", "mcp-1", "mcp", "/w/a", now=now)
    agents.beat("cursor", "mcp-2", "mcp", "/w/b", now=now)
    merged = _count(agents, now)
    agents.beat("old", "s0", "hook", "/w/c", now=now - agents.LIVE_SECONDS - 1)
    stale = _count(agents, now)
    _clear(home)
    try:
        agents.from_hook("claude-code", io.StringIO('{"cwd": "/w/a"}'))
        invented = True
    except agents.BeatError:
        invented = False
    written = list((Path(home) / "sessions").glob("*.json")) if (Path(home) / "sessions").exists() else []
    agents.beat("claude-code", "s1", "hook", "/w/a", now=now)
    (Path(home) / "sessions" / "torn.json").write_text("{", encoding="utf-8")
    bad = agents.records(now)[1]
    listed = subprocess.run([sys.executable, agents.__file__], capture_output=True, text=True, check=False, timeout=60)
    blocked = subprocess.run(
        [sys.executable, agents.__file__, "--hook", "x"],
        input="not json",
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    lifecycle = _lifecycle(agents, home, now)
    root = Path(agents.__file__).resolve().parent.parent
    declared = sorted(f"scripts/{m}" for m in agents.NETWORK_MODULES)
    tree_net = agents.network_modules(root)
    with tempfile.TemporaryDirectory(prefix="headron-net-") as planted:
        (Path(planted) / "quiet.py").write_text("import json\n", encoding="utf-8")
        (Path(planted) / "leak.py").write_text("from http.client import HTTPSConnection\n", encoding="utf-8")
        caught = agents.network_modules(Path(planted))
        nested = _nested_reads(agents, Path(planted))
    return [
        (
            "only the declared modules can open a network connection",
            "a new import that sends data off the machine unannounced",
            tree_net == declared,
        ),
        (
            "a planted network import is caught, its quiet twin is not",
            "a privacy scan that matches only the module names it was shown",
            caught == ["leak.py"],
        ),
        (
            "a worktree nested inside the tree is not read as its source, in git or out of it",
            "root.rglob reading .claude/worktrees copies as this tree's modules",
            nested == (["leak.py"], ["leak.py"]),
        ),
        (
            "a hooked agent that also runs the MCP server counts once",
            "a count of records, not agents",
            merged.count(("claude-code", "hook")) == 1 and ("claude-code", "mcp") not in merged,
        ),
        (
            "an agent with only the MCP server is still counted",
            "a count that only sees hooked agents",
            ("cursor", "mcp") in merged,
        ),
        (
            "a session unseen past the live window is not running",
            "a count of every session ever recorded",
            ("old", "hook") not in stale and len(stale) == len(merged),
        ),
        (
            "a hook payload with no session id is refused, nothing written",
            "an invented session id",
            not invented and not written,
        ),
        (
            "a torn record is reported and fails the listing",
            "a silent skip that shrinks the count",
            bad == ["torn.json"] and listed.returncode == 1 and "UNREADABLE" in listed.stdout,
        ),
        (
            "an ended session leaves the live count at once; a later beat resumes it",
            "a closed agent counted live until its last beat ages out",
            lifecycle["ended"] == "ended" and lifecycle["live_after_end"] == [] and lifecycle["resumed"] == "live",
        ),
        (
            "an end is sealed onto the field ledger under HEADRON_HOME, and the chain verifies",
            "a second ledger, or field events written to the real home by a test",
            lifecycle["kinds"] == ["session_ended"] and lifecycle["chain"] == [],
        ),
        (
            "a refused command or gate reaches the field ledger at once, by shape and digest, never its text",
            "a ledger that copies a command (and any secret in it) verbatim",
            lifecycle["refused"]
            and lifecycle["leaked"] is False
            and lifecycle["gate_code"] == 2
            and lifecycle["gate_row"],
        ),
        (
            "a shape re-fired in its own session is a re-fire; the same shape in another session is not",
            "a re-fire count keyed on the shape alone, across every session",
            lifecycle["joins"]["refusals"] == 3 and lifecycle["joins"]["refires"] == 1,
        ),
        (
            "a session whose verify failed then passed recovered; one that failed last did not",
            "a recovery rate from pass and fail totals, joined to nothing",
            lifecycle["joins"]["sessions_failed"] == 4
            and lifecycle["joins"]["sessions_recovered"] == 1
            and lifecycle["joins"]["broken_chains"] == 0,
        ),
        (
            "a nonzero verification exit outside code 1 is reported as non-successful",
            "an incomplete verification disappearing from the failure and session totals",
            lifecycle["joins"]["verify_other_nonzero"] == 1,
        ),
        (
            "an MCP client that never named itself writes no session record",
            "self-check and test spawns counted as agents",
            lifecycle["unnamed"] == [],
        ),
        (
            "a malformed hook input exits 1, never 2",
            "a missed heartbeat that blocks the agent's tool call",
            blocked.returncode == 1 and "no beat recorded" in blocked.stderr,
        ),
    ]
