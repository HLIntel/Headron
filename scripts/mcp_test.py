#!/usr/bin/env python3
"""The MCP route's process cases, split out of cli_test.py to keep it under the code-blob cap.

A case module: run() takes the RUNNING atlas_test module and registers into its counted CASES.

  mcp_fork_cases      a forked call reads an edited atlas and refuses a stale module; a slow call is killed
  bounded_output_case a call printing past MAX_OUTPUT is cut, drained and labelled, never held whole
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

ROOT = CASES = mutated = atlas = cast(Any, None)  # bound by run() from the running atlas_test module


def run(module) -> None:
    global ROOT, CASES, mutated, atlas
    ROOT, CASES, mutated, atlas = module.ROOT, module.CASES, module.mutated, module.atlas
    mcp_fork_cases()
    bounded_output_case()


_FORK_PROBE = """
import os, sys
sys.path.insert(0, sys.argv[1])
import atlascore, thea_mcp
def version():
    return ((thea_mcp.call("commands", {"json": True}).get("structuredContent") or {}).get("record") or {}).get("version")
print("warm", version(), thea_mcp._forkable(), flush=True)
atlascore.atlas()
input()
print("atlas-edited", version(), flush=True)
input()
print("module-edited", thea_mcp._forkable(), flush=True)
input()  # the harness has restored every planted file: a 1s child must not race that write
thea_mcp.TIMEOUT = 1
print("timeout", "timed out" in thea_mcp.call("check", {})["content"][0]["text"], flush=True)
print("parent", os.getcwd(), "THEA_READ_ONLY" in os.environ, flush=True)
"""


def _fork_answers() -> dict[str, list[str]]:
    """Run the probe through its edits; each printed line keyed by its first word."""
    probe = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", _FORK_PROBE, str(ROOT / "scripts")],
        cwd="/tmp",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "THEA_MCP_ISOLATE"},
    )
    assert probe.stdin and probe.stdout
    lines = [probe.stdout.readline()]
    with mutated("atlas.yaml", lambda t: t.replace("version: ", "version: 9", 1)):
        probe.stdin.write("\n")
        probe.stdin.flush()
        lines.append(probe.stdout.readline())
    with mutated("scripts/commands.py", lambda t: t + "\n# planted: a module edited under a warm parent\n"):
        probe.stdin.write("\n")
        probe.stdin.flush()
        lines.append(probe.stdout.readline())
    # RELEASED ONLY AFTER THE RESTORE: the timeout step ran while `mutated` was still rewriting
    # commands.py, and a child that imported it half-written crashed inside its 1s, reading False.
    out, _ = probe.communicate(input="\n", timeout=600)
    return {line.split()[0]: line.split()[1:] for line in [*lines, *out.splitlines()] if line.split()}


def mcp_fork_cases() -> None:
    """A warm parent answers from the tree on disk, never from what it imported; a slow child is killed."""
    version = str(atlas.atlas().get("version"))
    want = {
        "warm": [version, "True"],
        "atlas-edited": ["9" + version],
        "module-edited": ["False"],
        "timeout": ["True"],
        "parent": [str(Path("/tmp").resolve()), "False"],
    }
    got = _fork_answers()
    if got != want:
        raise SystemExit(f"FAIL thea-mcp fork: wanted {want}, got {got}")
    for needle, mutant, key in (
        ("value.cache_clear()", "pass", "atlas-edited"),
        ('return _WARM["stamp"] == _source_stamp()', "return True", "module-edited"),
    ):
        with mutated("scripts/thea_mcp.py", lambda t, n=needle, m=mutant: t.replace(n, m, 1)):
            planted = _fork_answers()
        if planted.get(key) == want[key]:
            raise SystemExit(f"FAIL the fork probe did not notice '{mutant}' planted for '{needle}'")
    CASES.append(
        (
            "a forked MCP call reads an edited atlas, refuses a stale module, is killed at its timeout",
            "a warm server answering from the atlas or the code it held before the edit",
        )
    )
    print("  ok    thea-mcp fork: edited atlas read fresh, stale module refused, timeout kills; two mutants caught")


def bounded_output_case() -> None:
    """THE REPLY IS BOUNDED (3.54.x): a command printing without end grew the server and the client's reply."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import thea_mcp

    cut = thea_mcp._bounded("x" * (thea_mcp.MAX_OUTPUT + 10))
    whole = thea_mcp._bounded("short")
    if whole != "short" or not cut.startswith("x" * thea_mcp.MAX_OUTPUT) or "output cut" not in cut:
        raise SystemExit("FAIL thea-mcp: an over-long output was not cut and labelled, or a short one was altered")
    saved = thea_mcp.MAX_OUTPUT
    thea_mcp.MAX_OUTPUT = 64
    try:
        shown = thea_mcp.call("thea", {"argv": ["commands"]})["content"][0]["text"]
    finally:
        thea_mcp.MAX_OUTPUT = saved
    if "output cut at 64" not in shown or len(shown) > 64 + 200:
        raise SystemExit(f"FAIL thea-mcp: a call past the cap returned {len(shown)} characters uncut")
    CASES.append(
        (
            "an MCP call's output past MAX_OUTPUT is cut and labelled",
            "a command printing without end held whole in memory",
        )
    )
    print("  ok    thea-mcp: output past the cap is cut, drained and labelled")
