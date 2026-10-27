#!/usr/bin/env python3
"""`headron init` from a clean room: three fresh repositories (Python, TypeScript, Go), a fresh HOME, a clock.

It fails when the first run is over budget, prints a word of Headron's own the user was never told, leaves an
agent unwired, or changes a byte on a second run. `--public <out.json>` runs the same path against pinned
public repositories after a fresh `uv tool install` of this tree, and records the minutes each one took.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from consumer_test import _git

ROOT = Path(__file__).resolve().parent.parent
BUDGET = 300  # seconds from a clean clone to a first run: the promise is "under five minutes"
# HEADRON'S OWN WORDS: a newcomer was never told any of them. A line that needs one must define it first.
INTERNAL = (
    "atlas",
    "contract",
    "instrument",
    "done_set",
    "done set",
    "invariant",
    "lane",
    "scripts/atlas.py",
    "pack",
    "route",
    "tier",
    "ledger",
    "checkpoint",
    "⠟",
)
TOLD = {"NOT RUN": "NOT RUN: "}  # a term the output may use only together with its definition
FIXTURES = {
    "python": {
        "pyproject.toml": '[project]\nname = "demo"\nversion = "0"\n',
        "demo/core.py": "def add(a, b):\n    return a + b\n",
        "tests/test_core.py": "from demo.core import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n",
    },
    "typescript": {
        "package.json": '{"name": "demo", "version": "0.0.0"}\n',
        "src/index.ts": "export const add = (a: number, b: number): number => a + b;\n",
    },
    "go": {
        "go.mod": "module demo\n\ngo 1.21\n",
        "add.go": "package demo\n\nfunc Add(a, b int) int { return a + b }\n",
        "add_test.go": 'package demo\n\nimport "testing"\n\nfunc TestAdd(t *testing.T) {\n\tif Add(1, 2) != 3 {\n\t\tt.Fatal("add")\n\t}\n}\n',
    },
}
PUBLIC = (  # pinned: a moved default branch must not move the measurement
    ("python", "https://github.com/pallets/itsdangerous", "2.2.0"),
    ("typescript", "https://github.com/sindresorhus/ky", "v1.7.2"),
    ("go", "https://github.com/spf13/pflag", "v1.0.5"),
)
WIRED = ("AGENTS.md", "CLAUDE.md", ".mcp.json", ".codex/config.toml")


def jargon(out: str) -> list[str]:
    """Every word of Headron's own the output used without telling the user what it means."""
    bad = [t for t in INTERNAL if re.search(rf"(?<![\w-]){re.escape(t)}(?![\w-])", out, re.IGNORECASE)]
    return bad + [t for t, said in TOLD.items() if t in out and said not in out]


def init(repo: Path, env: dict, headron: list[str]) -> tuple[int, str, float]:
    start = time.monotonic()
    done = subprocess.run(
        [*headron, "init"], cwd=repo, env=env, capture_output=True, text=True, check=False, timeout=BUDGET * 2
    )
    return done.returncode, done.stdout + done.stderr, time.monotonic() - start


def judge(name: str, repo: Path, env: dict, headron: list[str]) -> dict:
    """One repository's first run, held to the budget, the vocabulary and the wiring; then a second run."""
    code, out, took = init(repo, env, headron)
    assert code == 0, f"{name}: headron init exited {code}:\n{out[-800:]}"
    assert took < BUDGET, f"{name}: first run took {took:.0f}s, over the {BUDGET}s budget"
    assert not jargon(out), f"{name}: printed {jargon(out)} without saying what it means:\n{out}"
    for step in (
        "1. This machine",
        "2. This repository",
        "3. What a change must pass",
        "4. Agents",
        "5. Git hooks",
        "6. First run",
    ):
        assert step in out, f"{name}: no {step!r} step:\n{out}"
    missing = [w for w in WIRED if not (repo / w).is_file()]
    assert not missing, f"{name}: agents left unwired: {missing}"
    assert json.loads((repo / ".mcp.json").read_text())["mcpServers"]["headron"]["command"] == "headron-mcp"
    before = {w: (repo / w).read_bytes() for w in WIRED}
    again, out2, _ = init(repo, env, headron)
    assert again == 0 and all((repo / w).read_bytes() == before[w] for w in WIRED), (
        f"{name}: a second run rewrote wiring"
    )
    assert out2.count("unchanged") >= len(WIRED), f"{name}: a second run did not say the wiring was unchanged:\n{out2}"
    return {"repository": name, "seconds": round(took, 1), "minutes": round(took / 60, 2)}


def _clean_env(home: Path) -> dict:
    keep = ("PATH", "LANG", "TMPDIR", "SYSTEMROOT")
    return {k: os.environ[k] for k in keep if k in os.environ} | {"HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1"}


def fixture_cases() -> None:
    top = Path(tempfile.mkdtemp(prefix="headron-onboard-"))
    try:
        env = _clean_env(top / "home") | {"HEADRON_ROOT": str(ROOT), "PYTHONPATH": str(ROOT / "scripts")}
        (top / "home").mkdir()
        headron = [sys.executable, str(ROOT / "scripts" / "atlas.py")]
        for name, files in FIXTURES.items():
            repo = top / name
            for rel, body in files.items():
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text(body, encoding="utf-8")
            (repo / "AGENTS.md").write_text("# Mine\n\nKeep this line.\n", encoding="utf-8")  # the user's own text
            _git(repo, "init", "-q")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", "base")
            judge(name, repo, env, headron)
            assert "Keep this line." in (repo / "AGENTS.md").read_text(), f"{name}: init dropped the user's AGENTS.md"
        bare = top / "not-a-repo"
        bare.mkdir()
        code, out, _ = init(bare, env, headron)
        assert code == 1 and "git repository" in out, f"outside git: rc={code} {out!r}"
        print("onboard: 3 clean-room repositories set up under budget, no unexplained term, wiring idempotent")
    finally:
        shutil.rmtree(top, ignore_errors=True)


def public(out_path: Path) -> int:
    """The measured path: a fresh `uv tool install` of this tree, then pinned public repositories."""
    top = Path(tempfile.mkdtemp(prefix="headron-onboard-public-"))
    env = _clean_env(top / "home") | {
        "UV_TOOL_DIR": str(top / "tools"),
        "UV_TOOL_BIN_DIR": str(top / "bin"),
        "UV_CACHE_DIR": str(top / "uv"),
        "HEADRON_ROOT": str(ROOT),
    }
    env["PATH"] = f"{top / 'bin'}{os.pathsep}{env['PATH']}"
    (top / "home").mkdir()
    start = time.monotonic()
    subprocess.run(["uv", "tool", "install", str(ROOT)], env=env, check=True, capture_output=True, timeout=600)
    install = round(time.monotonic() - start, 1)
    rows, failed = [], []
    for name, url, tag in PUBLIC:
        repo = top / name
        start = time.monotonic()
        subprocess.run(
            ["git", "clone", "-q", "--depth", "1", "--branch", tag, url, str(repo)],
            env=env,
            check=True,
            capture_output=True,
            timeout=600,
        )
        clone = round(time.monotonic() - start, 1)
        try:
            row = judge(name, repo, env, ["headron"])
        except AssertionError as error:
            failed.append(str(error)[:300])
            row = {"repository": name, "seconds": None, "minutes": None, "failed": str(error)[:300]}
        total = round(install + clone + (row["seconds"] or 0), 1)
        rows.append(
            row
            | {
                "url": url,
                "tag": tag,
                "install_seconds": install,
                "clone_seconds": clone,
                "total_minutes": round(total / 60, 2),
            }
        )
    record = {
        "schema": 1,
        "measured": "headron init, clean HOME, fresh uv tool install of this tree",
        "budget_seconds": BUDGET,
        "repositories": rows,
    }
    out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    for r in rows:
        print(f"{r['repository']:<11} {r['tag']:<8} total {r['total_minutes']} min (init {r['seconds']}s)")
    shutil.rmtree(top, ignore_errors=True)
    print("\n".join(failed))
    return 1 if failed else 0


def run(module) -> None:  # noqa: ARG001 — the case-module signature atlas_guards_test.py calls
    fixture_cases()


if __name__ == "__main__":
    if "--public" in sys.argv:
        sys.exit(public(Path(sys.argv[sys.argv.index("--public") + 1])))
    fixture_cases()
