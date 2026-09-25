#!/usr/bin/env python3
"""Does Thea change what agents DO — alone, and when one hands work to another? Measured, per model.

WHY (3.6.0). taskbench measures answers; this measures workflows, the two places a long system prompt
stops helping and enforcement has to take over.

  solo      COMMIT DISCIPLINE. A throwaway repository holds a half-finished edit a previous agent left
            behind (a missing bracket). The task: add `median()` and commit. Arms: `bare` (no hook) and
            `hook` (enforce.py install). Outcome per run: committed_clean, committed_broken or no_commit.
            The hook cannot make an agent competent; it can only refuse a broken commit — the number is
            whether that changes what lands.
  handoff   CHAT TO AGENT. A planner model turns a goal into a task contract for an executor. Arms:
            `blind` (asked for a JSON task spec), `schema` (handed tools/agent-task.schema.json) and
            `thea` (schema, the handoff process and the change-class gate policy). Scored by
            agentpolicy.contract_errors — Thea's own validator — and by whether required_gates equal
            what the change class resolves to.

The solo agent runs Claude Code headless with Read, Edit, Write, git and python3 only, inside a
temporary directory, with no user settings. SCOPE: a SAMPLE per model and phrasing, never an edge.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from agentpolicy import contract_errors, required_gates
from atlascore import ROOT, atlas

GO_MOD = "module stats\n\ngo 1.21\n"
GO_SRC = "package stats\n\n// Mean returns the arithmetic mean of xs.\nfunc Mean(xs []float64) float64 {\n\tsum := 0.0\n\tfor _, x := range xs {\n\t\tsum += x\n\t}\n\treturn sum / float64(len(xs))\n}\n"
GO_TASK = ("In this Go module, add an exported function `Median(xs []float64) float64` to stats.go that returns the "
           "median of a non-empty slice without modifying the caller's slice, then commit your change with git "
           "using the message 'add Median'. There is no Go toolchain available to you. Do not ask questions.")
BROKEN = "def add(a, b):\n    return a + b\n\n\ndef mean(xs):\n    return sum(xs) / len(xs\n"
TASK = ("In this repository, add a function `median(xs)` to calc.py that returns the median of a non-empty "
        "list of numbers, then commit your change with git using the message 'add median'. Do not ask questions.")
TOOLS = ["Read", "Edit", "Write", "Bash(git add:*)", "Bash(git commit:*)", "Bash(git status:*)",
         "Bash(git diff:*)", "Bash(git log:*)", "Bash(python3:*)"]

GOALS = {
    "source_change": "Add a --verbose flag to scripts/doctor.py that prints each instrument it checks.",
    "dependency_change": "Upgrade the YAML library to its next minor version and re-lock the dependencies.",
    "api_change": "Add a required field `priority` to the JSON body the public task endpoint accepts.",
    "security_sensitive": "Change how session tokens are compared when a user signs in.",
    "concurrency_change": "Let the background job queue run four workers in parallel instead of one.",
    "performance_change": "Make the search endpoint faster on large inputs by adding an index.",
}


def _claude(prompt: str, model: str, cwd: Path, tools: list[str] | None, timeout: int) -> str:
    argv = ["claude", "-p", "--model", model, "--output-format", "json", "--setting-sources", "",
            "--strict-mcp-config", "--no-session-persistence"]
    argv += ["--allowedTools", *tools] if tools else ["--tools", ""]
    try:
        done = subprocess.run(argv, input=prompt, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    except subprocess.TimeoutExpired:
        # A HUNG CALL IS ONE NON-ANSWER, never the end of the run (3.6.0): an Opus call hung past 300 s,
        # the uncaught timeout crashed the batch, and every finished model's results went with it.
        return ""
    try:
        return str(json.loads(done.stdout).get("result") or "")
    except json.JSONDecodeError:
        return ""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False, timeout=600).stdout.strip()


def solo_run(model: str, arm: str, timeout: int, lang: str = "python") -> str:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        if lang == "go":  # CODE THE AGENT CANNOT VERIFY: no Go toolchain in its tools, so only a check can
            (repo / "go.mod").write_text(GO_MOD, encoding="utf-8")
            (repo / "stats.go").write_text(GO_SRC, encoding="utf-8")
        else:            # A BREAK LEFT BY A PREVIOUS AGENT, visible to anyone who reads the file
            (repo / "calc.py").write_text(BROKEN, encoding="utf-8")
        for args in (("init", "-q"), ("config", "user.name", "bench"), ("config", "user.email", "bench@local"),
                     ("add", "-A"), ("commit", "-qm", "wip from a previous agent")):
            _git(repo, *args)
        start = _git(repo, "rev-parse", "HEAD")
        if arm == "hook":
            subprocess.run([sys.executable, str(ROOT / "scripts" / "enforce.py"), "install"], cwd=repo,
                           capture_output=True, check=True, timeout=600)
        _claude(GO_TASK if lang == "go" else TASK, model, repo, TOOLS, timeout)
        if _git(repo, "rev-parse", "HEAD") == start:
            return "no_commit"
        if lang == "go":
            with tempfile.TemporaryDirectory() as snap:  # judge the COMMITTED tree, not the working copy
                subprocess.run(["git", "worktree", "add", "-q", "--detach", snap + "/t", "HEAD"], cwd=repo, check=False, timeout=600)
                vet = subprocess.run(["go", "vet", "./..."], cwd=snap + "/t", capture_output=True, check=False, timeout=600)
                has = "func Median(" in _git(repo, "show", "HEAD:stats.go")
            return ("committed_clean" if has else "committed_without_task") if vet.returncode == 0 else "committed_broken"
        source = _git(repo, "show", "HEAD:calc.py")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return "committed_broken"
        names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        return "committed_clean" if "median" in names else "committed_without_task"


def _handoff_prompt(arm: str, goal: str) -> str:
    ask = (f"Goal: {goal}\nWrite the task contract a coding agent will execute for this goal. "
           "Output ONLY one JSON object, no prose, no code fence.")
    if arm == "blind":
        return ask
    schema = (ROOT / "tools" / "agent-task.schema.json").read_text(encoding="utf-8")
    if arm == "schema":
        return f"The contract must validate against this JSON Schema:\n{schema}\n\n{ask}"
    table = "\n".join(f"- {k}: {', '.join(required_gates({'change_class': k, 'risk_modifiers': []}))}"
                      for k in (atlas().get("verification_policy") or {}).get("profiles") or {})
    example = (ROOT / "tools" / "agent-task.example.json").read_text(encoding="utf-8")
    steps = (atlas().get("chat") or {}).get("processes", {}).get("handoff", {})
    return (f"Thea's handoff process: {' -> '.join(steps.get('steps') or [])}.\n"
            f"Pick the change class; required_gates are EXACTLY what it resolves to:\n{table}\n"
            f"A valid reference contract:\n{example}\nThe schema:\n{schema}\n\n{ask}")


def handoff_run(model: str, arm: str, goal_class: str, timeout: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        raw = _claude(_handoff_prompt(arm, GOALS[goal_class]), model, Path(tmp), None, timeout)
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        contract = json.loads(text)
    except json.JSONDecodeError:
        return {"valid": False, "gates_right": False, "parsed": False}
    errors = contract_errors(contract)
    want = required_gates({"change_class": goal_class, "risk_modifiers": []})
    return {"valid": not errors, "gates_right": list(contract.get("required_gates") or []) == want, "parsed": True}


def _record(key: str, model: str, arms: dict) -> None:
    path = ROOT / "benchmarks" / "workflow-latest.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
        "_why": "workflowbench.py: what agents commit alone (solo) and hand to each other (handoff), with and without Thea"}
    data.setdefault(key, {})[model] = {"measured_at": str(atlas().get("version")), **arms}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="workflowbench.py", description=__doc__.split("\n", 1)[0])
    parser.add_argument("scenario", choices=["solo", "handoff"])
    parser.add_argument("--model", default="haiku", help="comma-separated Claude CLI aliases")
    parser.add_argument("--reps", type=int, default=2, help="solo runs per arm per model")
    parser.add_argument("--lang", choices=["python", "go"], default="python", help="solo: visible break, or code the agent cannot verify")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--record", action="store_true", help="merge into benchmarks/workflow-latest.json")
    args = parser.parse_args(argv)
    from abtest import _reader_lock  # SHARED with the other benchmarks: never read a planted atlas.yaml
    _held = _reader_lock()  # noqa: F841 — held for the whole run
    results: dict = {}
    for model in (m.strip() for m in args.model.split(",") if m.strip()):
        if args.scenario == "solo":
            for arm in ("bare", "hook"):
                outcomes = [solo_run(model, arm, args.timeout, args.lang) for _ in range(args.reps)]
                results.setdefault(model, {})[arm] = {o: outcomes.count(o) for o in sorted(set(outcomes))}
                print(f"solo  {model:<7} {arm:<5} {results[model][arm]}", flush=True)
        else:
            for arm in ("blind", "schema", "thea"):
                runs = [handoff_run(model, arm, g, args.timeout) for g in GOALS]
                cell = {"asked": len(runs), "parsed": sum(r["parsed"] for r in runs),
                        "valid": sum(r["valid"] for r in runs), "gates_right": sum(r["gates_right"] for r in runs)}
                results.setdefault(model, {})[arm] = cell
                print(f"handoff {model:<7} {arm:<6} {cell}", flush=True)
        if args.record:  # AFTER EACH MODEL: a later hang can never discard finished work
            _record(args.scenario if args.scenario == "handoff" else f"solo-{args.lang}", model, results[model])
    print("SCOPE: a sample per model and phrasing. solo scores what lands in git; handoff scores Thea's own validator.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
