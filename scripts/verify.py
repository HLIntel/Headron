#!/usr/bin/env python3
"""What ACTUALLY passed: run the declared done set, one verdict per gate, read off the exit code.

WHY (3.9.0). "Done" was seven commands typed into a document; an agent ran some, read their output and
reported green. Three ways that lies, each now a row state instead of a sentence:
  FAIL      the gate exited non-zero                      -> run exits 1
  NOT RUN   the gate was not run (THEA_READ_ONLY on a      -> run exits 2: incomplete is not done
            mutating gate, or its program is missing)
  PASS      exit 0 — and the gate's own SCOPE/COVERAGE line is printed beside it, because a pass
            over 17 of 36 packs and a pass over 36 print the same exit code
The verdict is the exit code, never the text; the coverage line is shown, never parsed into a verdict.

  python scripts/verify.py [--json]
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time

from atlascore import ROOT, atlas

TIMEOUT = 900
SELF_REPORT = ("COVERAGE", "SCOPE", "tests:", "caps:", "install footprint", "passed,", "Thea Software contract")


def run_gate(gate: dict) -> dict:
    argv = [sys.executable if gate["argv"][0] == "python" else gate["argv"][0], *gate["argv"][1:]]
    row = {"id": gate["id"], "argv": gate["argv"], "mutates": bool(gate.get("mutates"))}
    if row["mutates"] and os.environ.get("THEA_READ_ONLY"):
        return row | {"verdict": "NOT RUN", "why": "mutating gate under THEA_READ_ONLY"}
    if not shutil.which(argv[0]):
        return row | {"verdict": "NOT RUN", "why": f"{argv[0]} is not installed here"}
    start = time.monotonic()
    try:
        done = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT, check=False)  # noqa: S603
    except subprocess.TimeoutExpired:
        return row | {"verdict": "FAIL", "why": f"timed out after {TIMEOUT}s", "seconds": TIMEOUT}
    lines = [ln for ln in (done.stdout + done.stderr).splitlines() if ln.strip()]
    said = [ln.strip() for ln in lines if any(k in ln for k in SELF_REPORT)]
    # THE CAUSE, NOT THE FIRST ALARMING LINE (3.9.0): a suite that crashed printed an expected
    # "- WRONG ROUTE" from a passing case first, and verify blamed that. A traceback's last line is the cause.
    crashed = any(ln.startswith("Traceback") for ln in lines)
    # A suite's own verdict line starts FAIL and comes LAST; a "- " line is a check's finding list.
    fails = [ln for ln in lines if ln.startswith("FAIL")]
    # A guard's own verdict word (DUPLICATE, MISSED, MISFIRE) is the cause when no FAIL line was printed.
    shouted = [ln for ln in lines if re.match(r"[A-Z]{4,}\b", ln) and not ln.startswith(("SCOPE", "COVERAGE"))]
    first_error = lines[-1] if crashed and lines else fails[-1] if fails else shouted[-1] if shouted else next(
        (ln for ln in lines if ln.startswith("- ")), lines[-1] if lines else "")
    return row | {"verdict": "PASS" if done.returncode == 0 else "FAIL", "exit": done.returncode,
                  "seconds": round(time.monotonic() - start, 1), "self_report": said[:3],
                  "why": "" if done.returncode == 0 else (first_error[:160] or f"exited {done.returncode}")}


def verdict_code(rows: list[dict]) -> int:
    """1 on any FAIL; 2 when nothing failed but something did not run; 0 only when every gate PASSED."""
    verdicts = {r["verdict"] for r in rows}
    return 1 if "FAIL" in verdicts else 2 if "NOT RUN" in verdicts or not rows else 0


def main(argv: list[str]) -> int:
    gates = (atlas().get("verification_policy") or {}).get("done_set") or []
    if not gates:
        print("verify: verification_policy/done_set declares no gate — an empty done set passes nothing")
        return 1
    rows = [run_gate(g) for g in gates]
    tally = {v: sum(r["verdict"] == v for r in rows) for v in ("PASS", "FAIL", "NOT RUN")}
    code = verdict_code(rows)
    if "--json" in argv:
        print(json.dumps({"schema": 1, "command": "verify", "atlas_version": str(atlas().get("version")),
                          "rows": rows, "tally": tally, "exit": code}, indent=2))
        return code
    # ONE CAUSE, ONE LINE (3.13.0): a reviewer read one drift three times, once per gate that tripped on it.
    first_seen: dict[str, str] = {}
    for r in rows:
        why = r.get("why") or ""
        if why and why in first_seen:
            why = f"same cause as {first_seen[why]}"
        elif why:
            first_seen[why] = r["id"]
        print(f"{r['verdict']:<8}{r['id']:<16}{str(r.get('seconds', '-')) + 's':>7}  {why}")
        for said in r.get("self_report") or []:
            print(f"{'':<24}{said[:110]}")
    print(f"verify: {tally['PASS']} PASS, {tally['FAIL']} FAIL, {tally['NOT RUN']} NOT RUN of {len(rows)} declared gates"
          + ("" if code == 0 else " — NOT done" + (" (incomplete: a NOT RUN is never a pass)" if code == 2 else "")))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
