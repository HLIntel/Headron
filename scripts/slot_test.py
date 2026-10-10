#!/usr/bin/env python3
"""Planted case: one heavy suite per machine, across repositories — slot.py refuses the second, never deadlocks the nested."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from resilience import wait_until

SLOT = str(Path(__file__).resolve().parent / "slot.py")


def _run(env, *args, timeout=60):
    return subprocess.run([sys.executable, SLOT, *args], env=env, capture_output=True, text=True, timeout=timeout)


def slot_case(module) -> None:
    """The suite lock was one per git common dir: another repository's suite took the same cores unrefused."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "THEA_SLOT_LOCK": str(Path(tmp) / "suite.lock")}
        env.pop("THEA_SLOT_HELD", None)
        env["GOFLAGS"] = "-mod=mod -p=8"  # an outer slot's cap is replaced, other flags kept
        probe = "import os; print(os.environ['GOFLAGS'], os.environ['THEA_SLOT_HELD'].isdigit())"
        done = _run(env, "--", sys.executable, "-c", probe)
        if done.returncode != 0 or done.stdout.split() != ["-mod=mod", "-p=2", "True"]:
            raise SystemExit(
                f"FAIL a free slot did not run its command capped and handed down: {done.returncode} {done.stdout!r}"
            )
        if _run(env, "--", sys.executable, "-c", "raise SystemExit(7)").returncode != 7:
            raise SystemExit("FAIL slot swallowed its command's exit code")
        holder = subprocess.Popen(
            [sys.executable, SLOT, "--", sys.executable, "-c", "import time; time.sleep(30)"], env=env
        )
        try:
            if not wait_until(lambda: _run(env, "--status").returncode == 75, timeout=20, interval=0.2):
                raise SystemExit("FAIL the holder never showed as holding the slot")
            second = _run(env, "--wait", "0", "--", "true")
            if second.returncode != 75 or f"pid {holder.pid}" not in second.stderr:
                raise SystemExit(
                    f"FAIL a second suite on a held slot was not BUSY naming the holder: {second.returncode} {second.stderr!r}"
                )
            forged = _run({**env, "THEA_SLOT_HELD": "999999"}, "--wait", "0", "--", "true")
            if forged.returncode != 75:
                raise SystemExit("FAIL a dead THEA_SLOT_HELD pid was trusted as the slot's holder")
        finally:
            holder.kill()
            holder.wait(timeout=30)
        nested = _run(env, "--", sys.executable, SLOT, "--wait", "0", "--", "true")
        if nested.returncode != 0:
            raise SystemExit(
                f"FAIL a suite inside the slot deadlocked on its own holder: {nested.returncode} {nested.stderr!r}"
            )
        if _run(env, "--status").returncode != 0:
            raise SystemExit("FAIL a killed holder's slot was not released")
    print("  ok    one suite per machine: the second is BUSY naming the holder, the nested runs inside")


def run(module) -> None:
    slot_case(module)


if __name__ == "__main__":
    run(None)
