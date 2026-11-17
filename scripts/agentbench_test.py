#!/usr/bin/env python3
"""Planted case: an agent that never answered is NOT RUN, never a 0 solved that gets recorded."""

from __future__ import annotations

import contextlib
import io
import pathlib
import tempfile
from collections.abc import Callable
from types import ModuleType


def agentbench_case(module: ModuleType) -> None:
    """agentbench printed 'solved 0/4 · gates clean 4/4 · $0.000' for four API errors and --record would have kept it."""
    import agentbench

    dead = {
        "solved": False,
        "gates_clean": True,
        "seconds": 5.0,
        "turns": 0,
        "tokens": 0,
        "cost_usd": 0,
        "agent_error": True,
    }
    saved_run, saved_which, saved_root = agentbench.run, agentbench.shutil.which, agentbench.ROOT
    agentbench.run = lambda task, arm, model: dict(dead)
    agentbench.shutil.which = lambda name: "/bin/true"
    out = io.StringIO()
    with tempfile.TemporaryDirectory() as scratch:
        # the unfixed code wrote its zeros to ROOT/benchmarks/agent-latest.json: a plant must never reach the real record
        (pathlib.Path(scratch) / "benchmarks").mkdir()
        agentbench.ROOT = pathlib.Path(scratch)
        try:
            with contextlib.redirect_stdout(out):
                code = agentbench.main(["--record"])
        finally:
            agentbench.run, agentbench.shutil.which, agentbench.ROOT = saved_run, saved_which, saved_root
        recorded = (pathlib.Path(scratch) / "benchmarks" / "agent-latest.json").exists()
    if code != 2 or "NOT RUN" not in out.getvalue() or recorded:
        raise SystemExit(
            f"FAIL agentbench read an API-errored run as a result: exit {code}, recorded={recorded}: {out.getvalue()!r}"
        )
    module.CASES.append(
        (
            "an agent run that errored is NOT RUN at exit 2 and nothing is recorded",
            "a dead API scored as a clean 0 solved, and --record kept it as the benchmark",
        )
    )
    print("  ok    an errored agent run is NOT RUN, never a recorded 0")


def runner_case(module: ModuleType) -> None:
    """The VPS had no pytest: every task test failed, and agentbench printed 'solved 0/4' for both arms."""
    import json

    import agentbench

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "t").mkdir()
        spec = {"prompt": "p", "source": "s.py", "test": ["python3", "-m", "no_such_runner_module_xyz", "-q"]}
        (root / "t" / "task.json").write_text(json.dumps(spec), encoding="utf-8")
        real = agentbench.TASKS
        agentbench.TASKS = root
        try:
            absent = agentbench.missing_runners(["t"])
            spec["test"] = ["python3", "-m", "json.tool", "--help"]
            (root / "t" / "task.json").write_text(json.dumps(spec), encoding="utf-8")
            present = agentbench.missing_runners(["t"])
        finally:
            agentbench.TASKS = real
    if absent != ["python3 -m no_such_runner_module_xyz"] or present:
        raise SystemExit(f"FAIL agentbench runner preflight: absent={absent} present={present}")
    module.CASES.append(
        (
            "a task test runner that cannot start is NOT RUN before any agent is spent",
            "a missing pytest scored every task 0 and the 0 read as the agent's",
        )
    )
    print("  ok    a missing task test runner is NOT RUN, never a 0 solved")


# Reference fixes live HERE, never in benchmarks/agent/<task>/: agentbench copies every file there into the agent's scratch
REFERENCE = {
    "dedupe": "def dedupe(items):\n    return list(dict.fromkeys(items))\n",
    "duration": (
        "import re\n\n\ndef seconds(text):\n    units = {'h': 3600, 'm': 60, 's': 1}\n"
        "    return sum(int(n) * units[u] for n, u in re.findall(r'(\\d+)([hms])', text))\n"
    ),
    "window": "def window(xs, n):\n    return [xs[i : i + n] for i in range(len(xs) - n + 1)]\n",
}


def plant_case(module: ModuleType) -> None:
    """The first external freebench run: ratelimit's plant passed its own test, and dedupe's passed on 8 of 41 hash seeds — free solves."""
    import json

    import agentbench

    tasks = sorted(p.name for p in agentbench.TASKS.iterdir() if (p / "task.json").is_file())
    if sorted(REFERENCE) != tasks:
        raise SystemExit(
            f"FAIL every agent task needs a reference fix here: tasks={tasks} references={sorted(REFERENCE)}"
        )
    if bad := agentbench.plant_errors(tasks):
        raise SystemExit(f"FAIL an agent task's plant does not fail its own test: {bad}")
    for task in tasks:
        for seed in range(4):  # a reference fix is order-free; the plants carry the full seed sweep
            got = agentbench.test_outcomes(task, REFERENCE[task], seed)
            if not got or set(got.values()) != {"pass"}:
                raise SystemExit(f"FAIL {task}: the reference fix does not pass its test (seed {seed}): {got}")
    # the plant: a task whose test the unchanged source already passes, and one whose plant only fails on some seeds
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for name, source in (
            ("free", "def f():\n    return 1\n"),
            ("flaky", "def f():\n    return list({'b', 'a', 'c'})\n"),
        ):
            (root / name).mkdir()
            (root / name / "task.json").write_text(
                json.dumps({"prompt": "p", "source": "m.py", "test": []}), encoding="utf-8"
            )
            (root / name / "m.py").write_text(source, encoding="utf-8")
        (root / "free" / "test_m.py").write_text(
            "from m import f\n\n\ndef test_f():\n    assert f() == 1\n", encoding="utf-8"
        )
        (root / "flaky" / "test_m.py").write_text(
            "from m import f\n\n\ndef test_f():\n    assert f() == ['b', 'a', 'c']\n", encoding="utf-8"
        )
        real = agentbench.TASKS
        agentbench.TASKS = root
        try:
            caught = agentbench.plant_errors(["free", "flaky"])
        finally:
            agentbench.TASKS = real
    if len(caught) != 2 or not all("PASSES its own test" in c for c in caught):
        raise SystemExit(f"FAIL a plant that passes its own test, always or on some seeds, was not refused: {caught}")
    module.CASES.append(
        (
            "every agent task's plant fails its test by assertion on every hash seed, and its reference fix passes",
            "a plant that already passed its test scored every arm solved, so the bench counted free points",
        )
    )
    print("  ok    every agent-task plant fails its own test, and a reference fix passes it")


def record_case(module: ModuleType) -> None:
    """The first external freebench run scored errors as 0, named five router chains that served one model as five
    lanes, and crowned a winner inside its own noise: every kept external record is held to agentbench."""
    import copy
    import json

    import agentbench
    from atlascore import ROOT

    kept = sorted(ROOT.glob(agentbench.EXTERNAL_RECORDS))
    if not kept:
        raise SystemExit(f"FAIL no external record matches {agentbench.EXTERNAL_RECORDS}: the case would prove nothing")
    for path in kept:
        if bad := agentbench.record_errors(json.loads(path.read_text(encoding="utf-8"))):
            raise SystemExit(f"FAIL {path.name}: {bad}")
    base = json.loads(kept[0].read_text(encoding="utf-8"))
    rnd, lane = next(
        (r, n)
        for r, row in base["rounds"].items()
        for n, g in row["lanes"].items()
        if g.get("resolved_model") and g["errors"]
    )

    def planted(change: Callable[[dict, dict], object]) -> list[str]:
        doc = copy.deepcopy(base)
        change(doc, doc["rounds"][rnd]["lanes"][lane])
        return agentbench.record_errors(doc)

    plants = {
        "no error_policy": (lambda d, g: d.pop("error_policy"), "no error_policy"),
        "no resolved_model": (lambda d, g: g.pop("resolved_model"), "names no resolved_model"),
        "an N/A score": (lambda d, g: g.update(score=None), "no score in [0, 1]"),
        "a winner": (lambda d, g: d.update(winners={"main": lane}), "names a winner"),
        "a partial run": (lambda d, g: g.update(records=g["records"] - 1), "counted over all"),
    }
    for name, (change, needle) in plants.items():
        if not any(needle in e for e in planted(change)):
            raise SystemExit(f"FAIL an external record with {name} was not refused: {planted(change)}")
    module.CASES.append(
        (
            "an external cross-model record declares its error policy and each chain lane's served model, and names no winner",
            "errored records scored 0 and one model counted as five lanes, read as a ranking",
        )
    )
    print("  ok    an external cross-model record is refused without error policy, served model, or with a winner")


def run(module: ModuleType) -> None:
    for case in (agentbench_case, runner_case, plant_case, record_case):
        case(module)
