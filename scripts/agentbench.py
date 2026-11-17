#!/usr/bin/env python3
"""Does an agent FINISH more real tasks with Headron? The arm every other bench here marks NOT RUN.

WHY (3.18.0). abtest and taskbench measure answers — the right command, the right checks — and a reviewer
said plainly what that leaves open: nothing here measured whether an agent completes a real change. This
does. Each task under benchmarks/agent/ is a small module with a planted bug and a test that fails because
of it. A headless agent gets a scratch copy and a tool allowance of read, edit and the task's own test
runner. Two arms, same model, same prompt:
  blind   the task alone
  headron    the task plus what `headron gate` prints for the file, and "done only when each exits 0"
SCORING IS AN EXIT CODE: the task's own test after the agent stops (solved), and Headron's gates on the
source (gates_clean). Cost is what the CLI reports — seconds, turns, tokens, dollars — null when absent.

WHAT IT DOES NOT PROVE: three small single-file tasks written in this repository, one model, one run each.
It is a sample, K is printed, and a difference of one task is noise.

  python scripts/agentbench.py [--model haiku] [--record]     spends 2 agent runs per task
"""

from __future__ import annotations

import json
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from atlascore import ROOT, atlas, text_of

TASKS = ROOT / "benchmarks" / "agent"
TIMEOUT = 300
TOOLS = "Read,Edit,Write,Bash(python3 -m pytest:*),Bash(ruff format:*),Bash(python3 -c:*)"


def gate_lines(task: str, source: str) -> list[list[str]]:
    """What `headron gate` prints for the file, with the path rewritten to the scratch copy's."""
    from agentpolicy import required_gates  # noqa: PLC0415
    from atlas import gate_record  # noqa: PLC0415

    rel = f"benchmarks/agent/{task}/{source}"
    rows = [gate_record(rel, g)["argv"] for g in required_gates({"change_class": "source_change"})]
    return [[source if a == rel else a for a in argv] for argv in rows if argv]


def run(task: str, arm: str, model: str) -> dict:
    spec = json.loads(text_of(TASKS / task / "task.json"))
    gates = [g for g in gate_lines(task, spec["source"]) if g[0] != "pytest"]
    prompt = spec["prompt"]
    if arm == "headron_small":
        from knowledge import TIERS  # noqa: PLC0415

        arm_extra = "\n".join(TIERS["small"])
    else:
        arm_extra = ""
    if arm in ("headron", "headron_small"):
        prompt += (
            "\n\nHeadron, this repository's verification contract, says these commands prove a change to "
            f"{spec['source']}:\n"
            + "\n".join(shlex.join(g) for g in gates + [spec["test"]])
            + "\nRun them. You are done only when every one exits 0."
            + (f"\n{arm_extra}" if arm_extra else "")
        )
    with tempfile.TemporaryDirectory() as work:
        for f in (TASKS / task).iterdir():
            if f.is_file() and f.name != "task.json":
                shutil.copy(f, work)
        start = time.monotonic()
        try:
            done = subprocess.run(
                [
                    "claude",
                    "-p",
                    "--output-format",
                    "json",
                    "--model",
                    model,
                    "--setting-sources",
                    "",  # noqa: S607
                    "--permission-mode",
                    "acceptEdits",
                    "--allowedTools",
                    TOOLS,
                ],
                input=prompt,
                cwd=work,
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                check=False,
            )
            out: dict[str, Any] = json.loads(done.stdout or "{}")
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            out = {"is_error": True}
        seconds = round(time.monotonic() - start, 1)
        solved = subprocess.run(spec["test"], cwd=work, capture_output=True, timeout=120, check=False).returncode == 0
        clean = all(
            subprocess.run(g, cwd=work, capture_output=True, timeout=120, check=False).returncode == 0
            for g in gates
            if shutil.which(g[0])
        )
    usage = out.get("usage") or {}
    return {
        "solved": solved,
        "gates_clean": clean,
        "seconds": seconds,
        "turns": out.get("num_turns"),
        "tokens": (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)) if usage else None,
        "cost_usd": out.get("total_cost_usd"),
        "agent_error": bool(out.get("is_error")),
    }


def missing_runners(tasks: list[str]) -> list[str]:
    """Test runners (`python -m <module>`) that cannot start here: a task test that cannot run can never pass."""
    missing: set[str] = set()
    for task in tasks:
        test = json.loads(text_of(TASKS / task / "task.json"))["test"]
        probe = "import importlib.util,sys; sys.exit(importlib.util.find_spec(sys.argv[1]) is None)"
        if (
            test[1:2] == ["-m"]
            and subprocess.run([test[0], "-c", probe, test[2]], capture_output=True, timeout=60, check=False).returncode
        ):
            missing.add(f"{test[0]} -m {test[2]}")
    return sorted(missing)


# Each test_* function in the scratch copy, called directly: no runner, so a missing pytest reads as an error, never a fail
_PROBE = """
import importlib, json, pathlib, sys
sys.path.insert(0, ".")
out = {}
for f in sorted(pathlib.Path(".").glob("test_*.py")):
    try:
        mod = importlib.import_module(f.stem)
    except BaseException as exc:
        out[f.stem] = "error:" + type(exc).__name__
        continue
    for name in sorted(n for n in dir(mod) if n.startswith("test_")):
        try:
            getattr(mod, name)()
            out[name] = "pass"
        except AssertionError:
            out[name] = "assert"
        except BaseException as exc:
            out[name] = "error:" + type(exc).__name__
print(json.dumps(out))
"""
PLANT_SEEDS = range(32)  # PYTHONHASHSEED values: a plant whose verdict hangs on set order passes some of them


def test_outcomes(task: str, source_text: str | None = None, seed: int = 0) -> dict[str, str]:
    """{test name: pass | assert | error:<Type>} for the task's tests against its plant, or against `source_text`."""
    spec = json.loads(text_of(TASKS / task / "task.json"))
    with tempfile.TemporaryDirectory() as work:
        for f in (TASKS / task).iterdir():
            if f.is_file() and f.name != "task.json":
                shutil.copy(f, work)
        if source_text is not None:
            (pathlib.Path(work) / spec["source"]).write_text(source_text, encoding="utf-8")
        done = subprocess.run(
            [sys.executable, "-I", "-c", _PROBE],
            cwd=work,
            env={"PYTHONHASHSEED": str(seed), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    try:
        return json.loads(done.stdout or "{}")
    except json.JSONDecodeError:
        return {"probe": f"error:exit {done.returncode}"}


def plant_errors(tasks: list[str]) -> list[str]:
    """A plant must FAIL its own test, by assertion, on every hash seed: a test the plant passes hands out free solves."""
    errors = []
    for task in tasks:
        for seed in PLANT_SEEDS:
            got = test_outcomes(task, seed=seed)
            broken = sorted(n for n, v in got.items() if v.startswith("error"))
            if broken or not got:
                errors.append(f"{task}: the plant's tests do not run (seed {seed}): {broken or 'no test_* found'}")
                break
            if "assert" not in got.values():
                errors.append(f"{task}: the plant PASSES its own test (seed {seed}), so solved is free")
                break
    return errors


EXTERNAL_RECORDS = "benchmarks/freebench-*.json"  # cross-model runs made outside this script, kept as reported


def record_errors(doc: dict[str, Any]) -> list[str]:
    """What an external cross-model record must hold before any of its numbers is read (the first freebench run):
    a declared error policy wherever a lane errored, the served model for a router-chain lane, no score
    for a lane the source could not score, and no winner, since one run per lane does not order a tie."""
    errors: list[str] = []
    if doc.get("obtained_by") != "reported_external" or not doc.get("raw_records"):
        errors.append("an external record declares obtained_by: reported_external and where its raw records are")
    if not doc.get("arm"):
        errors.append("an external record declares its arm: blind numbers rank models, not Headron's effect")
    blob = json.dumps(doc).lower()
    for word in ("winner", "champion"):
        if f'"{word}' in blob:
            errors.append(f"a key names a {word}: one run per lane does not order lanes inside its noise")
    for rnd, row in (doc.get("rounds") or {}).items():
        tasks = row.get("tasks")
        for lane, got in (row.get("lanes") or {}).items():
            where = f"{rnd}/{lane}"
            score, records, errs = got.get("score"), got.get("records"), got.get("errors")
            if not isinstance(score, (int, float)) or not 0 <= score <= 1:
                errors.append(f"{where}: no score in [0, 1]; a lane the source could not score belongs in `excluded`")
            if not (isinstance(records, int) and isinstance(errs, int) and 0 <= errs <= records == tasks):
                errors.append(f"{where}: records {records} and errors {errs} must be counted over all {tasks} tasks")
            elif errs and not doc.get("error_policy"):
                errors.append(f"{where}: {errs} errored records and no error_policy, so a 0 may be a non-answer")
            if lane.startswith("freeroute-") and not got.get("resolved_model"):
                errors.append(f"{where}: a router-chain lane names no resolved_model, so its score has no model")
    return errors


SCREEN_RECORDS = "benchmarks/screen-*.json"  # cross-model screens measured here by multimodel_bench, kept as measured


def screen_record_errors(doc: dict[str, Any]) -> list[str]:
    """What a measured screen record must hold before any of its numbers is read (the universal census screen):
    every lane it scores ANSWERED (a lane with no answer sits in `excluded` with its cause, never as 0% or N/A),
    each rate carries its interval, tokens are counted or "unmeasured" (never a 0 standing for no usage), the
    error samples hold no account id, request hash or date, and nothing is crowned inside one run's noise."""
    errors: list[str] = []
    if doc.get("obtained_by") != "measured_live" or not doc.get("raw_records"):
        errors.append("a screen record declares obtained_by: measured_live and where its raw records are")
    if doc.get("repeats") != 1 or not isinstance(doc.get("tasks"), int):
        errors.append("a screen record declares repeats: 1 and its task count, so no reader takes a rate for an edge")
    blob = json.dumps(doc)
    for word in ("winner", "champion"):
        if f'"{word}' in blob.lower():
            errors.append(f"a key names a {word}: one run per lane does not order lanes inside its noise")
    if (
        re.search(r"[0-9a-f]{32,}", blob)
        or re.search(r"\d{4}-\d{2}-\d{2}", blob)
        or re.search(r"user_[A-Za-z0-9]{6,}", blob)
    ):
        errors.append("a vendor body kept a request hash, an account id or a date: the public record carries none")
    lanes, excluded = doc.get("lanes") or {}, doc.get("excluded") or {}
    if not lanes:
        errors.append("a screen record scores no lane: it would prove nothing")
    for lane, got in lanes.items():
        if lane in excluded:
            errors.append(f"{lane}: both scored and excluded")
        arms = got.get("arms") or {}
        if not arms:
            errors.append(f"{lane}: no answered arm; a lane with no answer belongs in `excluded`")
        for arm, a in arms.items():
            where, n, c, ci = f"{lane}/{arm}", a.get("answered"), a.get("correct"), a.get("ci95")
            if not (isinstance(n, int) and isinstance(c, int) and 0 <= c <= n and n > 0):
                errors.append(f"{where}: correct {c} of answered {n}; an arm with no answer is left out, never 0%")
                continue
            if not (isinstance(ci, list) and len(ci) == 2 and 0 <= ci[0] <= c / n <= ci[1] <= 1):
                errors.append(f"{where}: no 95% interval around {c}/{n}; a rate without one reads as a ranking")
            tok = a.get("tokens")
            if tok != "unmeasured" and not (isinstance(tok, int) and tok > 0):
                errors.append(f'{where}: tokens {tok!r}; an answer with no usage is "unmeasured", never 0')
        pair = got.get("paired") or {}
        cap = min((a.get("answered") or 0 for a in arms.values()), default=0) if len(arms) == 2 else 0
        n = pair.get("n")
        if not (isinstance(n, int) and 0 <= n <= cap and all(0 <= pair.get(k, -1) <= n for k in ("blind", "headron"))):
            errors.append(
                f"{lane}: paired {pair} exceeds what both arms answered ({cap}); a pair is one task, both answered"
            )
    total = doc.get("paired") or {}
    for k in ("n", "blind", "headron"):
        if total.get(k) != sum((g.get("paired") or {}).get(k, 0) for g in lanes.values()):
            errors.append(f"paired {k} is not the sum of its lanes: the headline pair is counted, never typed")
    for lane, why in excluded.items():
        if not (isinstance(why, dict) and why.get("reason")) or {"score", "correct", "ci95"} & set(why):
            errors.append(f"{lane}: an excluded lane names its reason and carries no number")
    return errors


def main(argv: list[str]) -> int:
    model = argv[argv.index("--model") + 1] if "--model" in argv else "haiku"
    if not shutil.which("claude"):
        print("agentbench: NOT RUN — no `claude` CLI on this machine; nothing is simulated in its place")
        return 2
    tasks = sorted(p.name for p in TASKS.iterdir() if (p / "task.json").is_file())
    only = argv[argv.index("--tasks") + 1].split(",") if "--tasks" in argv else tasks
    arms = argv[argv.index("--arms") + 1].split(",") if "--arms" in argv else ["blind", "headron"]
    tasks = [t for t in tasks if t in only]
    if missing := missing_runners(tasks):
        # a runner that is absent fails every task alike, so the bench would record "0 solved" for the machine, not the agent
        print(f"agentbench: NOT RUN — the task test runner cannot start here: {', '.join(missing)}; nothing spent")
        return 2
    if bad := plant_errors(tasks):
        # ratelimit's plant passed its own test in the first external freebench run: every arm "solved" it without a change
        print(f"agentbench: NOT RUN — a task cannot score a fix: {'; '.join(bad)}; nothing spent")
        return 2
    results = {t: {arm: run(t, arm, model) for arm in arms} for t in tasks}
    for arm in arms:
        rows = [results[t][arm] for t in tasks]
        print(
            f"{arm:<6} solved {sum(r['solved'] for r in rows)}/{len(rows)} · gates clean {sum(r['gates_clean'] for r in rows)}/{len(rows)}"
            f" · {sum(r['seconds'] for r in rows):.0f}s · ${sum(r['cost_usd'] or 0 for r in rows):.3f}"
        )
    print(f"K = {len(tasks)} tasks × {len(arms)} arms, one run each, model {model} — a sample, not an edge")
    errored = [f"{t}/{arm}" for t in tasks for arm in arms if results[t][arm]["agent_error"]]
    if errored:
        # an agent that never answered is not an agent that failed: its 0 solved and its clean gates (nothing was edited) say nothing
        print(
            f"agentbench: NOT RUN for {len(errored)} of {len(tasks) * len(arms)} runs (agent API error): {', '.join(errored)}; nothing recorded"
        )
        return 2
    if "--record" in argv and arms == ["blind", "headron"]:
        (ROOT / "benchmarks" / "agent-latest.json").write_text(
            json.dumps(
                {
                    "_why": "agentbench.py: real bug-fix tasks, solved = the task's own test exits 0 after the agent stops",
                    "measured_at": str(atlas().get("version")),
                    "model": model,
                    "arms": {
                        arm: {
                            "solved": sum(results[t][arm]["solved"] for t in tasks),
                            "gates_clean": sum(results[t][arm]["gates_clean"] for t in tasks),
                            "attempted": len(tasks),
                        }
                        for arm in ("blind", "headron")
                    },
                    "tasks": results,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):  # a script with no parser would RUN on --help
        print((__doc__ or sys.argv[0]).strip())
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
