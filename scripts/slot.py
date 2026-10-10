#!/usr/bin/env python3
"""One heavy suite per MACHINE, across every repository and every agent: `thea slot -- <command>`.

WHY. The suite lock was one per repository (its git common dir), so a thea verify, another repo's
vitest pool and a go test ran at once on the same cores. MEASURED on an 8-core machine: load 22-37,
the desktop UI starved (flicker, flipped panes), and two suites in two worktrees each ran past verify's
timeout (a 289 s suite took 558.6 s). The cores are the machine's, so the slot is the machine's.

CONTRACT (any tool may consume it; none forks it):
- the slot is an flock on THEA_SLOT_LOCK, else ~/.thea/suite.lock; the holder writes who it is into it;
- a holder exports THEA_SLOT_HELD=<pid>, and a child that sees a live holder runs inside the slot;
- a busy slot is BUSY (exit 75): the caller reports NOT RUN with the holder named, never a FAIL;
- `thea slot` runs its command at utility QoS on macOS with THEA_SLOT_WORKERS (default 2) workers
  for go, vitest, pytest-xdist and cargo. Background QoS is refused by design: it measured 13x slower
  under load (40.6 s against 3.1 s) and would trip every suite timeout.
WHAT IT DOES NOT PROVE: that a command is heavy. Which commands must take the slot is the caller's gate.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import subprocess
import sys
from pathlib import Path

BUSY = 75  # EX_TEMPFAIL, the code atlas_test and verify already read as NOT RUN


def lock_path() -> Path:
    return Path(os.environ.get("THEA_SLOT_LOCK") or Path.home() / ".thea" / "suite.lock")


def inherited() -> bool:
    """True when a live ancestor holds the slot and handed it down through THEA_SLOT_HELD."""
    pid = os.environ.get("THEA_SLOT_HELD", "")
    if not pid.isdigit():
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _try(label: str):
    """The held handle, or the holder's description when another process holds it."""
    path = lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+")  # noqa: SIM115 — the open descriptor IS the lock; closing releases it
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.seek(0)
        who = handle.read().strip() or "an unrecorded process"
        handle.close()
        return who
    handle.seek(0)
    handle.truncate()
    handle.write(f"pid {os.getpid()}: {label}")
    handle.flush()
    os.environ["THEA_SLOT_HELD"] = str(os.getpid())
    return handle


def take(label: str, wait: float = 0.0, say=print):
    """Hold the machine slot until the returned handle closes; None when an ancestor already holds it.

    Waits up to `wait` seconds, then raises SystemExit(BUSY) naming the holder."""
    if inherited():
        return None
    from resilience import wait_until

    got = []

    def free() -> bool:
        result = _try(label)
        if isinstance(result, str):
            if not got:
                say(f"slot: {result} holds the machine's suite slot; waiting up to {wait:.0f}s", file=sys.stderr)
            got[:] = [result]
            return False
        got[:] = [result]
        return True

    if free() or (wait > 0 and wait_until(free, timeout=wait, interval=2)):
        return got[0]
    say(
        f"BUSY: another suite holds this machine's slot ({got[0]}). Resolution: wait on that PID, "
        "then re-run; two suites at once both slow past verify's timeout",
        file=sys.stderr,
    )
    raise SystemExit(BUSY)


def wait_free(wait: float, say=print) -> bool:
    """Wait until the slot is free (taking and releasing it); False at the deadline. Never holds it."""
    try:
        handle = take("probe", wait, say)
    except SystemExit:
        return False
    if handle is not None:
        handle.close()
        os.environ.pop("THEA_SLOT_HELD", None)
    return True


def capped_env(workers: int) -> dict[str, str]:
    env = dict(os.environ)
    n = str(workers)
    # REPLACED, never appended: a slot inside a slot (a land's gates under `heavy`) inherited `-p=2` and
    # handed down `-p=2 -p=2`; go takes the last, but the cap must read as one value to every reader.
    kept = [f for f in env.get("GOFLAGS", "").split() if not f.startswith("-p=")]
    env["GOFLAGS"] = " ".join([*kept, f"-p={n}"])
    env.update(VITEST_MAX_FORKS=n, VITEST_MAX_THREADS=n, PYTEST_XDIST_AUTO_NUM_WORKERS=n, CARGO_BUILD_JOBS=n)
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thea slot", description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--wait", type=float, default=3600.0, help="seconds to wait for a busy slot, then BUSY (75)")
    parser.add_argument("--timeout", type=float, default=7200.0, help="seconds the command may run, then 124")
    parser.add_argument("--status", action="store_true", help="print the holder; exit 0 free, 75 held")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="-- the command to run inside the slot")
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.status:
        result = None if inherited() else _try("status")
        if isinstance(result, str):
            print(f"held: {result}")
            return BUSY
        print("free" if result is not None else f"held by this process tree (pid {os.environ['THEA_SLOT_HELD']})")
        return 0
    if not command:
        parser.error("a command to run is required: thea slot -- <command>")
    _held = take(" ".join(command)[:200], args.wait)  # noqa: F841 — held until exit
    env = capped_env(int(os.environ.get("THEA_SLOT_WORKERS") or 2))
    policy = ["taskpolicy", "-c", "utility"] if sys.platform == "darwin" and shutil.which("taskpolicy") else []
    try:
        return subprocess.run(policy + command, env=env, check=False, timeout=args.timeout).returncode  # noqa: S603
    except subprocess.TimeoutExpired:
        print(f"slot: {command[0]} ran past --timeout {args.timeout:.0f}s and was killed", file=sys.stderr)
        return 124
    except FileNotFoundError:
        print(f"slot: command not found: {command[0]}", file=sys.stderr)
        return 127
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
