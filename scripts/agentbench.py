#!/usr/bin/env python3
"""Does an agent FINISH more real tasks with Thea? The arm every other bench here marks NOT RUN.

WHY (3.18.0). abtest and taskbench measure answers — the right command, the right checks — and a reviewer
said plainly what that leaves open: nothing here measured whether an agent completes a real change. This
does. Each task under benchmarks/agent/ is a small module with a planted bug and a test that fails because
of it. A headless agent gets a scratch copy and a tool allowance of read, edit and the task's own test
runner. Two arms, same model, same prompt:
  blind   the task alone
  thea    the task plus what `thea gate` prints for the file, and "done only when each exits 0"
SCORING IS AN EXIT CODE: the task's own test after the agent stops (solved), and Thea's gates on the
source (gates_clean). Cost is what the CLI reports — seconds, turns, tokens, dollars — null when absent.

WHAT IT DOES NOT PROVE: three small single-file tasks written in this repository, one model, one run each.
It is a sample, K is printed, and a difference of one task is noise.

  python scripts/agentbench.py [--model haiku] [--record]     spends 2 agent runs per task
"""
from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

from atlascore import ROOT, atlas

TASKS = ROOT / "benchmarks" / "agent"
TIMEOUT = 300
TOOLS = "Read,Edit,Write,Bash(python3 -m pytest:*),Bash(ruff format:*),Bash(python3 -c:*)"


def gate_lines(task: str, source: str) -> list[list[str]]:
    """What `thea gate` prints for the file, with the path rewritten to the scratch copy's."""
    from agentpolicy import required_gates  # noqa: PLC0415
    from atlas import gate_record  # noqa: PLC0415
    rel = f"benchmarks/agent/{task}/{source}"
    rows = [gate_record(rel, g)["argv"] for g in required_gates({"change_class": "source_change"})]
    return [[source if a == rel else a for a in argv] for argv in rows if argv]


def run(task: str, arm: str, model: str) -> dict:
    spec = json.loads((TASKS / task / "task.json").read_text(encoding="utf-8"))
    gates = [g for g in gate_lines(task, spec["source"]) if g[0] != "pytest"]
    prompt = spec["prompt"]
    if arm == "thea":
        prompt += ("\n\nThea, this repository's verification contract, says these commands prove a change to "
                   f"{spec['source']}:\n" + "\n".join(shlex.join(g) for g in gates + [spec["test"]])
                   + "\nRun them. You are done only when every one exits 0.")
    with tempfile.TemporaryDirectory() as work:
        for f in (TASKS / task).iterdir():
            if f.is_file() and f.name != "task.json":
                shutil.copy(f, work)
        start = time.monotonic()
        try:
            done = subprocess.run(["claude", "-p", "--output-format", "json", "--model", model, "--setting-sources", "",  # noqa: S607
                                   "--permission-mode", "acceptEdits", "--allowedTools", TOOLS],
                                  input=prompt, cwd=work, capture_output=True, text=True, timeout=TIMEOUT, check=False)
            out = json.loads(done.stdout or "{}")
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            out = {"is_error": True}
        seconds = round(time.monotonic() - start, 1)
        solved = subprocess.run(spec["test"], cwd=work, capture_output=True, timeout=120, check=False).returncode == 0
        clean = all(subprocess.run(g, cwd=work, capture_output=True, timeout=120, check=False).returncode == 0
                    for g in gates if shutil.which(g[0]))
    usage = out.get("usage") or {}
    return {"solved": solved, "gates_clean": clean, "seconds": seconds, "turns": out.get("num_turns"),
            "tokens": (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)) if usage else None,
            "cost_usd": out.get("total_cost_usd"), "agent_error": bool(out.get("is_error"))}


def main(argv: list[str]) -> int:
    model = argv[argv.index("--model") + 1] if "--model" in argv else "haiku"
    if not shutil.which("claude"):
        print("agentbench: NOT RUN — no `claude` CLI on this machine; nothing is simulated in its place")
        return 2
    tasks = sorted(p.name for p in TASKS.iterdir() if (p / "task.json").is_file())
    results = {t: {arm: run(t, arm, model) for arm in ("blind", "thea")} for t in tasks}
    for arm in ("blind", "thea"):
        rows = [results[t][arm] for t in tasks]
        print(f"{arm:<6} solved {sum(r['solved'] for r in rows)}/{len(rows)} · gates clean {sum(r['gates_clean'] for r in rows)}/{len(rows)}"
              f" · {sum(r['seconds'] for r in rows):.0f}s · ${sum(r['cost_usd'] or 0 for r in rows):.3f}")
    print(f"K = {len(tasks)} tasks × 2 arms, one run each, model {model} — a sample, not an edge")
    if "--record" in argv:
        (ROOT / "benchmarks" / "agent-latest.json").write_text(json.dumps({
            "_why": "agentbench.py: real bug-fix tasks, solved = the task's own test exits 0 after the agent stops",
            "measured_at": str(atlas().get("version")), "model": model,
            "arms": {arm: {"solved": sum(results[t][arm]["solved"] for t in tasks),
                           "gates_clean": sum(results[t][arm]["gates_clean"] for t in tasks), "attempted": len(tasks)}
                     for arm in ("blind", "thea")},
            "tasks": results}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
