#!/usr/bin/env python3
"""doctor — can THIS machine run each instrument, and what does it cost when one cannot?

WHY THIS EXISTS (v1.3.1). Every other instrument here answers a question about the repository.
None answered the question asked first by anyone — human, agent or CI runner — arriving in a fresh
checkout: *what can I actually run?* Without it the failure mode is the worst kind: a missing
optional dependency makes an instrument do nothing, and doing nothing looks exactly like finding
nothing. `ghaudit` with no `gh` on PATH refuses loudly by design; the point of this file is that
you learn it in one call, before you plan around the answer.

REQUIRED versus OPTIONAL is a real distinction and it is printed, not implied:
  REQUIRED  the contract cannot run without it — the exit code is non-zero.
  OPTIONAL  something narrower cannot run. The exit code stays 0 and the LINE NAMES what is lost,
            because a warning that does not say what it costs gets read as noise.

  python scripts/doctor.py           # a table, and an exit code
  python scripts/doctor.py --json    # the same as a record

BLIND SPOT, AND ITS OWNER: this proves a tool RESOLVES and answers a version flag. It does not
prove the version is new enough for a given pack, and it says nothing about the 29 language
toolchains — that is `packprobe.py --mode smoke`, which runs them pack by pack.
"""
from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from atlascore import strict_yaml

ROOT = Path(__file__).resolve().parents[1]
PROBE_TIMEOUT = 10


def _run(argv: list[str]) -> tuple[bool, str]:
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=PROBE_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, exc.__class__.__name__
    said = (done.stdout or done.stderr).strip().splitlines()
    return done.returncode == 0, (said[0][:58] if said else "exited 0 and said nothing")


def _required_python() -> str:
    match = re.search(r'requires-python\s*=\s*">=([\d.]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return match.group(1) if match else "3.11"


def findings() -> list[dict]:
    """One row per capability: name, whether it is required, what was measured, what is lost."""
    rows: list[dict] = []

    want = _required_python()
    have = platform.python_version()
    rows.append({
        "capability": "python", "required": True,
        "ok": tuple(int(p) for p in have.split(".")[:2]) >= tuple(int(p) for p in want.split(".")[:2]),
        "measured": f"{have} (pyproject requires >={want})",
        "costs_if_absent": "nothing here runs",
    })

    try:
        import yaml  # noqa: F401
        yaml_ok, yaml_said = True, f"PyYAML {getattr(yaml, '__version__', 'unknown')}"
    except ImportError:
        yaml_ok, yaml_said = False, "not importable — pip install -r scripts/requirements.txt"
    rows.append({"capability": "pyyaml", "required": True, "ok": yaml_ok, "measured": yaml_said,
                 "costs_if_absent": "atlas.py, packprobe and every manifest reader refuse"})

    git_ok, git_said = _run(["git", "--version"]) if shutil.which("git") else (False, "not on PATH")
    rows.append({"capability": "git", "required": True, "ok": git_ok, "measured": git_said,
                 "costs_if_absent": "the contract falls back to walking the tree, so ignored files enter its roster"})

    gh_ok, gh_said = _run(["gh", "--version"]) if shutil.which("gh") else (False, "not on PATH")
    if gh_ok:
        authed, _ = _run(["gh", "auth", "status"])
        gh_said += " (authenticated)" if authed else " (NOT authenticated — gh auth login)"
        gh_ok = authed
    rows.append({"capability": "gh", "required": False, "ok": gh_ok, "measured": gh_said,
                 "costs_if_absent": "ghaudit.py cannot compare the live GitHub controls; it refuses rather than reporting"})

    ruff_ok, ruff_said = _run(["ruff", "--version"]) if shutil.which("ruff") else (False, "not on PATH")
    rows.append({"capability": "ruff", "required": False, "ok": ruff_ok, "measured": ruff_said,
                 "costs_if_absent": "the lint gate cannot run locally; CI still runs it"})

    try:
        import jsonschema  # noqa: F401
        js_ok, js_said = True, f"jsonschema {getattr(jsonschema, '__version__', 'unknown')}"
    except ImportError:
        js_ok, js_said = False, "not importable"
    rows.append({"capability": "jsonschema", "required": False, "ok": js_ok, "measured": js_said,
                 "costs_if_absent": "atlas_test.py skips the independent cross-check of this repo's own validator, "
                                    "by name, and says so"})

    # The instrument roster is READ from atlas.yaml, never listed here: a second copy would narrow
    # the moment an instrument is added beside it.
    if yaml_ok:
        declared = (strict_yaml((ROOT / "atlas.yaml").read_text(encoding="utf-8"), "atlas.yaml") or {}).get("instruments") or {}
        missing = [name for name, spec in declared.items() if not (ROOT / str(spec.get("script"))).exists()]
        rows.append({"capability": "instrument files", "required": True, "ok": not missing,
                     "measured": f"{len(declared) - len(missing)}/{len(declared)} present",
                     "costs_if_absent": f"declared but absent: {', '.join(missing)}" if missing else "—"})
    return rows


def main(argv: list[str]) -> int:
    rows = findings()
    broken = [r for r in rows if r["required"] and not r["ok"]]
    degraded = [r for r in rows if not r["required"] and not r["ok"]]
    if "--json" in argv:
        print(json.dumps({"schema": 1, "command": "doctor", "platform": platform.platform(),
                          "rows": rows, "required_missing": len(broken), "optional_missing": len(degraded)}, indent=2))
        return 1 if broken else 0

    print(f"doctor — {platform.platform()}\n")
    width = max(len(r["capability"]) for r in rows)
    for row in rows:
        mark = "ok  " if row["ok"] else ("FAIL" if row["required"] else "note")
        print(f"{mark} {row['capability'].ljust(width)}  {row['measured']}")
        if not row["ok"]:
            print(f"     {' ' * width}  costs: {row['costs_if_absent']}")
    print(f"\n{len(rows) - len(broken) - len(degraded)}/{len(rows)} capabilities present, "
          f"{len(broken)} required missing, {len(degraded)} optional missing")
    if not broken:
        print("The contract can run here: `python scripts/atlas.py check`.")
    print("SCOPE: this proves a tool resolves and answers a version flag. Whether the 29 language")
    print("       toolchains exist is `python scripts/packprobe.py --mode smoke`.")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
