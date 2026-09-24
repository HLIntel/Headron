#!/usr/bin/env python3
"""exrun — run every example this machine can, and say why it skipped the rest.

WHY THIS EXISTS (v2.2.0). The examples were documentation that happened to be code: one imported a
package that was never installed, so it could not run at all, and nothing noticed. An example
nobody executes is a skeleton — the exact thing this repository refuses in language packs, sitting
in the directory a reader copies from.

It holds NO roster of its own. Every file under examples/ is routed with this repository's own
router, and the recipe is looked up by route in atlas.yaml/example_runners. A file that does not
route, or whose route declares no runner, is REPORTED as unexercised rather than quietly passed
over: those two look identical in a summary and mean opposite things.

  python scripts/exrun.py            # PASS / FAIL / SKIP with the reason, exit 1 on any FAIL
  python scripts/exrun.py --json     # the same as a record

SCOPE: an example that PASSES proves its own assertions held on this machine with this toolchain.
It does not prove the pack's other declarations, which is `packprobe.py --mode smoke`, and it says
nothing about a toolchain that is absent — ABSENT IS NOT WRONG.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from atlascore import atlas, rel, route_for  # noqa: E402

STEP_TIMEOUT = 120
SKIP_SUFFIXES = {".json", ".md", ".txt", ".lock"}


def examples() -> list[Path]:
    return sorted(p for p in (ROOT / "examples").rglob("*")
                  if p.is_file() and p.suffix.lower() not in SKIP_SUFFIXES)


def run_one(path: Path, steps: list[list[str]]) -> tuple[str, str]:
    """(verdict, detail) for one example: PASS, FAIL or SKIP with the reason."""
    with tempfile.TemporaryDirectory() as work:
        out = str(Path(work) / "example.bin")
        for step in steps:
            argv = [word.replace("{file}", str(path)).replace("{out}", out) for word in step]
            if not shutil.which(argv[0]) and not argv[0].startswith("/"):
                return "SKIP", f"{argv[0]} is not on PATH — absent is not wrong"
            try:
                done = subprocess.run(argv, capture_output=True, text=True,
                                      timeout=STEP_TIMEOUT, cwd=ROOT, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                return "FAIL", f"{exc.__class__.__name__} running {' '.join(argv[:2])}"
            if done.returncode != 0:
                tail = (done.stderr or done.stdout).strip().splitlines()
                return "FAIL", f"exit {done.returncode} from {argv[0]}: {tail[-1][:120] if tail else 'no output'}"
        said = (done.stdout or "").strip().splitlines()
        return "PASS", (said[-1][:96] if said else "exited 0 and printed nothing")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="exrun.py", description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="emit the run as a record")
    args = parser.parse_args(argv)

    runners = atlas().get("example_runners") or {}
    rows = []
    for path in examples():
        route = route_for(str(path))
        if route is None:
            rows.append({"file": rel(path), "route": None, "verdict": "SKIP",
                         "detail": "not a routed artifact, so no toolchain claims it"})
            continue
        recipe = runners.get(route)
        if not recipe:
            rows.append({"file": rel(path), "route": route, "verdict": "UNEXERCISED",
                         "detail": f"atlas.yaml/example_runners declares no recipe for {route}"})
            continue
        verdict, detail = run_one(path, recipe["steps"])
        rows.append({"file": rel(path), "route": route, "verdict": verdict, "detail": detail})

    counts = {v: sum(1 for r in rows if r["verdict"] == v) for v in ("PASS", "FAIL", "SKIP", "UNEXERCISED")}
    if args.json:
        print(json.dumps({"schema": 1, "command": "exrun", "rows": rows, "counts": counts}, indent=2))
        return 1 if counts["FAIL"] else 0

    width = max(len(r["file"]) for r in rows)
    for row in rows:
        print(f"{row['verdict']:<12}{row['file'].ljust(width)}  {row['detail']}")
    print(f"\n{counts['PASS']} passed, {counts['FAIL']} failed, {counts['SKIP']} skipped, "
          f"{counts['UNEXERCISED']} routed with no runner declared, {len(rows)} files in examples/")
    print("SCOPE: a PASS proves this example's own assertions held here. Toolchain coverage per pack")
    print("       is `packprobe.py --mode smoke`; an absent toolchain is a fact about the machine.")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
