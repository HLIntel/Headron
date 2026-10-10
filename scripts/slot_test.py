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
        env = {**os.environ, "THEA_SLOT_LOCK": str(Path(tmp) / "suite.lock"), "THEA_SLOTS": "1"}
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


def _hold(env):
    return subprocess.Popen([sys.executable, SLOT, "--", sys.executable, "-c", "import time; time.sleep(30)"], env=env)


def second_slot_case() -> None:
    """One slot queued a land's CI an hour behind another repository's: THEA_SLOTS=2 runs the second, refuses the third."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "THEA_SLOT_LOCK": str(Path(tmp) / "suite.lock"), "THEA_SLOTS": "2"}
        env.pop("THEA_SLOT_HELD", None)
        lock = Path(tmp) / "suite.lock"
        first = _hold(env)
        try:
            if not wait_until(lambda: lock.exists() and lock.read_text().startswith("pid"), timeout=20, interval=0.2):
                raise SystemExit("FAIL the first holder never took slot 1")
            if _run(env, "--wait", "0", "--", "true").returncode != 0:
                raise SystemExit("FAIL a second suite was refused while slot 2 was free")
            second = _hold(env)
            try:
                if not wait_until(lambda: _run(env, "--status").returncode == 75, timeout=20, interval=0.2):
                    raise SystemExit("FAIL two holders did not fill both slots")
                third = _run(env, "--wait", "0", "--", "true")
                if (
                    third.returncode != 75
                    or f"pid {first.pid}" not in third.stderr
                    or f"pid {second.pid}" not in third.stderr
                ):
                    raise SystemExit(
                        f"FAIL a third suite was not BUSY naming both holders: {third.returncode} {third.stderr!r}"
                    )
            finally:
                second.kill()
                second.wait(timeout=30)
        finally:
            first.kill()
            first.wait(timeout=30)
        if _run({**env, "THEA_SLOTS": "0"}, "--status").returncode == 0:
            raise SystemExit("FAIL THEA_SLOTS=0 was accepted instead of refused")
    print("  ok    two slots: the second suite runs, the third is BUSY naming both holders, a bad count refuses")


def root_env_case() -> None:
    """`thea slot` exported its install's THEA_ROOT to the command: a worktree suite checked the main checkout."""
    scripts = Path(__file__).resolve().parent
    probe = "import os; print(os.environ.get('THEA_ROOT', 'unset'), os.environ.get('CODE_DEVELOPMENT_ROOT', 'unset'))"
    cli = f"import sys; sys.path.insert(0, {str(scripts)!r}); import atlas_cli; sys.exit(atlas_cli.main(sys.argv[1:]))"
    with tempfile.TemporaryDirectory() as tmp:
        env = {k: v for k, v in os.environ.items() if k not in ("THEA_ROOT", "CODE_DEVELOPMENT_ROOT", "THEA_SLOT_HELD")}
        env["THEA_SLOT_LOCK"] = str(Path(tmp) / "suite.lock")
        args = [sys.executable, "-c", cli, "--atlas-root", str(scripts.parent), "slot", "--wait", "0", "--"]
        done = subprocess.run([*args, sys.executable, "-c", probe], env=env, capture_output=True, text=True, timeout=60)
        if done.returncode != 0 or done.stdout.split() != ["unset", "unset"]:
            raise SystemExit(f"FAIL thea slot handed its own root to the command: {done.returncode} {done.stdout!r}")
    print("  ok    thea slot hands the command the caller's root variables, not its install's")


def atlas_busy_case() -> None:
    """Pinned to slot 1 alone, the planted suite passed or failed on whichever slot its parent happened to hold."""
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        lock = Path(tmp) / "suite.lock"
        env = {**os.environ, "THEA_SLOT_LOCK": str(lock), "THEA_SLOTS": "1", "ATLAS_LOCK_WAIT": "0"}
        env.pop("THEA_SLOT_HELD", None)
        holder = _hold(env)
        try:
            if not wait_until(lambda: lock.exists() and lock.read_text().startswith("pid"), timeout=20, interval=0.2):
                raise SystemExit("FAIL the holder never took the slot")
            suite = subprocess.run(
                [sys.executable, "scripts/atlas_test.py"], cwd=root, env=env, capture_output=True, timeout=120
            )
        finally:
            holder.kill()
            holder.wait(timeout=30)
    if suite.returncode != 75:
        raise SystemExit(f"FAIL a planted suite on a held slot was not refused BUSY: {suite.returncode}")
    print("  ok    a planted suite on a held machine slot is refused BUSY at once")


def run(module) -> None:
    slot_case(module)
    second_slot_case()
    root_env_case()
    atlas_busy_case()


if __name__ == "__main__":
    run(None)
