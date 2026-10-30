#!/usr/bin/env python3
"""What ACTUALLY passed: run the declared done set, one verdict per gate, read off the exit code.

WHY (3.9.0). "Done" was seven commands typed into a document; an agent ran some, read their output and
reported green. Three ways that lies, each now a row state instead of a sentence:
  FAIL      the gate exited non-zero                      -> run exits 1
  NOT RUN   the gate was not run (HEADRON_READ_ONLY on a      -> run exits 2: incomplete is not done
            mutating gate, or its program is missing)
  PASS      exit 0 — and the gate's own SCOPE/COVERAGE line is printed beside it, because a pass
            over 17 of 36 packs and a pass over 36 print the same exit code
  REUSED    a PASS recorded for this byte-identical tree, argv and environment -> done, not re-run;
            --fresh re-measures. Per gate (3.48.0): a re-run after one red gate pays for that gate only
The verdict is the exit code, never the text; the coverage line is shown, never parsed into a verdict.

SHARED WALL (3.59.x). Fifteen of the sixteen gates read the tree and write nothing; run one after the
other, the wall was the SUM. The read-only gates run concurrently (default up to 8 workers, `--jobs N` to
change), while a gate that plants and restores tracked files — planted_suite — runs alone AFTER the
pool exits, so no reader ever judges a planted tree. Each concurrent gate gets its own HEADRON_HOME:
two suites appending one hash-chained ledger would interleave their links.

  python scripts/verify.py [--json] [--changed] [--fresh] [--jobs N] [--receipt PATH]

RECEIPT (receipt v1). --receipt PATH writes this run as a receipt (scripts/receipt.py, tools/receipt.schema.json):
the same rows, one mapping to a verdict, plus the policy pinned to the base commit. The PR head's policy must
equal the base's or the receipt FAILs. A receipt needs the whole done set, so --changed is refused with it.
"""

from __future__ import annotations

import atexit
import fnmatch
import hashlib
import json
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import receipt
import resilience
from atlascore import ROOT, atlas, changed_paths, diff_names, ls_files, strict_yaml

TIMEOUT = 900
# A cap leaves capacity for the gates themselves: more Python launchers than this only contend.
DEFAULT_JOBS = min(multiprocessing.cpu_count() or 4, 8)
SELF_REPORT = ("COVERAGE", "SCOPE", "tests:", "caps:", "install footprint", "passed,", "Headron Software contract")
EVIDENCE_SCHEMA = 4  # 4: every row carries its own proof scope; a schema-3 store re-measures once
# A GATE'S OUTPUT IS READ BOUNDED (3.54.x): branchstate's runner learned this at 45 GB and a killed landing;
# this one still held every byte in a pipe. The head carries the self-report, the tail carries the verdict.
HEAD_BYTES, TAIL_BYTES = 64 << 10, 256 << 10


def undecided_exit(tool: str, code: int) -> str:
    """The declared reason this exit code means the tool DECIDED NOTHING, or "" when it decided."""
    spec = (atlas().get("enforcement") or {}).get("undecided_exits") or {}
    codes = spec.get(tool.rsplit("/", 1)[-1]) or []
    reason = " ".join(str(spec.get("reason") or "could not decide").split()).split(". ")[0]  # the rule, not its history
    return reason if code in [int(c) for c in codes] else ""


def _tool(argv: list[str]) -> str:
    """The program a gate runs: `python -m pytest` is pytest, `pytest` is pytest."""
    return argv[2] if len(argv) > 2 and argv[0] == "python" and argv[1] == "-m" else argv[0]


def _bounded_read(stream) -> tuple[str, int]:
    """One spooled stream as (head and tail, bytes written)."""
    size = stream.seek(0, 2)
    stream.seek(0)
    if size <= HEAD_BYTES + TAIL_BYTES:
        return stream.read().decode(errors="replace"), size
    head = stream.read(HEAD_BYTES).decode(errors="replace")
    stream.seek(size - TAIL_BYTES)
    cut = f"\n[verify: {size - HEAD_BYTES - TAIL_BYTES} bytes of output not read]\n"
    return head + cut + stream.read().decode(errors="replace"), size


def _bounded_run(argv: list[str], cwd: Path, env: dict | None = None) -> tuple[int, str, int]:
    """Run one gate with its output in files: (exit code, stdout then stderr bounded, bytes written).

    TWO FILES, NOT ONE: merged, a buffered stdout flushed at exit AFTER the traceback, and the cause stopped
    being the last line. stdout then stderr keeps the order the verdict reader was proven on."""
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        done = subprocess.run(  # noqa: S603
            argv, cwd=cwd, stdout=out, stderr=err, timeout=TIMEOUT, check=False, env=env or _gate_env()
        )
        (said, said_bytes), (cried, cried_bytes) = _bounded_read(out), _bounded_read(err)
        return done.returncode, said + cried, said_bytes + cried_bytes


def _input_names(root: Path) -> list[bytes]:
    """Every versioned or untracked path, in byte order, so a digest is the same on every machine."""
    names = ls_files(root, flags=("--cached", "--others", "--exclude-standard"))
    return sorted(name.encode("utf-8", "surrogateescape") for name in names)


def _digest(root: Path, names: list[bytes]) -> str:
    digest = hashlib.sha256()
    for raw in names:
        path = root / raw.decode("utf-8", errors="surrogateescape")
        digest.update(raw + b"\0")
        digest.update(path.read_bytes() if path.is_file() else b"\0deleted")  # deleted, not yet staged: still a state
        digest.update(b"\0")
    return digest.hexdigest()


def input_digest(root: Path = ROOT) -> str:
    """Digest every versioned or untracked input, never a timestamp or a prior verdict."""
    return _digest(root, _input_names(root))


def gate_inputs(gate: dict) -> list[str] | None:
    """The paths a gate's verdict depends on, or None. A bad declaration is None: it falls back to the whole tree.

    A pattern matches with fnmatch, so `*.py` reaches into every directory. A gate that names no inputs keeps
    the whole-tree proof; only a declared list may skip a changed file, and only the one it names.
    """
    raw = gate.get("inputs")
    if isinstance(raw, list) and raw and all(isinstance(p, str) and p for p in raw):
        return raw
    return None


def proof_scope(gate: dict, tree: str, root: Path = ROOT, scoped: bool = True) -> str:
    """What a PASS of this gate is a fact about: its declared inputs, else the whole tree.

    `scoped=False` is the strict whole-tree proof a landing reads, so an input list never weakens it.
    """
    patterns = gate_inputs(gate) if scoped else None
    if patterns is None:
        return f"tree:{tree}"
    names = [
        n
        for n in _input_names(root)
        if any(fnmatch.fnmatchcase(n.decode("utf-8", "surrogateescape"), p) for p in patterns)
    ]
    return f"inputs:{_digest(root, names)}"


def _dependency_digest(root: Path = ROOT) -> str:
    """Digest of the dependency lock file and toolchain config for cache invalidation.

    WHY (3.60.0). Byte-identical inputs with different dependencies can produce different results:
    a gate that passes with ruff 0.16.8 may fail with ruff 0.17.0. The lock file and config files
    that shape toolchain behavior are included in the cache key so evidence from one environment
    is never REUSED in another after a dependency change."""
    digest = hashlib.sha256()
    # Lock files that pin dependency versions
    for lock_name in ("scripts/requirements.lock.txt", "uv.lock", "pyproject.toml"):
        lock_path = root / lock_name
        if lock_path.is_file():
            digest.update(lock_name.encode() + b"\0")
            digest.update(lock_path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def gate_key(gate: dict, root: Path = ROOT) -> str:
    """A gate's identity for reuse: id, argv, mutates, and the environment its program resolves in.

    WHY (3.47.0). Byte-identical inputs on another interpreter or with an upgraded tool are a new
    measurement, so evidence from one environment is never REUSED in another; it is re-run instead.

    WHY (3.60.0). Added dependency digest: a gate that passes with one set of dependencies may fail
    with another. The lock file digest ensures cache invalidation when dependencies change."""
    seen = {
        "id": gate.get("id"),
        "argv": gate.get("argv"),
        "mutates": bool(gate.get("mutates")),
        "python": sys.version,
        "platform": sys.platform,
        "machine": os.uname().machine if hasattr(os, "uname") else "",
        "program": _program_identity(str((gate.get("argv") or [""])[0])),
        "deps": _dependency_digest(root),
    }
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

    return _git_path("headron-fast-evidence.json")


def reuse_evidence(gates: list[dict], tree: str, root: Path = ROOT, scoped: bool = True) -> dict[str, dict]:
    """The recorded PASS rows whose proof scope is still this one, by gate_key; any other gate re-runs.

    A row is reused when its scope matches: its declared inputs unchanged, or, for an undeclared gate, the
    whole tree byte-identical. A row from a later edit to an input it does not name is still a fact here.
    """
    try:
        saved = json.loads(_evidence_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = saved.get("rows") if saved.get("schema") == EVIDENCE_SCHEMA else None
    keys = {gate_key(g, root): g for g in gates}
    if not isinstance(rows, dict):
        return {}
    return {
        k: r
        for k, r in rows.items()
        if k in keys
        and r.get("verdict") == "PASS"
        and r.get("argv") == keys[k].get("argv")
        and r.get("scope") == proof_scope(keys[k], tree, root, scoped)
    }


def write_evidence(passed: dict[str, dict]) -> None:
    """The PASS rows, each carrying its proof scope; bounded by the done set, never by runs. A FAIL never becomes proof."""
    _evidence_path().write_text(
        json.dumps({"schema": EVIDENCE_SCHEMA, "rows": passed}, indent=1) + "\n", encoding="utf-8"
    )


def run_gate(gate: dict, cwd: Path = ROOT, env: dict | None = None) -> dict:
    argv = [sys.executable if gate["argv"][0] == "python" else gate["argv"][0], *gate["argv"][1:]]
    row = {
        "id": gate["id"],
        "argv": gate["argv"],
        "mutates": bool(gate.get("mutates")),
        # CARRIED ONTO THE ROW so --json records it too: a machine-dependent PASS is a LOCAL pass, and
        # a consumer reading the record must be able to tell those apart without re-reading atlas.yaml.
        "machine_dependent": bool(gate.get("machine_dependent")),
    }
    if row["mutates"] and os.environ.get("HEADRON_READ_ONLY"):
        return row | {"verdict": "NOT RUN", "why": "mutating gate under HEADRON_READ_ONLY"}
    if not shutil.which(argv[0]):
        return row | {"verdict": "NOT RUN", "why": f"{argv[0]} is not installed here"}
    # THE QUEUE WAIT IS NOT THE GATE'S TIME: a planted suite waits for the machine slot here, before the timed
    # run, so TIMEOUT counts the suite alone. Holding it here, the suite inherits it via HEADRON_SLOT_HELD.
    _held = None  # noqa: F841 — held to return, past the timed run
    if any("atlas_test" in part for part in argv):
        try:
            _held = __import__("slot").take(
                f"verify {row['id']}", wait=float(os.environ.get("HEADRON_SLOT_WAIT", "3600"))
            )
            if env is not None and "HEADRON_SLOT_HELD" in os.environ:
                env["HEADRON_SLOT_HELD"] = os.environ["HEADRON_SLOT_HELD"]
        except SystemExit:
            return row | {"verdict": "NOT RUN", "why": "queue wait ran out for the machine slot"}
    start = time.monotonic()
    try:
        returncode, text, size = _bounded_run(argv, cwd, env)
    except subprocess.TimeoutExpired:
        # NO VERDICT, NOT A FAIL: an overrun under load says nothing about the change. branchstate already
        # read it NOT RUN; FAIL here blamed the change and fed learn() a cause that was the machine's.
        return row | {"verdict": "NOT RUN", "why": f"timed out after {TIMEOUT}s", "seconds": TIMEOUT}
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if returncode == 75:  # atlas_test.BUSY: the machine holds another suite — not run, holder named
        return row | {"verdict": "NOT RUN", "why": (lines[-1] if lines else "busy")[:200]}
    # COULD NOT DECIDE IS NOT DECIDED NO: enforce.py read pytest's exit 5 ("no tests collected") as
    # undecided, and this runner called the same exit a FAIL, so a consumer with no tests could never pass.
    undecided = undecided_exit(_tool(gate["argv"]), returncode)
    if undecided:
        return row | {
            "verdict": "NOT RUN",
            "exit": returncode,
            "why": f"{_tool(gate['argv'])} exited {returncode} and decided nothing: {undecided}"[:200],
        }
    said = [ln.strip() for ln in lines if any(k in ln for k in SELF_REPORT)]
    # THE CAUSE, NOT THE FIRST ALARMING LINE (3.9.0): a suite that crashed printed an expected
    # "- WRONG ROUTE" from a passing case first, and verify blamed that. A traceback's last line is the cause.
    crashed = any(ln.startswith("Traceback") for ln in lines)
    # A suite's own verdict comes LAST, as a FAIL line or a guard's verdict word (DUPLICATE, CASE COUNT
    # MOVED); a "- " line is a check's finding list. SECOND SIGHTING: preferring any FAIL line over a later
    # shouted one blamed a passing case's expected "FAIL empty roster" for a suite that died on its count.
    alarms = [ln for ln in lines if re.match(r"[A-Z]{4,}\b", ln) and not ln.startswith(("SCOPE", "COVERAGE"))]
    first_error = (
        lines[-1]
        if crashed and lines
        else alarms[-1]
        if alarms
        else next((ln for ln in lines if ln.startswith("- ")), lines[-1] if lines else "")
    )
    return row | {
        "verdict": "PASS" if returncode == 0 else "FAIL",
        "exit": returncode,
        "seconds": round(time.monotonic() - start, 1),
        "self_report": said[:3],
        "output_bytes": size,
        "calls": 1,
        "why": "" if returncode == 0 else (first_error[:160] or f"exited {returncode}"),
    }


def _jobs(argv: list[str]) -> int:
    """Read --jobs N; a zero or malformed worker count refuses before any gate runs."""
    values = [arg.split("=", 1)[1] for arg in argv if arg.startswith("--jobs=")]
    if "--jobs" in argv:
        pos = argv.index("--jobs") + 1
        if pos == len(argv) or argv[pos].startswith("--"):
            raise SystemExit("verify: --jobs requires a positive integer")
        values.append(argv[pos])
    if len(values) > 1:
        raise SystemExit("verify: --jobs may be supplied once")
    try:
        jobs = int(values[0]) if values else DEFAULT_JOBS
    except ValueError as error:
        raise SystemExit("verify: --jobs requires a positive integer") from error
    if jobs < 1:
        raise SystemExit("verify: --jobs requires a positive integer")
    return jobs


def gate_dependencies(gates: list[dict]) -> dict[str, tuple[str, ...]]:
    """Validate the declared gate DAG and return each gate's prerequisite IDs."""
    ids = [str(gate.get("id") or "") for gate in gates]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("done_set gate ids must be non-empty and unique")
    known = set(ids)
    dependencies: dict[str, tuple[str, ...]] = {}
    for gate in gates:
        gate_id = str(gate["id"])
        raw = gate.get("depends_on") or []
        if not isinstance(raw, list) or not all(isinstance(dep, str) and dep for dep in raw):
            raise ValueError(f"gate {gate_id!r} depends_on must be a list of non-empty gate ids")
        if len(raw) != len(set(raw)):
            raise ValueError(f"gate {gate_id!r} names a prerequisite more than once")
        absent = set(raw) - known
        if absent:
            raise ValueError(f"gate {gate_id!r} depends on undeclared gate {sorted(absent)[0]!r}")
        if gate_id in raw:
            raise ValueError(f"gate {gate_id!r} depends on itself")
        dependencies[gate_id] = tuple(raw)
    pending = {gate_id: set(deps) for gate_id, deps in dependencies.items()}
    while pending:
        ready = {gate_id for gate_id, deps in pending.items() if not deps}
        if not ready:
            raise ValueError(f"done_set gate dependency cycle: {', '.join(sorted(pending))}")
        for gate_id in ready:
            pending.pop(gate_id)
        for deps in pending.values():
            deps.difference_update(ready)
    return dependencies


def run_declared_gates(
    gates: list[dict], cwd: Path, jobs: int, completed: dict[str, dict] | None = None, on_row: Any | None = None
) -> list[dict]:
    """Run dependency-ready readers concurrently and retain pruned descendants as NOT RUN rows.

    Mutators remain exclusive: every ready reader drains before one starts, and each ready mutator
    runs alone. A blocked descendant is visible rather than silently omitted from the verdict.
    """
    dependencies = gate_dependencies(gates)
    rows: dict[int, dict] = {
        index: completed[str(gate["id"])]
        for index, gate in enumerate(gates)
        if completed and str(gate["id"]) in completed
    }
    if on_row and completed:
        for index in sorted(rows):
            on_row(rows[index])
    pending = set(range(len(gates))) - set(rows)
    ids = {str(gate["id"]): index for index, gate in enumerate(gates)}
    while pending:
        blocked = [
            index
            for index in pending
            if any(
                rows[ids[dep]]["verdict"] not in ("PASS", "REUSED")
                for dep in dependencies[str(gates[index]["id"])]
                if ids[dep] in rows
            )
        ]
        for index in blocked:
            gate = gates[index]
            dependency = next(
                dep
                for dep in dependencies[str(gate["id"])]
                if ids[dep] in rows and rows[ids[dep]]["verdict"] not in ("PASS", "REUSED")
            )
            rows[index] = {
                "id": gate["id"],
                "argv": gate["argv"],
                "mutates": bool(gate.get("mutates")),
                "machine_dependent": bool(gate.get("machine_dependent")),
                "verdict": "NOT RUN",
                "why": f"pruned: prerequisite {dependency} was {rows[ids[dependency]]['verdict']}",
            }
            pending.remove(index)
            if on_row:
                on_row(rows[index])
        if blocked:
            # A newly pruned row can itself be a prerequisite. Propagate the explicit NOT RUN
            # result before looking for runnable descendants in the remaining DAG.
            continue
        ready = [
            index
            for index in pending
            if all(
                ids[dep] in rows and rows[ids[dep]]["verdict"] in ("PASS", "REUSED")
                for dep in dependencies[str(gates[index]["id"])]
            )
        ]
        readers = [index for index in ready if not gates[index].get("mutates")]
        if readers:
            with ThreadPoolExecutor(max_workers=min(jobs, len(readers))) as pool:
                futures = {}
                for r_idx, index in enumerate(readers):
                    if r_idx > 0 and jobs > 1:
                        resilience.space(0.008)
                    fut = pool.submit(run_gate, gates[index], cwd, _gate_env(f"{index}-{gates[index]['id']}"))
                    futures[fut] = index
                for future in as_completed(futures):
                    index = futures[future]
                    row = future.result()
                    rows[index] = row
                    pending.remove(index)
                    if on_row:
                        on_row(row)
            continue
        if ready:
            index = ready[0]
            rows[index] = run_gate(gates[index], cwd, _gate_env(f"{index}-{gates[index]['id']}"))
            pending.remove(index)
            if on_row:
                on_row(rows[index])
            continue
        raise AssertionError("validated gate dependency DAG had no runnable gate")
    return [rows[index] for index in range(len(gates))]


def print_row(r: dict, first_seen: dict[str, str] | None = None) -> None:
    """Format and print one gate verdict immediately to provide real-time verification feedback."""
    why = r.get("why") or ""
    if first_seen is not None:
        if why and why in first_seen:
            why = f"same {'evidence' if r['verdict'] == 'REUSED' else 'cause'} as {first_seen[why]}"
        elif why:
            first_seen[why] = r["id"]
    local = "  [this machine only]" if r.get("machine_dependent") and r["verdict"] == "PASS" else ""
    print(f"{_paint(r['verdict'])}{r['id']:<16}{str(r.get('seconds', '-')) + 's':>7}  {why}{local}", flush=True)
    for said in r.get("self_report") or []:
        print(f"{'':<24}{said[:110]}", flush=True)


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
        for gate in (
            g for g in required_gates({"change_class": "source_change"}) if g in (policy.get("fast_loop") or [])
        ):
            argv = gate_record(path, gate).get("argv") or []
            if argv and argv[-1] == path:  # per-file only: a whole-suite runner belongs to the full verify
                rows.append({"id": f"{gate}:{path}", "argv": argv, "mutates": False})
    return rows


def record(rows: list[dict], tally: dict, code: int) -> dict:
    """The `--json` record, ONE PRODUCER: frozen as tools/atlas-output.schema.json $defs/verify, and atlas_test
    asserts real rows against it without running verify inside the suite verify itself runs."""
    from runtime import resolve  # noqa: PLC0415

    return {
        "schema": 1,
        "command": "verify",
        "atlas_version": str(atlas().get("version")),
        "rows": rows,
        "tally": tally,
        "exit": code,
        "agent": resolve(),
    }


def unpushed_row() -> dict:
    """THE SESSION-END GATE HOLDS THE LANE BOUND (3.47.0). branchstate printed every breach and exited 1,
    and nothing that ends a session read that exit: fifteen lanes held unpushed work, several past forty
    hours against a two-hour bound. `verify` IS the done hook, so a breach is a FAIL row here, never a print.
    Machine dependent by nature: it reads this clone's refs, which no other machine has."""
    from branchstate import unpushed_errors  # noqa: PLC0415

    problems = unpushed_errors()
    return {
        "id": "unpushed_bound",
        "argv": ["python", "scripts/branchstate.py"],
        "mutates": False,
        "machine_dependent": True,
        "verdict": "FAIL" if problems else "PASS",
        "calls": 1,
        "why": f"{len(problems)} breach(es), first: {problems[0]}"[:160] if problems else "",
    }


def hooks_row(root: Path | None = None) -> dict:
    """THE HOOKS ARE ACTIVE OR THIS ROW SAYS SO. `.githooks/pre-push` refuses a bare lane push and
    the tracked pre-commit runs the fast rungs, but git reads them only when core.hooksPath names that
    directory. Unset, a bare push passes silently in this clone. A missing hook or a non-executable one is
    the same silence, so both are FAIL. Machine dependent: the setting is per clone, shared by its worktrees."""
    root = root or Path.cwd()
    configured = subprocess.run(
        ["git", "-C", str(root), "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    ).stdout.strip()
    problems = [] if configured == ".githooks" else [f"core.hooksPath is {configured or 'unset'}, not .githooks"]
    problems += [
        f"{name} is missing or not executable"
        for name in ("pre-push", "pre-commit")
        if not (root / ".githooks" / name).is_file() or not os.access(root / ".githooks" / name, os.X_OK)
    ]
    return {
        "id": "hooks_active",
        "argv": ["git", "config", "--get", "core.hooksPath"],
        "mutates": False,
        "machine_dependent": True,
        "verdict": "FAIL" if problems else "PASS",
        "calls": 1,
        "why": (
            (" ; ".join(problems) + " — activate with: git config core.hooksPath .githooks")
            if problems
            else "core.hooksPath is .githooks; pre-push and pre-commit are executable"
        )[:160],
    }


def upstream_row() -> dict:
    """THE UPSTREAM COUNT (3.53.0): the lane bound's other direction, commits on the default branch this
    lane lacks. No origin ref is NOT RUN; the count read is printed on every verdict, a pass included."""
    from atlascore import atlas as _atlas  # noqa: PLC0415
    from upstream import upstream_errors  # noqa: PLC0415

    problems, count = upstream_errors(Path.cwd(), _atlas().get("branch_policy") or {})
    return {
        "id": "upstream_bound",
        "argv": ["python", "scripts/upstream.py"],
        "mutates": False,
        "machine_dependent": True,
        "verdict": "FAIL" if problems else "NOT RUN" if count is None else "PASS",
        "calls": 1,
        "why": (problems[0] if problems else f"upstream count {count}, from the last fetch")[:160],
    }


def target_tree() -> Path:
    """The repository `verify` proves: the caller's, found from the working directory; ROOT outside any repository.

    SIGHTED (3.51.0): `headron verify` in a consumer ran THIS atlas's done set over ROOT and wrote its marker
    into the atlas's git dir, so the consumer's dashboard never got a verdict. An atlas checkout (a lane of
    this repository included) keeps the done set; any other repository gets the gates routed for its change.
    """
    done = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    return Path(done.stdout.strip()).resolve() if done.returncode == 0 else ROOT.resolve()


def is_atlas_checkout(tree: Path) -> bool:
    return (tree / "atlas.yaml").is_file() and (tree / "scripts" / "verify.py").is_file()


def consumer_files(tree: Path, base: str | None = None) -> tuple[list[str], str]:
    """The consumer's change: commits past a base (or the remote default), plus everything uncommitted.
    ("", reason) on a diff git could not answer, which the caller turns into a NOT RUN row."""
    bases = (
        (base,)
        if base
        else ("origin/HEAD", f"origin/{(atlas().get('branch_policy') or {}).get('default_base') or 'main'}")
    )
    for ref in bases:
        try:
            committed = diff_names(tree, f"{ref}...HEAD")
        except ValueError:
            continue
        return sorted({f for f in [*committed, *changed_paths(tree)] if (tree / f).is_file()}), ""
    return sorted(f for f in changed_paths(tree) if (tree / f).is_file()), (
        f"cannot diff base {base!r}; choose an existing commit with --base <ref>"
        if base
        else "no origin/HEAD or default base to diff against; fetch origin or use --base <ref> "
        "(for local uncommitted changes against the current commit: --base HEAD)"
    )


def consumer_rows(tree: Path, base: str | None = None) -> list[dict]:
    """Run each gate the atlas routes for the consumer's changed files, IN the consumer's tree.
    A declared `none` (absent) is no row; an undeclared or unroutable gate is NOT RUN, never skipped."""
    from branchstate import _consumer_change_class, consumer_records  # noqa: PLC0415

    files, unknown = consumer_files(tree, base)
    if not files:  # ONE ROW: the missing base and the empty change were two rows for one gate, counted twice
        why = "; ".join(w for w in (unknown, f"no changed file in {tree}") if w)
        return [{"id": "changed_files", "argv": [], "verdict": "NOT RUN", "why": why}]
    rows: list[dict] = [{"id": "changed_files", "argv": [], "verdict": "NOT RUN", "why": unknown}] if unknown else []
    ran: list[list[str]] = []
    for rec in consumer_records(tree, files, _consumer_change_class()):
        argv, name = rec.get("argv"), f"{rec.get('gate')}:{rec['path']}"
        if rec.get("state") == "runnable" and argv and argv not in ran:
            ran.append(argv)
            rows.append(run_gate({"id": name, "argv": argv}, cwd=tree))
        elif rec.get("state") not in ("runnable", "absent"):
            rows.append(
                {"id": name, "argv": argv, "verdict": "NOT RUN", "why": str(rec.get("why") or rec.get("state"))}
            )
    return rows


def _store(tree: Path, name: str) -> Path:
    """A runtime record inside `tree`'s own git dir, never tracked."""
    done = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", name],
        cwd=tree,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    return Path(done.stdout.strip())


LESSONS_CAP = 200  # distinct causes kept; the store grows by cause, never by run — bounded, per unbounded-growth


def learn(rows: list[dict]) -> list[str]:
    """Count each failing cause across runs; return the causes seen twice or more — the second time is a rule."""
    from safeedit import _git_path  # noqa: PLC0415

    store = _git_path("headron-lessons.json")
    try:
        lessons = json.loads(store.read_text(encoding="utf-8")) if store.is_file() else {}
    except (OSError, json.JSONDecodeError):
        # A truncated write from a killed run resets the count, never the run (3.56.0): learn()
        # feeds report() after the gates ran, and a crash there loses the work with no verdict.
        lessons = {}
    # ONE COUNT PER CAUSE PER RUN: twelve files failing one gate for one reason is one lesson, not twelve.
    seen = {f"{r['id'].split(':')[0]} :: {r.get('why', '')[:90]}" for r in rows if r["verdict"] == "FAIL"}
    for key in seen:
        lessons[key] = lessons.get(key, 0) + 1
    lessons = dict(sorted(lessons.items(), key=lambda kv: -kv[1])[:LESSONS_CAP])
    if not os.environ.get("HEADRON_READ_ONLY"):  # the MCP route reads; a NOT RUN suite must not count as a lesson
        store.write_text(json.dumps(lessons, indent=1), encoding="utf-8")
    return [k for k in seen if lessons[k] >= 2]


def _parse_base(argv: list[str]) -> str | None:
    """Optional `--base <ref>` / `--base=<ref>` for consumer trees without origin (folded from product-readiness)."""
    base = next((arg.split("=", 1)[1] for arg in argv if arg.startswith("--base=")), None)
    if "--base" in argv:
        position = argv.index("--base") + 1
        if position == len(argv) or argv[position].startswith("--"):
            raise SystemExit("verify: --base requires an existing commit or ref")
        base = argv[position]
    return base


def _receipt_path(argv: list[str]) -> Path | None:
    """Optional `--receipt <path>` / `--receipt=<path>`: where this run's receipt is written."""
    path = next((arg.split("=", 1)[1] for arg in argv if arg.startswith("--receipt=")), None)
    if "--receipt" in argv:
        position = argv.index("--receipt") + 1
        if position == len(argv) or argv[position].startswith("--"):
            raise SystemExit("verify: --receipt requires a file path")
        path = argv[position]
    return Path(path) if path else None


def _git_text(tree: Path, *args: str) -> str | None:
    done = subprocess.run(["git", *args], cwd=tree, capture_output=True, text=True, check=False, timeout=600)
    return done.stdout if done.returncode == 0 else None


def _commit_of(tree: Path, ref: str) -> str | None:
    found = _git_text(tree, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return found.strip() if found and found.strip() else None


def _policy_of(text: str) -> object:
    """The verification_policy section of an atlas.yaml text; ValueError when it has none (a finding, not a skip)."""
    data = strict_yaml(text, "atlas.yaml")
    if not isinstance(data, dict) or "verification_policy" not in data:
        raise ValueError("no verification_policy section")
    return data["verification_policy"]


def _pin(ok: bool, why: str, commit: str | None, digest: str | None) -> dict:
    """The policy_pinned row, and the pin the receipt carries: base commit and policy digest, None where unread."""
    row = {"id": "policy_pinned", "argv": [], "verdict": "PASS" if ok else "FAIL", "why": why}
    return {"row": row, "base_commit": commit, "digest": digest}


def policy_pin(tree: Path, argv: list[str]) -> dict:
    """THE POLICY IS READ FROM BASE (receipt v1). The PR head's verification_policy must equal the base commit's, or
    the receipt FAILs: a PR cannot grade itself with the gates it removed. A missing base or policy is a FAIL
    finding, never a skip, so the pin carries None wherever nothing could be read."""
    base = _parse_base(argv)
    refs = (
        (base,)
        if base
        else ("origin/HEAD", f"origin/{(atlas().get('branch_policy') or {}).get('default_base') or 'main'}")
    )
    commit = next((c for c in (_commit_of(tree, ref) for ref in refs) if c), None)
    if commit is None:
        return _pin(False, "no base commit to read the policy from; pass --base <ref>", None, None)
    base_text = _git_text(tree, "show", f"{commit}:atlas.yaml")
    if base_text is None:
        return _pin(False, f"atlas.yaml missing at base {commit[:12]}: no policy to read", commit, None)
    try:
        digest = receipt.digest(_policy_of(base_text))
    except Exception as error:  # a finding: the base's policy is unreadable, so nothing can be pinned to it
        return _pin(False, f"atlas.yaml at base {commit[:12]} is not a policy: {error}", commit, None)
    if not (tree / "atlas.yaml").is_file():
        return _pin(
            False,
            f"atlas.yaml removed in the PR head: refused, the policy is read from base {commit[:12]}",
            commit,
            digest,
        )
    try:
        same = receipt.digest(_policy_of((tree / "atlas.yaml").read_text(encoding="utf-8"))) == digest
    except Exception as error:
        return _pin(False, f"atlas.yaml in the PR head is not a policy: {error}", commit, digest)
    if not same:
        return _pin(
            False,
            f"verification_policy edited in the PR head: refused, the policy is read from base {commit[:12]}",
            commit,
            digest,
        )
    return _pin(True, f"verification_policy unchanged from base {commit[:12]}", commit, digest)


def write_receipt(path: Path, rows: list[dict], pin: dict, input_tree: str) -> None:
    """This run's receipt: the rows the verdict is read from, through receipt.py's one mapping, and nothing else."""
    body = receipt.build(rows, base_commit=pin["base_commit"], policy_digest=pin["digest"], input_digest=input_tree)
    path.write_text(receipt.dumps(body), encoding="utf-8")


def main(argv: list[str]) -> int:
    overall_start = time.monotonic()
    tree_root = target_tree()
    receipt_to = _receipt_path(argv)
    live_stream = "--json" not in argv
    first_seen: dict[str, str] = {}
    on_row = (lambda r: print_row(r, first_seen)) if live_stream else None
    if not is_atlas_checkout(tree_root):
        rows = consumer_rows(tree_root, _parse_base(argv))
        pin = policy_pin(tree_root, argv) if receipt_to else None
        if pin:
            rows.append(pin["row"])
        code = report(
            rows, argv, _store(tree_root, "headron-last-verify.json"), measured=True, overall_start=overall_start
        )
        if receipt_to and pin:
            write_receipt(receipt_to, rows, pin, input_digest(tree_root))
        return code
    changed = "--changed" in argv
    if changed and receipt_to:
        raise SystemExit("verify: --receipt needs the whole done set; drop --changed")
    gates = changed_gates() if changed else (atlas().get("verification_policy") or {}).get("done_set") or []
    if not gates:
        print("verify: verification_policy/done_set declares no gate — an empty done set passes nothing")
        return 1
    try:
        gate_dependencies(gates)
    except ValueError as error:
        print(f"verify: invalid done_set dependency graph: {error}")
        return 1
    tree = input_digest()
    saved = {} if "--fresh" in argv else reuse_evidence(gates, tree)
    keys = [gate_key(g) for g in gates]
    reused = {
        str(gate["id"]): saved[key]
        | {"verdict": "REUSED", "why": "this tree, argv and environment PASSED before; --fresh re-measures"}
        for key, gate in zip(keys, gates, strict=True)
        if key in saved
    }
    # Display cached results immediately for the edit loop, clearly marked REUSED or stale
    if on_row and reused:
        for gate_id, evidence in reused.items():
            row = {"id": gate_id, "verdict": "REUSED", "seconds": 0, "why": "cached"}
            on_row(row)
    jobs = _jobs(argv)
    rows: list[dict[str, Any]] = run_declared_gates(gates, tree_root, jobs, reused, on_row=on_row)
    proven = {
        k: g | r | {"scope": proof_scope(g, tree)}
        for k, g, r in zip(keys, gates, rows, strict=True)
        if r["verdict"] == "PASS"
    }
    passed = saved | proven
    if len(passed) > len(saved) and input_digest() == tree:  # a tree edited mid-run proves nothing about either
        write_evidence(passed)
    measured = any(r["verdict"] != "REUSED" for r in rows)
    spared = round(sum(r.get("seconds") or 0 for r in rows if r["verdict"] == "REUSED"), 1)
    if changed:  # a fact read from the last suite's ledger, never run: the fast loop stays seconds
        import edges  # noqa: PLC0415
        import impact  # noqa: PLC0415

        files = [f for f in changed_paths(ROOT) if (ROOT / f).is_file()]
        extra_fast = [edges.changed_row(files), impact.changed_row()]
        if on_row:
            for extra in extra_fast:
                on_row(extra)
        rows += extra_fast
    extra_lane = [] if changed else [unpushed_row(), upstream_row(), hooks_row()]
    if on_row:
        for extra in extra_lane:
            on_row(extra)
    rows += extra_lane
    from safeedit import _git_path  # noqa: PLC0415

    pin = policy_pin(tree_root, argv) if receipt_to else None
    if pin:
        if on_row:
            on_row(pin["row"])
        rows.append(pin["row"])
    code = report(
        rows,
        argv,
        _git_path("headron-last-verify.json"),
        measured,
        spared,
        learn(rows),
        streamed=live_stream,
        overall_start=overall_start,
        jobs=jobs,
        binding={
            "base": pin["base_commit"] if pin else None,
            "policy_digest": pin["digest"] if pin else None,
            "input_digest": tree,
        },
    )
    if receipt_to and pin:
        write_receipt(receipt_to, rows, pin, tree)
    return code


GATE_HOME: list[str] = []  # one private directory per run, made on first use


def _gate_env(tag: str = "") -> dict:
    """A gate's environment: HEADRON_HOME moved aside, so a suite's planted refusals never reach the field ledger.

    ONE HOME PER CONCURRENT GATE (3.59.x): the ledger under HEADRON_HOME is a hash-chained append, and two
    suites appending one stream would interleave their links — so a gate run beside others gets a home
    of its own (`tag`), removed at exit like the shared one."""
    if not tag:
        if not GATE_HOME:
            GATE_HOME.append(tempfile.mkdtemp(prefix="headron-gate-home-"))
            # REMOVED AT EXIT (3.54.0): one directory per run and none removed left 34 in $TMPDIR on one machine.
            atexit.register(shutil.rmtree, GATE_HOME[0], ignore_errors=True)
        home = GATE_HOME[0]
    else:
        # Gate ids include artifact paths (and therefore ``:`` and ``/``).  Those are valid record
        # identifiers but not portable filename components, notably on macOS where ``:`` is rejected.
        # Keep a short readable stem and a digest so independent long ids remain distinguishable.
        safe_tag = re.sub(r"[^A-Za-z0-9_.-]+", "-", tag).strip("-") or "gate"
        marker = hashlib.sha256(tag.encode("utf-8")).hexdigest()[:12]
        home = tempfile.mkdtemp(prefix=f"headron-gate-{safe_tag[:48]}-{marker}-")
        atexit.register(shutil.rmtree, home, ignore_errors=True)
    return {**os.environ, "HEADRON_HOME": home}


def report(
    rows: list[dict],
    argv: list[str],
    marker: Path,
    measured: bool,
    spared: float = 0,
    recurring=(),
    streamed: bool = False,
    overall_start: float | None = None,
    jobs: int = 1,
    binding: dict | None = None,
) -> int:
    """Write the last verdict to `marker` and print it; the verdict is the returned code.

    `binding` (base, policy_digest, input_digest) is what the verdict was measured over; receipt.py reads it back."""
    tally = {v: sum(r["verdict"] == v for r in rows) for v in ("PASS", "REUSED", "FAIL", "NOT RUN")}
    local_only = sum(1 for r in rows if r.get("machine_dependent") and r["verdict"] == "PASS")
    code = verdict_code(rows)
    wall_seconds = round(time.monotonic() - overall_start, 2) if overall_start is not None else 0.0
    cpu_seconds = round(sum(r.get("seconds") or 0 for r in rows if r.get("verdict") == "PASS"), 2)
    speedup = round(cpu_seconds / max(0.1, wall_seconds), 2) if wall_seconds > 0 else 1.0
    telemetry = {
        "wall_seconds": wall_seconds,
        "cpu_seconds": cpu_seconds,
        "spared_seconds": spared,
        "speedup": speedup,
        "jobs": jobs,
    }
    # THE LAST VERDICT OUTLIVES THE PROCESS (3.19.0): `headron resume` reads it, so an agent picking up a lane
    # knows which gate failed without re-running everything. A runtime store inside .git, never tracked.
    if not os.environ.get("HEADRON_READ_ONLY"):  # an MCP verify's exit 2 overwrote the lane's real PASS
        marker.write_text(
            json.dumps({"exit": code, "rows": rows, "measured": measured, "telemetry": telemetry} | (binding or {})),
            encoding="utf-8",
        )
        import agents  # noqa: PLC0415

        failed = [r["id"] for r in rows if r["verdict"] in ("FAIL", "NOT RUN")]
        agents.field("field_verify", {"exit": code, "tally": tally, "failed": failed})
    if "--json" in argv:
        print(json.dumps(record(rows, tally, code), indent=2))
        return code
    if not streamed:
        first_seen: dict[str, str] = {}
        for r in rows:
            print_row(r, first_seen)
    for lesson in recurring[:3]:
        print(f"RECURRING  {lesson} — seen before: write the rule and its guard (`headron failures` shows the shape)")
    print(
        f"verify: {tally['PASS']} PASS, {tally['REUSED']} REUSED, {tally['FAIL']} FAIL, {tally['NOT RUN']} NOT RUN of {len(rows)} declared gates"
        f"{f'; {local_only} of those passes are this machine only' if local_only else ''}"
        f"{f'; reuse spared {spared}s' if spared else ''}"
        + ("" if code == 0 else " — NOT done" + (" (incomplete: a NOT RUN is never a pass)" if code == 2 else ""))
    )
    return code


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):  # a script with no parser would RUN on --help
        print((__doc__ or sys.argv[0]).strip())
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
