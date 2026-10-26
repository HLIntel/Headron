"""Regression cases for bounded execution, explicit verification scope and read-only MCP."""

import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import boundedinput
import gaterunner
import thea_mcp
import verify
from testgroups import run_group


def run(module):
    def passed(name):
        module.CASES.append((name, "an incomplete or unbounded operation reported as safe"))
        print("  ok    " + name)

    noisy = gaterunner.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('x'*200000+'tail'); sys.stderr.write('y'*200000); sys.exit(7)",
        ],
        timeout=5,
        keep=1024,
    )
    assert noisy.returncode == 7 and noisy.stdout.endswith("tail")
    assert len(noisy.stdout) == len(noisy.stderr) == 1024 and noisy.output_bytes == 400004
    passed("gate output is bounded without losing the exit code or byte count")
    with tempfile.TemporaryDirectory() as folder:
        tree = Path(folder)
        (tree / "checked.py").write_text("value = 1\n", encoding="utf-8")
        checked = gaterunner.run(
            [sys.executable, "-c", "import checked"], cwd=tree, env={"PYTHONDONTWRITEBYTECODE": "0"}, timeout=5
        )
        assert checked.returncode == 0 and not (tree / "__pycache__").exists()
    passed("a gate runner never emits Python bytecode beside checked source")
    try:
        gaterunner.run([sys.executable, "-c", "while True: pass"], timeout=0.1)
    except subprocess.TimeoutExpired:
        pass
    else:
        raise AssertionError("gate deadline did not refuse a running process")
    passed("a timed-out gate has no passing verdict")
    assert boundedinput.read_stdin(io.BytesIO(b"abc"), 3) == "abc"
    for raw in (b"abcd", b"\xff"):
        try:
            boundedinput.read_stdin(io.BytesIO(raw), 3)
        except SystemExit:
            continue
        raise AssertionError("oversized or malformed stdin accepted")
    passed("hook input refuses excess bytes and malformed UTF-8")
    for verb in ("verify", "slot"):
        assert thea_mcp.call("thea", {"argv": [verb]})["isError"]
        assert thea_mcp.call(verb, {})["isError"]
    passed("both MCP call forms refuse process-executing verbs")
    with tempfile.TemporaryDirectory() as folder:
        tree = Path(folder)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        subprocess.run(["git", "init", "-q", str(tree)], check=True, timeout=10, env=env)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--allow-empty",
                "-qm",
                "base",
            ],
            cwd=tree,
            check=True,
            timeout=10,
            env=env,
        )
        (tree / "a.py").write_text("x = 1\n")
        files, reason = verify.consumer_files(tree, "HEAD")
        assert files == ["a.py"] and not reason
        assert "--base" in verify.consumer_files(tree)[1]
        assert verify.consumer_files(tree, "missing-ref")[1]
    passed("a local repository can select an explicit comparison base")
    fake = SimpleNamespace(CASES=[])

    def broken(_):
        raise subprocess.CalledProcessError(128, ["git", "init"], stderr=b"fixture denied")

    run_group(fake, "fixture", broken)
    run_group(fake, "next", lambda m: m.CASES.append(("later case", "hidden failures")))
    assert len(fake.SUITE_ERRORS) == 1 and len(fake.CASES) == 1
    passed("fixture failures remain failures while later groups still run")
