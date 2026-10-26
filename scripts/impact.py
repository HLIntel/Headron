#!/usr/bin/env python3
"""The runtime test-impact map: which repository files each planted group ACTUALLY loads, keyed on content hashes.

WHY. `verify --changed` ran no test at all, and the static import graph cannot scope one: MEASURED, a
median change reaches 32 of 37 test modules through lazy imports. So the map is RECORDED, not derived:
while a group runs, every repository file whose code executes (sys.monitoring), every file it opens
(the `open` audit event) and every repository script it spawns (plus that script's local imports) is a
dependency. A group that passed is stored with the sha256 of each dependency's bytes.

SELECTION. A group runs when any dependency's bytes differ from the passing record, or when it has no
record. Keyed on bytes, never on a diff, so a record from any worktree of this clone is valid for the
same bytes: the map lives in the COMMON git dir, and a fresh lane inherits it. No map is NOT RUN.

LIMIT. A value read through a cache filled before the group began, or a child process's dynamic import,
is not seen. The fast loop is the quick answer; the full planted suite in the done set stays the verdict.

    python scripts/impact.py run <group>...   # run named planted groups under the suite locks, refresh their record
    python scripts/impact.py select           # print the groups the current bytes select, and why
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = "thea-impact.json"
SCHEMA = 1
# Bounded storage: keep only groups that still exist in PLANTED_GROUPS; drop stale entries on save.
# The store is small (one hash per dependency per group), but stale groups accumulate over time.
MAX_STORE_BYTES = 256 * 1024  # 256 KiB cap: ~30 groups × ~100 deps × 64-byte hash each
_PREFIX = str(ROOT) + os.sep
_STACK: list[set[str]] = []  # one dependency set per open group; a nested group's set merges into its parent
_RECORDS: dict[str, dict | None] = {}  # top-level group -> {"deps": [...], "secs": n}, or None when it failed
_ON: list[bool] = []


def store_path() -> Path:
    """The map, in the clone's COMMON git dir: hash-keyed, so every worktree may read and refresh it."""
    where = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    ).stdout.strip()
    return Path(where) / STORE


def _note(path: str) -> None:
    if _STACK and path.startswith(_PREFIX):
        _STACK[-1].add(path[len(_PREFIX) :])


def _on_start(code, _offset):
    _note(code.co_filename)
    return sys.monitoring.DISABLE  # one event per code object per group: restart_events re-arms it


def _audit(event: str, args: tuple) -> None:
    if not _STACK:
        return
    if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
        _note(os.path.abspath(os.fsdecode(args[0])))
    elif event == "subprocess.Popen" and len(args) > 1 and isinstance(args[1], (list, tuple)):
        cwd = os.fsdecode(args[2]) if len(args) > 2 and args[2] else os.getcwd()
        for arg in args[1]:
            arg = os.fsdecode(arg) if isinstance(arg, (str, bytes)) else ""
            if arg.endswith(".py"):
                for dep in closure(Path(os.path.join(cwd, arg)).resolve()):
                    _note(str(dep))


def closure(script: Path) -> set[Path]:
    """A spawned script and the sibling modules it imports, transitively: the child is not traced, so its
    static reach stands in for it. Over-inclusion only selects more; it never hides a dependency."""
    seen: set[Path] = set()
    todo = [script]
    while todo:
        path = todo.pop()
        if path in seen or not path.is_file() or not str(path).startswith(_PREFIX):
            continue
        seen.add(path)
        from atlascore import parsed_python, walked  # noqa: PLC0415 — the shared, content-keyed trees

        try:
            tree = parsed_python(path.read_text(encoding="utf-8"), str(path))
        except UnicodeDecodeError:
            continue
        for node in walked(tree) if tree else ():
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
            if isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module]
            todo += [path.parent / f"{n.split('.')[0]}.py" for n in names]
    return seen


def start() -> bool:
    """Arm the recorder once per process. False (records nothing) before Python 3.12, which has no
    sys.monitoring: the map is then not refreshed, and selection reads whatever record exists."""
    if _ON:
        return _ON[0]
    mon = getattr(sys, "monitoring", None)
    tool = next((t for t in (5, 4, 3, 2) if mon and mon.get_tool(t) is None), None)
    _ON.append(tool is not None)
    if mon and tool is not None:
        mon.use_tool_id(tool, "thea-impact")
        mon.register_callback(tool, mon.events.PY_START, _on_start)
        mon.set_events(tool, mon.events.PY_START)
        sys.addaudithook(_audit)
    return _ON[0]


def _clear_caches() -> None:
    """A value cached before the group began is read without an `open`: clear this repository's lru caches
    at each top-level group, so the group re-reads what it uses and the read is recorded."""
    import functools  # noqa: PLC0415
    import gc  # noqa: PLC0415

    for obj in gc.get_objects():
        if isinstance(obj, functools._lru_cache_wrapper):  # noqa: SLF001 — the one type every lru_cache is
            home = getattr(sys.modules.get(getattr(obj, "__module__", "")), "__file__", None) or ""
            if home.startswith(_PREFIX):
                obj.cache_clear()


def enter() -> None:
    if _ON and _ON[0]:
        if not _STACK:
            _clear_caches()
        _STACK.append(set())
        sys.monitoring.restart_events()


def leave(name: str, ok: bool, secs: float) -> None:
    if not (_ON and _ON[0] and _STACK):
        return
    deps = _STACK.pop()
    if _STACK:
        _STACK[-1] |= deps  # a nested group's reach is its parent's too; only the top level is selectable
        return
    _RECORDS[name] = {"deps": sorted(deps), "secs": round(secs, 2)} if ok else None


def digest(rel: str) -> str | None:
    path = ROOT / rel
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def load(store: Path | None = None) -> dict | None:
    path = store or store_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("schema") == SCHEMA else None


def save(store: Path | None = None) -> int:
    """Merge this process's records into the map: a passing group's bytes recorded, a failed group's dropped.
    Hashed at save, after every plant is restored. Written whole and renamed, so a reader never sees half.
    Bounded: drop stale groups (no longer in PLANTED_GROUPS) and prune if the store exceeds its byte cap."""
    if not _RECORDS:
        return 0
    path = store or store_path()
    data = load(path) or {"schema": SCHEMA, "groups": {}}
    from atlascore import ls_files  # noqa: PLC0415

    known = set(ls_files(ROOT, flags=("-co", "--exclude-standard")))  # tracked or addable: never .git or bytecode
    live = set(groups())  # only keep groups that still exist in PLANTED_GROUPS
    for name, rec in _RECORDS.items():
        if rec is None:
            data["groups"].pop(name, None)
        else:
            deps = {p: digest(p) for p in rec["deps"] if p in known}
            data["groups"][name] = {"deps": deps, "secs": rec["secs"]}
    # Drop stale groups that no longer exist in PLANTED_GROUPS
    for stale in set(data["groups"]) - live:
        data["groups"].pop(stale, None)
    # Bounded storage: if over cap, drop oldest groups (by secs, ascending) until under
    payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    if len(payload) > MAX_STORE_BYTES:
        ordered = sorted(data["groups"].items(), key=lambda item: item[1].get("secs", 0))
        while len(payload) > MAX_STORE_BYTES and ordered:
            oldest_name, _ = ordered.pop(0)
            data["groups"].pop(oldest_name, None)
            payload = json.dumps(data, indent=1, sort_keys=True).encode("utf-8")
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    count = len(_RECORDS)
    _RECORDS.clear()
    return count


def groups() -> tuple[str, ...]:
    """The one planted-group list the full suite runs."""
    from atlas_guards_test import PLANTED_GROUPS  # noqa: PLC0415

    return PLANTED_GROUPS


def select(names: tuple[str, ...], data: dict) -> dict[str, list[str]]:
    """Each selected group -> why: the dependencies whose bytes moved, or ["no passing record"]."""
    chosen: dict[str, list[str]] = {}
    for name in names:
        rec = (data.get("groups") or {}).get(name)
        if rec is None:
            chosen[name] = ["no passing record"]
            continue
        moved = [p for p, h in rec["deps"].items() if digest(p) != h]
        if moved:
            chosen[name] = moved
    return chosen


def changed_row(store: Path | None = None) -> dict:
    """`verify --changed`: run only the planted groups whose recorded dependencies changed. No map is NOT RUN."""
    row = {"id": "impact:groups", "argv": ["python", "scripts/impact.py", "run"], "mutates": True}
    data = load(store)
    if data is None:
        return row | {"verdict": "NOT RUN", "why": "no test-impact map: run the planted suite once in this clone"}
    names = groups()
    chosen = select(names, data)
    spared = sum((data["groups"].get(n) or {}).get("secs", 0) for n in names if n not in chosen)
    if not chosen:
        return row | {"verdict": "PASS", "calls": 0, "why": f"0 of {len(names)} planted groups load a changed file"}
    from verify import run_gate  # noqa: PLC0415

    done = run_gate(row | {"argv": [*row["argv"], *chosen]})
    lead = f"{len(chosen)} of {len(names)} groups ran ({', '.join(list(chosen)[:4])}); {round(spared)}s spared"
    return done | {"why": f"{lead}; {done['why']}" if done.get("why") else lead}


def run(names: list[str]) -> int:
    """The selected groups, under the planted suite's own locks and restore discipline; refresh their record."""
    if os.environ.get("THEA_READ_ONLY"):
        raise SystemExit("THEA_READ_ONLY is set: planted groups PLANT defects in tracked files — refused")
    unknown = sorted(set(names) - set(groups()))
    if unknown:
        raise SystemExit(f"impact: not a planted group: {unknown}; the groups are atlas_guards_test.PLANTED_GROUPS")
    import signal  # noqa: PLC0415
    import time  # noqa: PLC0415

    import atlas_test  # noqa: PLC0415
    import safeedit  # noqa: PLC0415
    from testgroups import run_group  # noqa: PLC0415

    _locks = (atlas_test.host_lock(), atlas_test.suite_lock())  # noqa: F841 — held to exit, as the suite holds them
    os.environ["THEA_SUITE_PID"] = str(os.getpid())
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    for line in safeedit.restore_leftovers(ROOT):
        print(f"  restored a plant a killed run left behind: {line}")
    start()
    began = time.perf_counter()
    for name in names:
        run_group(atlas_test, name, __import__(name).run)
    save()
    failures = getattr(atlas_test, "SUITE_ERRORS", [])
    print("\n".join(f"FAIL {f}" for f in failures))
    print(f"impact: {len(names) - len(failures)}/{len(names)} groups pass in {time.perf_counter() - began:.1f}s")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["run"] and argv[1:]:
        return run(argv[1:])
    if argv == ["select"]:
        data = load()
        if data is None:
            print("no test-impact map: run the planted suite once in this clone")
            return 2
        for name, why in select(groups(), data).items():
            print(f"{name:<22}{', '.join(why[:4])}")
        return 0
    print("usage: impact.py run <group>... | impact.py select")
    return 2


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):  # a script with no parser would RUN on --help
        print((__doc__ or sys.argv[0]).strip())
        sys.exit(0)
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.exit(main(sys.argv[1:]))
