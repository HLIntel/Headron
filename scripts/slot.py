#!/usr/bin/env python3
"""A few heavy suites per MACHINE, across every repository and every agent: `headron slot -- <command>`.

WHY. The suite lock was one per repository (its git common dir), so a headron verify, another repo's
vitest pool and a go test ran at once on the same cores. MEASURED on an 8-core machine: load 22-37,
the desktop UI starved (flicker, flipped panes), and two suites in two worktrees each ran past verify's
timeout (a 289 s suite took 558.6 s). The cores are the machine's, so the slot is the machine's.

MORE THAN ONE, SIZED BY THE MACHINE (3.54.0). One slot queued a land's CI an hour behind another
repository's, on a machine with cores to spare. Each suite is capped at HEADRON_SLOT_WORKERS,
so the machine fits cores / (2 x workers) of them (8 cores, 2 workers: 2 slots), and a slot past the
first is taken only while at least HEADRON_SLOT_IDLE of the cores (default 0.25) sat idle over a 1 s sample
of the kernel's CPU ticks: a busy machine falls back to one suite, which is the measured failure above.

IDLE TICKS, NOT LOAD AVERAGE. The gate first read the 1-minute load, which counts threads waiting on I/O as
well as running ones. MEASURED on the same 8-core machine: load 14-22 while `top` showed 29-36% idle, so the
ceiling (6) withheld every slot past the first and a land's CI ran its units one at a time on
a machine with 2.5 cores free. A host with no tick reader (neither /proc/stat nor Mach) is never granted a
second slot. `admitter()` adds a settle: after a grant the next is judged only once the new suite's load
can show in a sample.

CONTRACT (any tool may consume it; none forks it):
- slot 1 is an flock on HEADRON_SLOT_LOCK, else ~/.headron/suite.lock; slot n is that path + `.n`; a holder
  takes the first free one and writes who it is into it; HEADRON_SLOTS overrides how many there are;
- a holder exports HEADRON_SLOT_HELD=<pid>, and a child that sees a live holder runs inside the slot;
- a waiter queues first-come-first-served (tickets under `<lock>.queue`, a dead one swept) and runs when
  it reaches the head and a slot is free; BUSY (exit 75) only at the wait's deadline or with `--wait 0`,
  and the caller reports NOT RUN with the holder named, never a FAIL; the holder records HEADRON_AGENT;
- `headron slot` runs its command at utility QoS on macOS with HEADRON_SLOT_WORKERS (default 2) workers
  for go, vitest, pytest-xdist and cargo. Background QoS is refused by design: it measured 13x slower
  under load (40.6 s against 3.1 s) and would trip every suite timeout.
WHAT IT DOES NOT PROVE: that a command is heavy. Which commands must take the slot is the caller's gate.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

BUSY = 75  # EX_TEMPFAIL, the code atlas_test and verify already read as NOT RUN
IDLE_FLOOR = 0.25  # of the cores: the idle share a slot past the first needs; the rest is the desktop's headroom
SAMPLE_S = 1.0  # seconds between the two tick reads one verdict compares
SETTLE_S = 10.0  # after a grant, seconds before the next is judged: a unit's worktree and install hide its load


def lock_path() -> Path:
    return Path(os.environ.get("HEADRON_SLOT_LOCK") or Path.home() / ".headron" / "suite.lock")


def workers() -> int:
    return int(os.environ.get("HEADRON_SLOT_WORKERS") or 2)


def slot_count() -> int:
    raw = os.environ.get("HEADRON_SLOTS", "")
    if not raw:
        return max(1, (os.cpu_count() or 1) // (2 * workers()))
    if not raw.isdigit() or int(raw) < 1:
        raise SystemExit(f"slot: HEADRON_SLOTS={raw!r} is not a positive integer; refusing to guess a slot count")
    return int(raw)


def lock_paths() -> list[Path]:
    first = lock_path()
    return [first, *(first.with_name(f"{first.name}.{n}") for n in range(2, slot_count() + 1))]


def cpu_ticks() -> tuple[int, int] | None:
    """(idle, total) CPU ticks since boot over every core; None on a host with no reader."""
    if sys.platform.startswith("linux"):
        try:
            first = Path("/proc/stat").read_text().split("\n", 1)[0].split()
            fields = [int(x) for x in first[1:9]]  # user nice system idle iowait irq softirq steal; guest is in user
        except (OSError, ValueError):
            return None
        return fields[3] + fields[4], sum(fields)
    if sys.platform == "darwin":
        import ctypes

        try:
            lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        except OSError:
            return None
        lib.mach_host_self.restype = ctypes.c_uint32
        lib.host_statistics.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32))
        info, count = (ctypes.c_uint32 * 4)(), ctypes.c_uint32(4)  # HOST_CPU_LOAD_INFO: user, system, idle, nice
        if lib.host_statistics(lib.mach_host_self(), 3, info, ctypes.byref(count)) != 0:
            return None
        return info[2], sum(info)
    return None


def idle_share(
    read: Callable[[], tuple[int, int] | None] = cpu_ticks, wait: Callable[[float], object] = time.sleep
) -> float | None:
    """The share of all cores idle across one SAMPLE_S window; None when the host cannot say."""
    first = read()
    if first is None:
        return None
    wait(SAMPLE_S)
    second = read()
    if second is None:
        return None
    # Mach ticks are 32-bit counters that wrap; a delta modulo 2**32 is exact for any window under ~60 days.
    idle, total = ((b - a) % 2**32 for a, b in zip(first, second, strict=True))
    return idle / total if total else None


def idle_floor() -> float:
    raw = os.environ.get("HEADRON_SLOT_IDLE", "")
    try:
        return float(raw) if raw else IDLE_FLOOR
    except ValueError:
        raise SystemExit(f"slot: HEADRON_SLOT_IDLE={raw!r} is not a number; refusing to guess a floor") from None


def spare_cores(
    read: Callable[[], tuple[int, int] | None] = cpu_ticks, wait: Callable[[float], object] = time.sleep
) -> bool:
    """True when HEADRON_SLOT_IDLE of the cores sat idle over one sample; never on a host that cannot measure."""
    floor = idle_floor()
    if floor <= 0:
        return True  # the operator's (or a test's) explicit "do not measure"
    share = idle_share(read, wait)
    return share is not None and share >= floor


def withheld(k: int) -> str:
    return f"slot {k} withheld: under {idle_floor():.0%} of {os.cpu_count()} cores idle"


def admitter(
    settle_s: float = SETTLE_S, clock: Callable[[], float] = time.monotonic, room: Callable[[], bool] = spare_cores
) -> Callable[[], bool]:
    """spare_cores for a caller that starts a suite on each True: no second grant within settle_s of the last."""
    granted: list[float] = []

    def admit() -> bool:
        if idle_floor() > 0 and granted and clock() - granted[-1] < settle_s:
            return False  # a floor of 0 measures nothing, so there is no load to wait for
        if not room():
            return False
        granted.append(clock())
        return True

    return admit


def inherited() -> bool:
    """True when a live ancestor holds the slot and handed it down through HEADRON_SLOT_HELD."""
    pid = os.environ.get("HEADRON_SLOT_HELD", "")
    if not pid.isdigit():
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _flock(path: Path, label: str):
    """The held handle for one slot file, or its holder's description when another process holds it."""
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
    return handle


def _try(label: str):
    """A held handle for the first free slot, or every holder's description when none can be taken."""
    held = []
    for k, path in enumerate(lock_paths()):
        if k and not spare_cores():
            held.append(withheld(k))
            break
        result = _flock(path, label)
        if not isinstance(result, str):
            os.environ["HEADRON_SLOT_HELD"] = str(os.getpid())
            return result
        held.append(result)
    return "; ".join(held)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def queue_dir() -> Path:
    first = lock_path()
    return first.with_name(f"{first.name}.queue")


def _enqueue() -> Path:
    """A ticket in arrival order: a zero-padded clock then the pid, so a sort is first-come-first-served."""
    directory = queue_dir()
    directory.mkdir(parents=True, exist_ok=True)
    ticket = directory / f"{time.time_ns():020d}-{os.getpid()}"
    ticket.touch()
    return ticket


def _at_head(ticket: Path) -> bool:
    """True when `ticket` is the earliest live ticket. A ticket whose process died is swept, never waited on."""
    live = []
    for other in sorted(queue_dir().iterdir()):
        pid = other.name.rsplit("-", 1)[-1]
        if pid.isdigit() and _alive(int(pid)):
            live.append(other)
        else:
            other.unlink(missing_ok=True)
    return bool(live) and live[0] == ticket


def take(label: str, wait: float = 0.0, say: Callable[..., object] = print):
    """Hold the machine slot until the returned handle closes; None when an ancestor already holds it.

    `wait=0` is one attempt: BUSY (75) at once, naming the holder. `wait>0` joins a first-come-first-served
    queue and runs when it reaches the head and a slot is free; BUSY only at the deadline. The holder records
    HEADRON_AGENT (the agent or chat that asked) so a waiter can see whose turn it is."""
    if inherited():
        return None
    from resilience import divergent_interval, wait_until

    agent = os.environ.get("HEADRON_AGENT", "")
    who = f"{agent}: {label}" if agent else label
    got = []

    def free() -> bool:
        result = _try(who)
        got[:] = [result]
        return not isinstance(result, str)

    if free():
        return got[0]
    if wait <= 0:
        say(
            f"BUSY: every suite slot on this machine is taken ({got[0]}). Resolution: wait on a PID named, "
            "then re-run; more suites than slots slow past verify's timeout",
            file=sys.stderr,
        )
        raise SystemExit(BUSY)
    ticket = _enqueue()
    say(f"slot: queued behind {got[0]}; waiting up to {wait:.0f}s, first come runs first", file=sys.stderr)

    def my_turn() -> bool:
        return _at_head(ticket) and free()

    try:
        if wait_until(my_turn, timeout=wait, interval=divergent_interval):
            return got[0]
    finally:
        ticket.unlink(missing_ok=True)
    say(f"BUSY: queue wait ran out after {wait:.0f}s; slot still held by {got[0]}", file=sys.stderr)
    raise SystemExit(BUSY)


def wait_free(wait: float, say: Callable[..., object] = print) -> bool:
    """Wait until the slot is free (taking and releasing it); False at the deadline. Never holds it."""
    try:
        handle = take("probe", wait, say)
    except SystemExit:
        return False
    if handle is not None:
        handle.close()
        os.environ.pop("HEADRON_SLOT_HELD", None)
    return True


def slot_status() -> dict:
    """Return the current slot state as a dict: queue depth, holders, load, and slot count.

    This provides telemetry for dashboards and cross-session analysis. The dict includes:
    - slots: total number of slots on this machine
    - held: list of holder descriptions for occupied slots
    - free: number of free slots
    - queue_depth: number of processes waiting in the FCFS queue
    - load_1m: current 1-minute load average
    - cores: CPU count
    - inherited: whether this process tree inherited a slot from an ancestor
    """
    inh = inherited()
    holders = []
    free_count = 0
    for k, path in enumerate(lock_paths()):
        if k and not spare_cores():
            holders.append(withheld(k))
            continue
        try:
            with open(path, "r") as handle:
                try:
                    fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
                except BlockingIOError:
                    # Held: the file names the live holder. A takeable lock is free whatever its text says,
                    # since a holder's note outlives its release.
                    holders.append(handle.read().strip() or f"slot {k} held")
                    continue
            free_count += 1
        except OSError:
            # Slot file doesn't exist or can't be read — count as free
            free_count += 1

    queue_depth = 0
    try:
        qdir = queue_dir()
        if qdir.exists():
            for ticket in qdir.iterdir():
                pid = ticket.name.rsplit("-", 1)[-1]
                if pid.isdigit() and _alive(int(pid)):
                    queue_depth += 1
    except OSError:
        pass

    return {
        "slots": slot_count(),
        "held": len(holders),
        "free": free_count,
        "queue_depth": queue_depth,
        "load_1m": round(os.getloadavg()[0], 2),
        "cores": os.cpu_count() or 1,
        "inherited": inh,
        "divergent_spacing": True,
    }


def capped_env(workers: int) -> dict[str, str]:
    env = dict(os.environ)
    n = str(workers)
    # REPLACED, never appended: a slot inside a slot (a land's gates under `heavy`) inherited `-p=2` and
    # handed down `-p=2 -p=2`; go takes the last, but the cap must read as one value to every reader.
    kept = [f for f in env.get("GOFLAGS", "").split() if not f.startswith("-p=")]
    env["GOFLAGS"] = " ".join([*kept, f"-p={n}"])
    # the caller's root variables, not the ones atlas_cli exported for this install: a worktree suite under heavy
    # checked the main checkout's tree (3.53.0). atlas_cli is absent when slot.py runs bare.
    cli = sys.modules.get("atlas_cli")
    caller = getattr(cli, "CALLER_ENV", None)
    for var, value in {v: caller.get(v) for v in ("HEADRON_ROOT", "CODE_DEVELOPMENT_ROOT")}.items() if caller else ():
        if value is None:
            env.pop(var, None)
        else:
            env[var] = value
    env.update(VITEST_MAX_FORKS=n, VITEST_MAX_THREADS=n, PYTEST_XDIST_AUTO_NUM_WORKERS=n, CARGO_BUILD_JOBS=n)
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="headron slot", description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--wait", type=float, default=3600.0, help="seconds to wait for a busy slot, then BUSY (75)")
    parser.add_argument("--timeout", type=float, default=7200.0, help="seconds the command may run, then 124")
    parser.add_argument("--status", action="store_true", help="print the holder; exit 0 free, 75 held")
    parser.add_argument("--status-json", action="store_true", help="print slot telemetry as JSON")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="-- the command to run inside the slot")
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.status_json:
        print(json.dumps(slot_status(), indent=2))
        return 0
    if args.status:
        result = None if inherited() else _try("status")
        if isinstance(result, str):
            print(f"held: {result}")
            return BUSY
        if result is not None:
            result.close()
        print(
            f"free ({slot_count()} slots)"
            if result is not None
            else f"held by this process tree (pid {os.environ['HEADRON_SLOT_HELD']})"
        )
        return 0
    if not command:
        parser.error("a command to run is required: headron slot -- <command>")
    _held = take(" ".join(command)[:200], args.wait)  # noqa: F841 — held until exit
    env = capped_env(workers())
    # QoS: macOS uses taskpolicy for utility class; Linux uses nice for lower priority.
    # Background QoS is refused by design: it measured 13x slower under load.
    if sys.platform == "darwin" and shutil.which("taskpolicy"):
        policy = ["taskpolicy", "-c", "utility"]
    elif shutil.which("nice"):
        policy = ["nice", "-n", "10"]  # Linux: lower priority by 10 levels
    else:
        policy = []
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
