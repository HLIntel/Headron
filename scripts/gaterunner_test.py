"""Tests for gaterunner.py: a SIGTERM to the runner stops the gate's process group instead of orphaning it.

proves: a runner terminated mid-gate exits 143 and leaves no gate process alive; the handler is removed after
  `run` returns, and a handler the caller set is kept
does_not_prove: SIGKILL (it cannot be caught; nothing in-process can stop children then), or Windows
closed_by: scripts/gaterunner_test.py
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import gaterunner
from resilience import wait_until

HERE = Path(__file__).resolve().parent


def _alive(token: str) -> bool:
    return subprocess.run(["pgrep", "-f", token], capture_output=True, check=False, timeout=10).returncode == 0


def test_sigterm_stops_the_gate_group() -> None:
    if os.name != "posix":
        return
    token = f"headron-gate-{uuid.uuid4().hex[:12]}"
    # The token is split in the runner's own argv so pgrep matches the gate alone, never the runner.
    code = (
        "import sys, gaterunner; "
        f"gaterunner.run([sys.executable, '-c', 'import time; time.sleep(600)', {token[:8]!r} + {token[8:]!r}], "
        "timeout=120)"
    )
    runner = subprocess.Popen([sys.executable, "-c", code], cwd=HERE, env={**os.environ, "PYTHONPATH": str(HERE)})
    try:
        assert wait_until(lambda: _alive(token), timeout=30, interval=0.1), "the gate never started"
        runner.send_signal(signal.SIGTERM)
        assert runner.wait(timeout=30) == 143, runner.returncode
        wait_until(lambda: not _alive(token), timeout=5, interval=0.1)
        assert not _alive(token), "the gate outlived its terminated runner: orphaned"
    finally:
        if runner.poll() is None:
            runner.kill()
        subprocess.run(["pkill", "-f", token], check=False, timeout=10)


def test_sigterm_stops_every_running_graph_node() -> None:
    """Width 2 through micrograph: SIGTERM reaches the main thread, its `finally` stops both nodes' groups."""
    if os.name != "posix":
        return
    token = f"headron-node-{uuid.uuid4().hex[:12]}"
    mark = Path(tempfile.mkdtemp()) / "stopping"
    code = f"""
import subprocess, sys, time, gaterunner, micrograph
MARK = {str(mark)!r}
class Sleeper:
    def __init__(self, name):
        self.p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)", {token[:8]!r} + {token[8:]!r}],
                                  start_new_session=True)
    def poll(self):
        return None
    def stop(self):
        open(MARK, "a").close()
        time.sleep(1)  # a stop slow enough that the second TERM lands inside it
        gaterunner._stop(self.p)
nodes = [micrograph.Node("a", timeout_s=120), micrograph.Node("b", timeout_s=120)]
with gaterunner.stop_children_on_sigterm():
    micrograph.run(nodes, lambda node, _t: Sleeper(node.name), budget_s=240, width=2)
"""
    runner = subprocess.Popen([sys.executable, "-c", code], cwd=HERE, env={**os.environ, "PYTHONPATH": str(HERE)})

    def count() -> int:
        return len(subprocess.run(["pgrep", "-f", token], capture_output=True, text=True, timeout=10).stdout.split())

    try:
        assert wait_until(lambda: count() == 2, timeout=30, interval=0.1), "both nodes never started"
        runner.send_signal(signal.SIGTERM)
        assert wait_until(mark.exists, timeout=30, interval=0.05), "the graph never began stopping"
        runner.send_signal(signal.SIGTERM)  # a forwarded second TERM, mid-stop, must not cut the stop short
        assert runner.wait(timeout=30) == 143, runner.returncode
        wait_until(lambda: count() == 0, timeout=5, interval=0.1)
        assert count() == 0, "a graph node outlived its terminated runner: orphaned"
    finally:
        if runner.poll() is None:
            runner.kill()
        subprocess.run(["pkill", "-f", token], check=False, timeout=10)


def test_handler_scoped_and_caller_kept() -> None:
    if os.name != "posix":
        return
    assert gaterunner.run([sys.executable, "-c", "pass"], timeout=30).returncode == 0
    assert signal.getsignal(signal.SIGTERM) is signal.SIG_DFL, "run left its handler installed"

    def mine(_signum: int, _frame: object) -> None:
        return None

    previous = signal.signal(signal.SIGTERM, mine)
    try:
        with gaterunner.stop_children_on_sigterm():
            assert signal.getsignal(signal.SIGTERM) is mine, "a caller's handler was replaced"
    finally:
        signal.signal(signal.SIGTERM, previous)


def run_cases() -> None:
    for case in (
        test_sigterm_stops_the_gate_group,
        test_sigterm_stops_every_running_graph_node,
        test_handler_scoped_and_caller_kept,
    ):
        case()
        print(f"  ok    {case.__name__}")


if __name__ == "__main__":
    run_cases()
    print("PASS  gaterunner_test")
