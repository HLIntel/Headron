#!/usr/bin/env python3
"""What ACTUALLY passed: run the declared done set, one verdict per gate, read off the exit code.

WHY (3.9.0). "Done" was seven commands typed into a document; an agent ran some, read their output and
reported green. Three ways that lies, each now a row state instead of a sentence:
  FAIL      the gate exited non-zero                      -> run exits 1
  NOT RUN   the gate was not run (THEA_READ_ONLY on a      -> run exits 2: incomplete is not done
            mutating gate, or its program is missing)
  PASS      exit 0 — and the gate's own SCOPE/COVERAGE line is printed beside it, because a pass
            over 17 of 36 packs and a pass over 36 print the same exit code
  REUSED    a PASS recorded for this byte-identical tree, argv and environment -> done, not re-run;
            --fresh re-measures. Per gate (3.48.0): a re-run after one red gate pays for that gate only
The verdict is the exit code, never the text; the coverage line is shown, never parsed into a verdict.

  python scripts/verify.py [--json]
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

from atlascore import ROOT, atlas, changed_paths, ls_files

TIMEOUT = 900
SELF_REPORT = ("COVERAGE", "SCOPE", "tests:", "caps:", "install footprint", "passed,", "Thea Software contract")
EVIDENCE_SCHEMA = 3


def input_digest() -> str:
    """Digest every versioned or untracked input, never a timestamp or a prior verdict."""
    digest = hashlib.sha256()
    names = ls_files(ROOT, flags=("--cached", "--others", "--exclude-standard"))
    for raw in sorted(name.encode("utf-8", "surrogateescape") for name in names):  # byte order: the digest is unchanged
        path = ROOT / raw.decode("utf-8", errors="surrogateescape")
        digest.update(raw + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def gate_key(gate: dict) -> str:
    """A gate's identity for reuse: id, argv, mutates, and the environment its program resolves in.

    WHY (3.47.0). Byte-identical inputs on another interpreter or with an upgraded tool are a new
    measurement, so evidence from one environment is never REUSED in another; it is re-run instead."""
    seen = {"id": gate.get("id"), "argv": gate.get("argv"), "mutates": bool(gate.get("mutates")),
            "python": sys.version, "platform": sys.platform, "machine": os.uname().machine if hasattr(os, "uname") else "",
            "program": _program_identity(str((gate.get("argv") or [""])[0]))}
    return hashlib.sha256(json.dumps(seen, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _program_identity(name: str) -> str:
    """A program's resolved path and size+mtime: an upgrade in place changes it without a version call."""
    found = shutil.which(name)
    if not found:
        return "missing"
    stat = os.stat(found)
    return f"{os.path.realpath(found)}:{stat.st_size}:{stat.st_mtime_ns}"


def _evidence_path():
    from safeedit import _git_path  # noqa: PLC0415
    return _git_path("thea-fast-evidence.json")


def reuse_evidence(gates: list[dict], tree: str) -> dict[str, dict]:
    """This tree's recorded PASS rows, by gate_key; a gate whose key is absent re-runs."""
    try:
        saved = json.loads(_evidence_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = saved.get("rows") if saved.get("schema") == EVIDENCE_SCHEMA and saved.get("tree") == tree else None
    keys = {gate_key(g): g for g in gates}
    return {k: r for k, r in rows.items() if k in keys and r.get("verdict") == "PASS"
            and r.get("argv") == keys[k].get("argv")} if isinstance(rows, dict) else {}


def write_evidence(passed: dict[str, dict], tree: str) -> None:
    """ONE tree's PASS rows, so the store is bounded by the done set, never by runs; a FAIL never becomes proof."""
    _evidence_path().write_text(json.dumps({"schema": EVIDENCE_SCHEMA, "tree": tree, "rows": passed}, indent=1) + "\n",
                                encoding="utf-8")


def run_gate(gate: dict) -> dict:
    argv = [sys.executable if gate["argv"][0] == "python" else gate["argv"][0], *gate["argv"][1:]]
    row = {"id": gate["id"], "argv": gate["argv"], "mutates": bool(gate.get("mutates")),
           # CARRIED ONTO THE ROW so --json records it too: a machine-dependent PASS is a LOCAL pass, and
           # a consumer reading the record must be able to tell those apart without re-reading atlas.yaml.
           "machine_dependent": bool(gate.get("machine_dependent"))}
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
    if done.returncode == 75:  # atlas_test.BUSY: the machine holds another suite — not run, holder named
        return row | {"verdict": "NOT RUN", "why": (lines[-1] if lines else "busy")[:200]}
    said = [ln.strip() for ln in lines if any(k in ln for k in SELF_REPORT)]
    # THE CAUSE, NOT THE FIRST ALARMING LINE (3.9.0): a suite that crashed printed an expected
    # "- WRONG ROUTE" from a passing case first, and verify blamed that. A traceback's last line is the cause.
    crashed = any(ln.startswith("Traceback") for ln in lines)
    # A suite's own verdict comes LAST, as a FAIL line or a guard's verdict word (DUPLICATE, CASE COUNT
    # MOVED); a "- " line is a check's finding list. SECOND SIGHTING: preferring any FAIL line over a later
    # shouted one blamed a passing case's expected "FAIL empty roster" for a suite that died on its count.
    alarms = [ln for ln in lines if re.match(r"[A-Z]{4,}\b", ln) and not ln.startswith(("SCOPE", "COVERAGE"))]
    first_error = lines[-1] if crashed and lines else alarms[-1] if alarms else next(
        (ln for ln in lines if ln.startswith("- ")), lines[-1] if lines else "")
    return row | {"verdict": "PASS" if done.returncode == 0 else "FAIL", "exit": done.returncode,
                  "seconds": round(time.monotonic() - start, 1), "self_report": said[:3],
                  "output_bytes": len(done.stdout) + len(done.stderr), "calls": 1,
                  "why": "" if done.returncode == 0 else (first_error[:160] or f"exited {done.returncode}")}


def _paint(verdict: str) -> str:
    """Colour only where a person reads it: a terminal, and never when NO_COLOR is set (no-color.org)."""
    text = f"{verdict:<8}"
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\033[{ {'PASS': '32', 'FAIL': '31', 'NOT RUN': '33'}.get(verdict, '0') }m{text}\033[0m"


def verdict_code(rows: list[dict]) -> int:
    """1 on any FAIL; 2 when nothing failed but something did not run; 0 only when every gate PASSED."""
    verdicts = {r["verdict"] for r in rows}
    return 1 if "FAIL" in verdicts else 2 if verdicts - {"PASS", "REUSED"} or not rows else 0


def changed_gates() -> list[dict]:
    """The fast loop (3.20.0): each CHANGED file's own gates, plus the contract — seconds, not minutes, so it
    runs after every edit instead of once at the end, when a wrong turn is already several edits deep."""
    from agentpolicy import required_gates  # noqa: PLC0415
    from atlas import gate_record  # noqa: PLC0415
    files = [f for f in changed_paths(ROOT) if (ROOT / f).is_file()]
    policy = atlas().get("verification_policy") or {}
    rows = [{"id": "contract", "argv": ["python", "scripts/atlas.py", "check"], "mutates": False}]
    lint = next((g["argv"] for g in policy.get("done_set") or [] if g["id"] == "lint"), None)
    py = [f for f in files if f.endswith(".py")]
    if lint and py:  # the done set's own linter, narrowed from the tree to the changed files
        # --force-exclude: named files would otherwise bypass the configured excludes the tree-wide run honours
        rows.append({"id": "lint:changed", "argv": [*lint[:-1], "--force-exclude", *py], "mutates": False})
    for path in files:
        for gate in (g for g in required_gates({"change_class": "source_change"}) if g in (policy.get("fast_loop") or [])):
            argv = gate_record(path, gate).get("argv") or []
            if argv and argv[-1] == path:  # per-file only: a whole-suite runner belongs to the full verify
                rows.append({"id": f"{gate}:{path}", "argv": argv, "mutates": False})
    return rows


def record(rows: list[dict], tally: dict, code: int) -> dict:
    """The `--json` record, ONE PRODUCER: frozen as tools/atlas-output.schema.json $defs/verify, and atlas_test
    asserts real rows against it without running verify inside the suite verify itself runs."""
    return {"schema": 1, "command": "verify", "atlas_version": str(atlas().get("version")),
            "rows": rows, "tally": tally, "exit": code}


def unpushed_row() -> dict:
    """THE SESSION-END GATE HOLDS THE LANE BOUND (3.47.0). branchstate printed every breach and exited 1,
    and nothing that ends a session read that exit: fifteen lanes held unpushed work, several past forty
    hours against a two-hour bound. `verify` IS the done hook, so a breach is a FAIL row here, never a print.
    Machine dependent by nature: it reads this clone's refs, which no other machine has."""
    from branchstate import unpushed_errors  # noqa: PLC0415
    problems = unpushed_errors()
    return {"id": "unpushed_bound", "argv": ["python", "scripts/branchstate.py"], "mutates": False,
            "machine_dependent": True, "verdict": "FAIL" if problems else "PASS", "calls": 1,
            "why": f"{len(problems)} breach(es), first: {problems[0]}"[:160] if problems else ""}


LESSONS_CAP = 200  # distinct causes kept; the store grows by cause, never by run — bounded, per unbounded-growth


def learn(rows: list[dict]) -> list[str]:
    """Count each failing cause across runs; return the causes seen twice or more — the second time is a rule."""
    from safeedit import _git_path  # noqa: PLC0415
    store = _git_path("thea-lessons.json")
    lessons = json.loads(store.read_text(encoding="utf-8")) if store.is_file() else {}
    # ONE COUNT PER CAUSE PER RUN: twelve files failing one gate for one reason is one lesson, not twelve.
    seen = {f"{r['id'].split(':')[0]} :: {r.get('why', '')[:90]}" for r in rows if r["verdict"] == "FAIL"}
    for key in seen:
        lessons[key] = lessons.get(key, 0) + 1
    lessons = dict(sorted(lessons.items(), key=lambda kv: -kv[1])[:LESSONS_CAP])
    store.write_text(json.dumps(lessons, indent=1), encoding="utf-8")
    return [k for k in seen if lessons[k] >= 2]


def main(argv: list[str]) -> int:
    changed = "--changed" in argv
    gates = changed_gates() if changed else (atlas().get("verification_policy") or {}).get("done_set") or []
    if not gates:
        print("verify: verification_policy/done_set declares no gate — an empty done set passes nothing")
        return 1
    tree = input_digest()
    saved = {} if "--fresh" in argv else reuse_evidence(gates, tree)
    keys = [gate_key(g) for g in gates]
    rows = [saved[k] | {"verdict": "REUSED", "why": "this tree, argv and environment PASSED before; --fresh re-measures"}
            if k in saved else run_gate(g) for k, g in zip(keys, gates, strict=True)]
    passed = saved | {k: r for k, r in zip(keys, rows, strict=True) if r["verdict"] == "PASS"}
    if len(passed) > len(saved) and input_digest() == tree:  # a tree edited mid-run proves nothing about either
        write_evidence(passed, tree)
    measured = any(r["verdict"] != "REUSED" for r in rows)
    spared = round(sum(r.get("seconds") or 0 for r in rows if r["verdict"] == "REUSED"), 1)
    if changed:  # a fact read from the last suite's ledger, never run: the fast loop stays seconds
        import edges  # noqa: PLC0415
        rows.append(edges.changed_row([f for f in changed_paths(ROOT) if (ROOT / f).is_file()]))
    rows += [] if changed else [unpushed_row()]
    recurring = learn(rows)
    tally = {v: sum(r["verdict"] == v for r in rows) for v in ("PASS", "REUSED", "FAIL", "NOT RUN")}
    local_only = sum(1 for r in rows if r.get("machine_dependent") and r["verdict"] == "PASS")
    code = verdict_code(rows)
    # THE LAST VERDICT OUTLIVES THE PROCESS (3.19.0): `thea resume` reads it, so an agent picking up a lane
    # knows which gate failed without re-running everything. A runtime store inside .git, never tracked.
    from safeedit import _git_path  # noqa: PLC0415
    _git_path("thea-last-verify.json").write_text(json.dumps({"exit": code, "rows": rows, "measured": measured}), encoding="utf-8")
    if "--json" in argv:
        print(json.dumps(record(rows, tally, code), indent=2))
        return code
    # ONE CAUSE, ONE LINE (3.13.0): a reviewer read one drift three times, once per gate that tripped on it.
    first_seen: dict[str, str] = {}
    for r in rows:
        why = r.get("why") or ""
        if why and why in first_seen:
            why = f"same {'evidence' if r['verdict'] == 'REUSED' else 'cause'} as {first_seen[why]}"
        elif why:
            first_seen[why] = r["id"]
        # A MACHINE-DEPENDENT PASS IS A LOCAL PASS (3.33.0). Sighted at 3.32.0: own_enforcement was green
        # on the author's Mac and red in CI on the same tree, because a toolchain was simply absent here.
        # The label is printed on the row, never only in a footnote nobody reads.
        local = "  [this machine only]" if r.get("machine_dependent") and r["verdict"] == "PASS" else ""
        print(f"{_paint(r['verdict'])}{r['id']:<16}{str(r.get('seconds', '-')) + 's':>7}  {why}{local}")
        for said in r.get("self_report") or []:
            print(f"{'':<24}{said[:110]}")
    for lesson in recurring[:3]:
        print(f"RECURRING  {lesson} — seen before: write the rule and its guard (`thea failures` shows the shape)")
    print(f"verify: {tally['PASS']} PASS, {tally['REUSED']} REUSED, {tally['FAIL']} FAIL, {tally['NOT RUN']} NOT RUN of {len(rows)} declared gates"
          f"{f'; {local_only} of those passes are this machine only' if local_only else ''}"
          f"{f'; reuse spared {spared}s' if spared else ''}"
          + ("" if code == 0 else " — NOT done" + (" (incomplete: a NOT RUN is never a pass)" if code == 2 else "")))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
