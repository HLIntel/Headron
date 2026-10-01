"""Planted cases for schedtargets: each kills a named wrong implementation of the scheduler sweep (3.48.0)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path


def run(module) -> None:
    """A scheduled job whose target is gone FAILS on the host that runs it; a paused one warns (3.48.0)."""
    import schedtargets

    mac = schedtargets.MAC_HOME
    home = Path(tempfile.mkdtemp(prefix="thea-sched-"))
    try:
        (home / "live").mkdir()
        (home / ".hermes" / "scripts").mkdir(parents=True)
        (home / ".hermes" / "cron").mkdir()

        def sweep(jobs: list[dict], platform: str = "darwin") -> dict:
            (home / ".hermes" / "cron" / "jobs.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
            return schedtargets.sweep(str(home), platform, str(home / ".hermes"), fixture=True)

        def script(name: str, body: str) -> dict:
            (home / ".hermes" / "scripts" / name).write_text(body, encoding="utf-8")
            return {"name": name, "script": name}

        rows = [
            ("a live $HOME target passes", [script("ok.sh", 'cd "$HOME/live" || exit 1')], "darwin", 0, 0),
            ("a deleted repository FAILS", [script("gone.sh", "cd $HOME/gone || exit 1")], "darwin", 1, 0),
            (
                "a cd that exits zero on a dead target FAILS",
                [script("green.sh", "cd $HOME/live || exit 0")],
                "darwin",
                1,
                0,
            ),
            (
                "a macOS home path on linux FAILS",
                [{"name": "mac", "prompt": f"run {mac}x/y.sh", "workdir": f"{mac}x"}],
                "linux",
                1,
                0,
            ),
            ("a paused dead job only WARNS", [{**script("p.sh", "cd ~/gone"), "state": "paused"}], "darwin", 0, 1),
        ]
        for name, jobs, platform, faults, warns in rows:
            got = sweep(jobs, platform)
            if (bool(got["faults"]), bool(got["warns"])) != (bool(faults), bool(warns)) or not got["checked"]:
                raise SystemExit(f"FAIL {name}: {got}")
            module.CASES.append((name, "a scheduled job reporting success over a target that is not there"))
            print(f"  ok    {name}")
        units = home / ".config" / "systemd" / "user"
        (units / "timers.target.wants").mkdir(parents=True)
        (units / "job.service").write_text("[Service]\nExecStart=%h/nope/run.sh\n", encoding="utf-8")
        (units / "timers.target.wants" / "job.timer").write_text("", encoding="utf-8")
        (home / ".hermes" / "cron" / "jobs.json").unlink()
        got = schedtargets.sweep(str(home), "linux", str(home / ".hermes"), fixture=True)
        if got["jobs"] != 1 or not got["faults"]:
            raise SystemExit(f"FAIL a timer-armed unit with a missing program did not fail: {got}")
        module.CASES.append(
            ("a timer-armed unit with a missing program FAILS", "a unit nobody resolved, not being a job list")
        )
        shutil.rmtree(home / ".config")
        if schedtargets.main(["--root", str(home), "--platform", "linux"]) != 1:
            raise SystemExit("FAIL an empty roster passed")
        module.CASES.append(("an empty scheduler roster FAILS", "a clean pass over nothing"))
        print("  ok    a timer-armed unit with a missing program FAILS; an empty roster FAILS")
    finally:
        shutil.rmtree(home, ignore_errors=True)
