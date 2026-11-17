#!/usr/bin/env python3
"""One task through Connect -> Context -> Gates -> Receipt, with every declared gate's verdict as measured.

WHY. The first version wrote PASS for a gate it never ran (a tool off PATH, a gate no pack answers), for every
gate when execution was off, and for a fallback that lent one contract check's verdict to every gate, and its
receipt hashed the target's path, not its bytes. Its receipt then attested work nobody did. A gate that does not
run is NOT RUN with the reason; NOT RUN is never a pass (receipt.verdict_of), so such a workflow answers 2.

proves: each declared gate is run or reported NOT RUN with why; the verdict is receipt.verdict_of over those
  states; the receipt's inputs carry the target's sha256 and the git tree, so a substituted file or another tree
  gives another input_digest
does_not_prove: that the task was done (this runner makes no edit), who ran it (receipt_id is integrity, not
  authenticity), or that a gate checks what its name says
closed_by: scripts/workflow_runner_test.py, which plants execute off, a gate no tool answers, a tool off PATH,
  a FAIL gate, an edited target, and the CLI exit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import receipt as receipt_mod
from agentpolicy import required_gates
from agentrun import environment_fingerprint, workspace_report
from atlascore import atlas, route_for
from runtime import resolve

STATUS = {"PASS": "ok", "FAIL": "refused", "NOT RUN": "unknown"}


def target_inputs(task: str, target_path: str, agent: str) -> dict[str, Any]:
    """What the receipt binds: the target's bytes and the tree, not only its name. None when absent or no tree."""
    import obligations  # noqa: PLC0415

    target = Path(target_path)
    sha = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    return {"task": task, "path": target_path, "path_sha256": sha, "tree": obligations.tree(), "agent": agent}


def gate_rows(declared: list[dict[str, Any]], execute: bool) -> list[dict[str, Any]]:
    """One row per declared gate: run when it can, else NOT RUN with the reason. Never a PASS nobody measured."""
    from verify import run_declared_gates  # noqa: PLC0415

    rows: dict[str, dict[str, Any]] = {}
    runnable = []
    for record in declared:
        gate, argv = record["gate"], list(record.get("argv") or [])
        if not execute:
            rows[gate] = {"id": gate, "verdict": "NOT RUN", "why": "execution off (--no-execute)"}
        elif not argv:
            rows[gate] = {
                "id": gate,
                "verdict": "NOT RUN",
                "why": f"{record.get('state', 'absent')}: {record.get('why', '')}"[:200],
            }
        else:
            if shutil.which(argv[0]) is None and shutil.which("uvx") and argv[0] in ("ruff", "basedpyright"):
                argv = ["uvx", *argv]
            if shutil.which(argv[0]) is None:
                rows[gate] = {"id": gate, "verdict": "NOT RUN", "why": f"{argv[0]} is not on PATH"}
            else:
                runnable.append({"id": gate, "argv": argv, "mutates": False})
    for row in run_declared_gates(runnable, Path.cwd(), jobs=1) if runnable else []:
        rows[row["id"]] = {"id": row["id"], "verdict": row["verdict"], "why": row.get("why", "")}
    return [rows[record["gate"]] for record in declared]


def run_workflow(
    task: str, path: str | None = None, agent_name: str | None = None, execute: bool = True, as_json: bool = False
) -> tuple[dict[str, Any], int]:
    """Connect -> Context -> Gates -> Receipt. Exit 0 every gate PASS, 1 any FAIL, 2 any NOT RUN (verify.verdict_code)."""
    from atlas import gate_record  # noqa: PLC0415
    from verify import verdict_code  # noqa: PLC0415

    start_time = time.monotonic()
    target_path = path or "scripts/commands.py"
    target_route = route_for(target_path) or "unrouted"

    agent_info = resolve(agent_name)
    agent_display = agent_info.get("agent") if agent_info.get("agent") != "unknown" else (agent_name or "unknown")
    runtime_display = agent_info.get("runtime") if agent_info.get("runtime") != "unknown" else "unknown"
    env = environment_fingerprint()
    ws = workspace_report()
    if not as_json:
        print("=" * 78)
        print("HEADRON WORKFLOW")
        print("=" * 78)
        print(f"[1/4] CONNECT   agent: {agent_display} (runtime: {runtime_display})")

    planned_gates = required_gates({"change_class": "source_change", "task_profile": "default"})
    if not as_json:
        print(f"[2/4] CONTEXT   {target_path} -> {target_route}")
        print(f"                required gates: {', '.join(planned_gates)}")
        print(f"[3/4] GATES     task: {task} (this runner makes no edit; sandboxing unmeasured)")

    measured_rows = gate_rows([gate_record(target_path, g) for g in planned_gates], execute)
    exit_code = verdict_code(measured_rows)
    verdict = receipt_mod.verdict_of([receipt_mod.check_state(r["verdict"]) for r in measured_rows])

    inputs = target_inputs(task, target_path, str(agent_display))
    receipt_data = receipt_mod.build_computation_receipt(
        program="headron.workflow",
        version=str(atlas().get("version", "unknown")),
        inputs=inputs,
        outputs={"verdict": verdict, "checks": measured_rows},
        status=STATUS[verdict],
        verification={"verdict": verdict, "checks": measured_rows},
        evidence_refs=(target_path,),
    )

    elapsed_s = round(time.monotonic() - start_time, 2)
    if not as_json:
        passed = sum(r["verdict"] == "PASS" for r in measured_rows)
        print(f"[4/4] RECEIPT   {receipt_data['receipt_id'][:16]}... ({verdict})")
        for row in measured_rows:
            if row["verdict"] != "PASS":
                print(f"                {row['verdict']:<8} {row['id']}: {row['why'][:120]}")
        print("-" * 78)
        print(f"VERDICT:        {verdict} ({passed}/{len(measured_rows)} gates PASS)")
        print(f"RECEIPT ID:     {receipt_data['receipt_id']}")
        print(f"TARGET:         {target_path} sha256 {inputs['path_sha256'] or 'absent'} on tree {inputs['tree']}")
        print(f"DURATION:       {elapsed_s}s")
        print("=" * 78)

    record = {
        "schema": 1,
        "command": "workflow",
        "task": task,
        "path": target_path,
        "agent": agent_display,
        "verdict": verdict,
        "receipt": receipt_data,
        "verification": {"rows": measured_rows, "exit": exit_code},
        "environment": env,
        "workspace": ws,
        "duration_s": elapsed_s,
    }
    return record, exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="workflow_runner.py", description="Run a task's declared gates and write a receipt of what each answered."
    )
    parser.add_argument("task", nargs="?", default="Verify task and repository contract", help="the task assignment")
    parser.add_argument("--path", default=None, help="target path or artifact the task operates on")
    parser.add_argument("--agent", default=None, help="agent runtime name (antigravity, claude, codex, local)")
    parser.add_argument(
        "--no-execute", dest="execute", action="store_false", help="run no gate: every gate answers NOT RUN (exit 2)"
    )
    parser.add_argument("--json", action="store_true", help="emit workflow outcome as a JSON record")
    args = parser.parse_args(argv)

    record, code = run_workflow(
        task=args.task, path=args.path, agent_name=args.agent, execute=args.execute, as_json=args.json
    )
    if args.json:
        print(json.dumps(record, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
