"""Bounded process capture shared by verification, landing and local enforcement.

Drain pipes continuously while retaining only their tails. A noisy tool cannot
grow memory or a temporary log without bound. The deadline includes descendants
holding a pipe open; on POSIX the isolated process group is stopped together.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass


@dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str
    output_bytes: int


def _drain(pipe, tail: bytearray, count: list[int], keep: int, ended: threading.Event) -> None:
    try:
        while chunk := pipe.read(65536):
            count[0] += len(chunk)
            tail.extend(chunk)
            if len(tail) > keep:
                del tail[:-keep]
    finally:
        pipe.close()
        ended.set()


def _stop(process: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def run(argv, *, cwd=None, timeout: float, env=None, keep: int = 65536, merge: bool = False) -> Result:
    """Return the real exit code and bounded UTF-8 tails; timeout never means PASS."""
    if keep <= 0 or timeout <= 0:
        raise ValueError("capture size and timeout must be positive")
    deadline = time.monotonic() + timeout
    with subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge else subprocess.PIPE,
        start_new_session=os.name == "posix",
    ) as process:
        tails, counts, events = [], [], []
        for pipe in (process.stdout, process.stderr):
            if pipe is None:
                continue
            tail, count, ended = bytearray(), [0], threading.Event()
            tails.append(tail)
            counts.append(count)
            events.append(ended)
            threading.Thread(target=_drain, args=(pipe, tail, count, keep, ended), daemon=True).start()
        try:
            code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
            for ended in events:
                if not ended.wait(max(0, deadline - time.monotonic())):
                    raise subprocess.TimeoutExpired(argv, timeout)
        except BaseException:
            _stop(process)
            for ended in events:
                ended.wait(1)
            raise
        text = [tail.decode("utf-8", errors="replace") for tail in tails]
        return Result(code, text[0], "" if merge else text[1], sum(count[0] for count in counts))
