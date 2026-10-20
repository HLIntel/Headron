#!/usr/bin/env python3
"""`thea init`: the first five minutes in a repository, in one command.

WHY (3.57.0). Timed in clean clones of three public repositories (Python, TypeScript, Go), every step of the
documented path took seconds, and none of them answered a newcomer: `thea doctor` checked this project's own
instruments and ended on `python scripts/atlas.py check`, a file the newcomer does not have; `thea port .`
printed glyphs; nothing wired an agent. This walks the path once, in the user's words:
  1 THIS MACHINE   git, and every tool a check here calls: found, or what it costs to lack it
  2 THIS REPO      tracked files per language
  3 CHECKS         the checks a change to each language must pass, with the command
  4 AGENTS         AGENTS.md (Codex, and anything that reads it), CLAUDE.md, .mcp.json, .codex/config.toml
  5 FIRST RUN      those checks run once on today's code, so a failure an agent meets later is not blamed on it
Wiring is idempotent and marker-delimited: a second run changes no byte, and text outside the markers is kept.
Exit 0 when the repository is set up (a failing check on today's code is information, not a setup failure);
1 when it is not a git repository.

  thea init [--no-wiring] [--no-run] [--json]
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path

from atlascore import atlas, ls_files

BEGIN, END = "<!-- BEGIN thea (written by `thea init`; edit outside these markers) -->", "<!-- END thea -->"
AGENTS_BLOCK = """## Checking a change with Thea

- Before editing a file: `thea gate <file>` prints the checks a change to it must pass.
- After a change: `thea verify` runs those checks; exit 0 only when every one passed.
- Then `thea report` lists the files, each check's result and what is still unverified.
- NOT RUN means a check could not run here. It is never a pass: say so, do not claim done."""
CLAUDE_BLOCK = "@AGENTS.md"
CODEX_TABLE = "[mcp_servers.thea]"
CODEX_BLOCK = f'# written by `thea init`\n{CODEX_TABLE}\ncommand = "thea-mcp"\n'
SKIP_DIRS = ("node_modules/", "vendor/", "dist/", "build/", "third_party/")


def _git(tree: Path, *args: str) -> tuple[int, str]:
    done = subprocess.run(["git", *args], cwd=tree, capture_output=True, text=True, check=False, timeout=600)
    return done.returncode, done.stdout


def scan(tree: Path) -> dict[str, list[str]]:
    """Tracked files by language, generated and vendored directories left out."""
    from atlascore import route_for  # noqa: PLC0415

    by: dict[str, list[str]] = {}
    for rel in ls_files(tree):
        if any(rel.startswith(d) or f"/{d}" in rel for d in SKIP_DIRS):
            continue
        language = route_for(rel)
        if language and (tree / rel).is_file():
            by.setdefault(language, []).append(rel)
    return by


def _sample(files: list[str]) -> str:
    """The file whose checks stand for its language: the most common suffix, outside tests, shortest path."""
    suffix = Counter(Path(f).suffix for f in files).most_common(1)[0][0]
    pool = [f for f in files if Path(f).suffix == suffix]
    plain = [f for f in pool if "test" not in f.lower()] or pool
    return min(plain, key=lambda f: (f.count("/"), len(f), f))


def checks(tree: Path, by: dict[str, list[str]]) -> list[dict]:
    """Each language's checks, from the one producer `thea verify` uses."""
    from branchstate import _consumer_change_class  # noqa: PLC0415
    from consumergates import consumer_records  # noqa: PLC0415

    samples = {_sample(files): language for language, files in by.items()}
    out = []
    for rec in consumer_records(tree, sorted(samples), _consumer_change_class()):
        argv = rec.get("argv") or []
        tool = argv[0] if argv else ""
        found = bool(tool) and bool(shutil.which(tool))  # the same test `thea verify` applies
        out.append(
            {
                "language": samples[rec["path"]],
                "file": rec["path"],
                "check": str(rec.get("gate")),
                "argv": argv,
                "state": "ready" if rec.get("state") == "runnable" and found else _state(rec, tool, found),
                "why": str(rec.get("why") or "")[:160],
            }
        )
    return out


def _state(rec: dict, tool: str, found: bool) -> str:
    if rec.get("state") == "absent":
        return "no tool"  # the language has no established tool for this check: an answer, not a gap
    return f"{tool} not installed" if tool and not found else "cannot run"


def _block(text: str, block: str) -> str:
    """`text` with the Thea block in place: replaced between the markers, appended when there are none."""
    framed = f"{BEGIN}\n{block}\n{END}"
    if BEGIN in text and END in text:
        head, rest = text.split(BEGIN, 1)
        return head + framed + rest.split(END, 1)[1]
    return (text.rstrip("\n") + "\n\n" if text.strip() else "") + framed + "\n"


def _mcp(text: str) -> str:
    data = json.loads(text) if text.strip() else {}
    servers = data.setdefault("mcpServers", {})
    if "thea" in servers:
        return text  # the user's own entry wins, whatever it says
    servers["thea"] = {"command": "thea-mcp", "args": []}
    return json.dumps(data, indent=2) + "\n"


def _codex(text: str) -> str:
    return text if CODEX_TABLE in text else (text.rstrip("\n") + "\n\n" if text.strip() else "") + CODEX_BLOCK


WIRING = {
    "AGENTS.md": lambda t: _block(t, AGENTS_BLOCK),
    "CLAUDE.md": lambda t: _block(t, CLAUDE_BLOCK),
    ".mcp.json": _mcp,
    ".codex/config.toml": _codex,
}


def wire(tree: Path, write: bool) -> list[dict]:
    """Each wiring file and what happened to it: written, updated, unchanged, or skipped (unreadable)."""
    out = []
    for rel, edit in WIRING.items():
        path = tree / rel
        old = path.read_text(encoding="utf-8") if path.is_file() else ""
        try:
            new = edit(old)
        except (json.JSONDecodeError, AttributeError) as error:
            out.append({"file": rel, "result": "skipped", "why": f"cannot read it as JSON: {error}"[:120]})
            continue
        result = "unchanged" if new == old else "updated" if path.is_file() else "written"
        if write and new != old:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new, encoding="utf-8")
        out.append({"file": rel, "result": result if write else f"would be {result}"})
    return out


def first_run(tree: Path, found: list[dict]) -> list[dict]:
    """Run each ready check once on the code as it is; one command shared by many files runs once."""
    from verify import run_gate  # noqa: PLC0415

    rows, ran = [], []
    for c in found:
        if c["state"] != "ready" or c["argv"] in ran:
            continue
        ran.append(c["argv"])
        row = run_gate({"id": f"{c['check']}:{c['file']}", "argv": c["argv"]}, cwd=tree)  # bounded by verify's TIMEOUT
        rows.append(c | {"verdict": row["verdict"], "seconds": row.get("seconds"), "why": str(row.get("why") or "")})
    return rows


def build(tree: Path, wiring: bool, run: bool) -> dict:
    start = time.monotonic()
    by = scan(tree)
    found = checks(tree, by) if by else []
    machine = [{"tool": "git", "found": bool(shutil.which("git"))}] + [
        {"tool": t, "found": not any(c["state"] == f"{t} not installed" for c in found)}
        for t in sorted({c["argv"][0] for c in found if c["argv"]})
    ]
    return {
        "schema": 1,
        "command": "init",
        "atlas_version": str(atlas().get("version")),
        "repository": tree.name,
        "machine": machine,
        "languages": {language: len(files) for language, files in sorted(by.items(), key=lambda kv: -len(kv[1]))},
        "checks": found,
        "wiring": wire(tree, wiring),
        "first_run": first_run(tree, found) if run else [],
        "seconds": round(time.monotonic() - start, 1),
        "exit": 0,
    }


def text(rec: dict) -> str:
    out = [f"thea init: {rec['repository']}", "", "1. This machine"]
    out += [f"   {'found  ' if m['found'] else 'MISSING'} {m['tool']}" for m in rec["machine"]]
    if not all(m["found"] for m in rec["machine"]):
        out.append("   A check whose tool is missing reports NOT RUN until you install it.")
    out += ["", "2. This repository"]
    out += [f"   {n:>5} {language} file(s)" for language, n in rec["languages"].items()] or ["   no file Thea knows"]
    out += ["", "3. What a change must pass (`thea gate <file>` shows them for any file)"]
    for c in rec["checks"]:
        how = shlex.join(c["argv"]) if c["argv"] else f"no established tool does this for {c['language']}"
        out.append(f"   {c['language']:<12} {c['check']:<24} {c['state']:<16} {how}")
    out += ["", "4. Agents (Claude Code: CLAUDE.md, .mcp.json; Codex: AGENTS.md, .codex/config.toml)"]
    out += [f"   {w['result']:<10} {w['file']}{'  ' + w['why'] if w.get('why') else ''}" for w in rec["wiring"]]
    if rec["first_run"]:
        out += ["", "5. First run, on the code as it is now (before any change of yours)"]
        out += [f"   {r['verdict']:<8} {r['language']:<12} {r['check']:<24} {r['why'][:70]}" for r in rec["first_run"]]
        if any(r["verdict"] != "PASS" for r in rec["first_run"]):
            out.append("   These already fail or cannot run today: a change of yours did not cause them.")
    if "NOT RUN" in "\n".join(out):
        out += ["", "NOT RUN: the check could not run here, so it proves nothing; it is never counted as a pass."]
    out += ["", f"Set up in {rec['seconds']}s. Next: change a file, then `thea verify` and `thea report`."]
    return "\n".join(out)


def main(args) -> int:
    from verify import is_atlas_checkout  # noqa: PLC0415

    code, top = _git(Path.cwd(), "rev-parse", "--show-toplevel")
    if code != 0:
        print("thea init: run it inside a git repository (`git init` first, then commit once)")
        return 1
    tree = Path(top.strip()).resolve()
    if is_atlas_checkout(tree):  # Thea's own repository is set up by its contract, never wired by this
        note = "this is Thea's own repository; it is already set up (`thea verify` checks it)"
        empty = {"machine": [], "languages": {}, "checks": [], "wiring": [], "first_run": [], "seconds": 0.0}
        rec = {"schema": 1, "command": "init", "atlas_version": str(atlas().get("version")), "repository": tree.name}
        print(json.dumps(rec | empty | {"note": note, "exit": 0}, indent=2) if args.json else f"thea init: {note}")
        return 0
    rec = build(tree, not getattr(args, "no_wiring", False), not getattr(args, "no_run", False))
    print(json.dumps(rec, indent=2) if args.json else text(rec))
    return rec["exit"]
