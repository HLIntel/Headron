#!/usr/bin/env python3
"""Every ACTIVE scheduled job's target must exist on THIS host — `thea schedtargets [--root DIR] [--platform P]`.

WHY (3.48.0). A scheduled job ran every half hour for a repository deleted long before, and its jobs file
was copied verbatim to a second host of another platform, where its paths could never exist. The wrapper
said `cd X || { echo ...; exit 0; }`, so every run reported SUCCESS on both hosts. Nothing resolved a
scheduler's targets: a probe of periodicity proves the job fires, never that what it fires at is there.
This is the second sighting of `a_hook_that_runs_a_deleted_script`, one layer out.

SOURCES: an agent job list ($HERMES_HOME/cron/jobs.json) · launchd user agents (darwin) · user units a
`*.wants/` directory links, directly or through their timer (linux) · the user crontab.
FAULTS on an active job: a missing script, program, working directory or cd/exec/interpreter target; a
macOS home path on linux; a `cd X || ... exit 0` that turns a dead target into a green run. A paused job
with the same fault WARNS — it resumes silently the day someone un-pauses it. An empty roster FAILS:
a pass over nothing is not a pass.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_EXT = re.compile(r"\.(sh|zsh|bash|mjs|js|py|ts)$")
_INTERP = r"(?:(?:ba|z)?sh|node|python3?|bun|deno)"
TARGET_RES = [
    re.compile(r"(?:^|[\s;&|({])cd\s+(\"[^\"]+\"|[^\s;&|)]+)"),
    re.compile(r"(?:^|[\s;&|({])(?:exec|source|\.)\s+(?:\S*/)?" + _INTERP + r"?\s*(\"[^\"]+\"|[~$/][^\s;&|)]+)"),
    re.compile(r"(?:^|[\s;&|({])(?:/\S*/)?" + _INTERP + r"\s+(\"[^\"]+\"|[~$/][^\s;&|)]+)"),
]
GREEN_ON_DEAD = re.compile(r"\bcd\b[^\n]*\|\|[^\n]*\bexit\s+0\b")
MAC_HOME = "/Users/"  # a home on darwin; a path under it can never exist on linux
BLIND_SPOT = (
    "targets built from variables other than HOME, paths a program opens at runtime, "
    "system units, other users' crontabs"
)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def expand(raw: str, home: str) -> str:
    """Quotes first, THEN the home forms — the other order left every quoted "$HOME/x" unchecked."""
    p = raw.strip('"')
    for prefix in ("~/", "$HOME/", "${HOME}/", "%h/"):
        if p.startswith(prefix):
            return home + "/" + p[len(prefix) :]
    return p


def hermes_jobs(hermes: Path) -> list[dict]:
    text = _read(hermes / "cron" / "jobs.json")
    if not text:
        return []
    data = json.loads(text)
    rows = data if isinstance(data, list) else data.get("jobs") or []
    return [
        {
            "src": "hermes",
            "name": j.get("name") or j.get("id"),
            "active": j.get("enabled") is not False
            and not re.search(r"paused|disabled", str(j.get("state") or ""), re.I),
            "script": str(hermes / "scripts" / j["script"]) if j.get("script") else None,
            "text": j.get("prompt") or "",
            "workdir": j.get("workdir"),
        }
        for j in rows
    ]


def launchd_jobs(home: Path) -> list[dict]:
    agents, jobs = home / "Library" / "LaunchAgents", []
    for plist in sorted(agents.glob("*.plist")) if agents.is_dir() else []:
        raw = plist.read_bytes()
        if raw.startswith(b"bplist"):
            try:
                done = subprocess.run(
                    ["plutil", "-convert", "xml1", "-o", "-", str(plist)], capture_output=True, text=True, timeout=10
                )
                x = done.stdout if done.returncode == 0 else ""
            except subprocess.TimeoutExpired:
                x = ""
        else:
            x = raw.decode("utf-8", errors="replace")
        arr = re.search(r"<key>ProgramArguments</key>\s*<array>([\s\S]*?)</array>", x)
        args = re.findall(r"<string>([^<]*)</string>", arr.group(1)) if arr else []
        prog = re.search(r"<key>Program</key>\s*<string>([^<]*)<", x)
        wd = re.search(r"<key>WorkingDirectory</key>\s*<string>([^<]*)<", x)
        script = next((a for a in args[1:] if a.startswith("/") and SCRIPT_EXT.search(a)), None)
        jobs.append(
            {
                "src": "launchd",
                "name": plist.name,
                "active": not re.search(r"<key>Disabled</key>\s*<true/>", x),
                "program": prog.group(1) if prog else (args[0] if args else None),
                "script": script,
                "workdir": wd.group(1) if wd else None,
            }
        )
    return jobs


def systemd_jobs(home: Path) -> list[dict]:
    units = home / ".config" / "systemd" / "user"
    if not units.is_dir():
        return []
    wanted = {link.name for d in units.glob("*.wants") for link in d.iterdir()}
    jobs = []
    for unit in sorted(units.glob("*.service")):
        x = _read(unit) or ""
        ex = re.search(r"^ExecStart=[-@!+:]*(\S+)(.*)$", x, re.M)
        wd = re.search(r"^WorkingDirectory=-?(\S+)", x, re.M)
        rest = [expand(a, str(home)) for a in ex.group(2).split()] if ex else []
        jobs.append(
            {
                "src": "systemd",
                "name": unit.name,
                "active": unit.name in wanted or unit.name.replace(".service", ".timer") in wanted,
                "program": ex.group(1) if ex else None,
                "script": next((a for a in rest if a.startswith("/") and SCRIPT_EXT.search(a)), None),
                "workdir": wd.group(1) if wd else None,
            }
        )
    return jobs


def crontab_jobs(home: Path, fixture: bool) -> list[dict]:
    if fixture:
        text = _read(home / ".crontab") or ""
    else:
        try:
            done = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            return []
        text = done.stdout if done.returncode == 0 else ""
    jobs = []
    for line in text.splitlines():
        t = line.strip()
        if not t or t.startswith("#") or re.match(r"^\w+=", t):
            continue
        cmd = " ".join(t.split()[1:] if t.startswith("@") else t.split()[5:])
        jobs.append({"src": "crontab", "name": cmd[:60], "active": True, "text": cmd})
    return jobs


def targets_in(text: str, home: str) -> list[str]:
    out: dict[str, None] = {}
    for rx in TARGET_RES:
        for m in rx.finditer(text):
            p = expand(m.group(1), home)
            if p.startswith("/") and not re.search(r"[$*`]", p):
                out[p] = None
    return list(out)


def job_faults(job: dict, home: str, platform: str) -> tuple[list[str], int]:
    """Every fault on one job, and how many paths it resolved — the count is printed, never assumed."""
    bad, checked = [], 0

    def check(path: str, why: str) -> str | None:
        nonlocal checked
        checked += 1
        if platform == "linux" and path.startswith(MAC_HOME):
            return f"{why} {path} is a macOS path on linux"
        return None if os.path.exists(path) else f"{why} {path} missing"

    program = expand(job.get("program") or "", home)  # `ExecStart=%h/x` is a path; unexpanded it was skipped
    if program.startswith("/"):
        bad.append(check(program, "program"))
    if job.get("workdir"):
        bad.append(check(expand(job["workdir"], home), "workdir"))
    body = job.get("text") or ""
    if job.get("script"):
        fault = check(job["script"], "script")
        bad.append(fault)
        body += "\n" + ("" if fault else _read(Path(job["script"])) or "")
    bad += [check(t, "target") for t in targets_in(body, home)]
    if GREEN_ON_DEAD.search(body):
        bad.append("`cd ... || ... exit 0` reports a dead target as success")
    return [b for b in bad if b], checked


def sweep(home: str, platform: str, hermes: str | None = None, fixture: bool = False) -> dict:
    root = Path(home)
    jobs = hermes_jobs(Path(hermes) if hermes else root / ".hermes")
    jobs += launchd_jobs(root) if platform == "darwin" else []
    jobs += systemd_jobs(root) if platform == "linux" else []
    jobs += crontab_jobs(root, fixture)
    faults, warns, checked = [], [], 0
    for job in jobs:
        bad, n = job_faults(job, home, platform)
        checked += n
        (faults if job["active"] else warns).extend(f"{job['src']}:{job['name']}: {b}" for b in bad)
    counts = {s: sum(j["src"] == s for j in jobs) for s in ("hermes", "launchd", "systemd", "crontab")}
    return {
        "jobs": len(jobs),
        "active": sum(j["active"] for j in jobs),
        "counts": counts,
        "checked": checked,
        "faults": faults,
        "warns": warns,
        "platform": platform,
    }


def main(argv: list[str]) -> int:
    root = argv[argv.index("--root") + 1] if "--root" in argv else None
    platform = argv[argv.index("--platform") + 1] if "--platform" in argv else sys.platform
    home = root or str(Path.home())
    hermes = str(Path(home) / ".hermes") if root else os.environ.get("HERMES_HOME")
    r = sweep(home, platform, hermes, fixture=bool(root))
    for f in r["faults"]:
        print(f"FAIL {f}")
    for w in r["warns"]:
        print(f"WARN (paused) {w}")
    c = r["counts"]
    print(
        f"schedtargets: {r['jobs']} jobs ({r['active']} active; hermes {c['hermes']}, launchd {c['launchd']}, "
        f"systemd {c['systemd']}, crontab {c['crontab']}), {r['checked']} targets checked, "
        f"{len(r['faults'])} fault(s), {len(r['warns'])} paused warn(s) [{platform}]"
    )
    print(f"blind spot: {BLIND_SPOT}")
    if not r["jobs"]:
        print("FAIL empty roster — no scheduler source found; a pass over nothing is not a pass")
        return 1
    return 1 if r["faults"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
