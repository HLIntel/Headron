#!/usr/bin/env python3
"""The reference runner: the one caller in this tree that executes anything under the policy.

WHY IT EXISTS (2.9.0). `plan --json` produced a good-looking record and nothing compared it to
what happened afterwards, so an agent could plan one change and make another with no artifact
that disagreed. This runner closes the loop in one record: the SAME contract carries the plan and
the outcome, every planned gate appears in the result INCLUDING the ones that did not run, and the
changed files are compared against the paths the plan declared.

THE THREE THINGS IT REFUSES TO CLAIM.
  1. A gate that did not run is written `ran: false` with the reason. A missing gate and a passing
     gate are otherwise the same absence, which is the shape this record exists to refuse.
  2. The sandbox rows marked host-observed are printed UNOBSERVED. A task that ran outside a
     sandbox must never read as one that ran inside it.
  3. The environment is fingerprinted, because two runs reporting the same gate as passed under
     different toolchains are two different claims wearing one word.

IT IS NOT A SECURITY BOUNDARY. It refuses what it is asked about. An agent that does not ask is
bounded by the host, per `atlas.yaml/agent_policy/sandbox_requirements`.
"""
from __future__ import annotations

import hashlib
import json
import platform
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import agentaudit
import agentpolicy
from atlascore import ROOT, atlas, route_for


def workspace_report() -> dict:
    """The one sandbox row this process can answer for: where it writes, and whether that is isolated.

    Named by `agent_policy/sandbox_requirements/workspace_lifetime/observed_by`, so the contract
    refuses if this function is renamed or deleted — a row observed by nothing is the blind spot
    the roster exists to make unrepresentable.
    """
    scratch = Path(tempfile.gettempdir()).resolve()
    return {
        "repository": str(ROOT.resolve()),
        "scratch": str(scratch),
        "isolated": not str(ROOT.resolve()).startswith(str(scratch) + "/"),
    }


def environment_fingerprint() -> dict:
    """The machine, as an identity rather than a description.

    `doctor` answers which capabilities exist; this answers WHICH MACHINE, so two outcome records
    that both say a gate passed can be told apart when their toolchains differ. Everything in the
    digest is something that changes the meaning of an exit code.
    """
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                          text=True, check=False)
    facts = {
        "os": platform.system(),
        "release": platform.release().split("-", 1)[0],
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "atlas_version": str(atlas().get("version")),
        "repository_commit": head.stdout.strip()[:40] if head.returncode == 0 else "unknown",
    }
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":"))
    facts["fingerprint"] = hashlib.sha256(canonical.encode()).hexdigest()
    return facts


def changed_files() -> list[str]:
    """What the working tree actually changed, from git rather than from the agent's account of it."""
    result = subprocess.run(["git", "status", "--porcelain=v1", "-z"], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []
    fields = [f for f in result.stdout.split("\0") if f.strip()]
    return sorted({f[3:] for f in fields if len(f) > 3})


def plan_drift(contract: dict) -> list[str]:
    """Does the contract still agree with what the router and the policy resolve TODAY?

    A plan is resolved once and acted on later. If the route moved, the change class gained a gate,
    or the atlas version advanced, the plan is stale — and a stale plan that still validates is the
    most convincing kind of wrong.
    """
    problems: list[str] = []
    target = contract.get("target")
    resolved = route_for(str(target)) if target else contract.get("route")
    if target and resolved != contract.get("route"):
        problems.append(f"the contract routes {target} to {contract.get('route')!r}; "
                        f"the router resolves {resolved!r}")
    if str(contract.get("atlas_version")) != str(atlas().get("version")):
        problems.append(f"planned against atlas {contract.get('atlas_version')}, "
                        f"this tree is {atlas().get('version')} — re-plan rather than re-use")
    expected = agentpolicy.required_gates(contract)
    if contract.get("required_gates") is not None and list(contract["required_gates"]) != expected:
        problems.append(f"required_gates says {contract['required_gates']}, the change class and "
                        f"its modifiers resolve to {expected}")
    return problems


def run_gates(contract: dict, stream: Path, execute: bool, budget: dict) -> list[dict]:
    """One row per PLANNED gate, including every one that did not run and why.

    `execute` is off by default. A runner that shells out on every pull request would make this
    gate depend on 35 toolchains being present; with it off the rows still say what WOULD run,
    which is the part that rots. An absent tool is reported, never skipped.
    """
    rows: list[dict] = []
    for gate in agentpolicy.required_gates(contract):
        argv, why = agentpolicy.gate_command(str(contract.get("route")), gate)
        row: dict[str, object] = {"gate": gate, "ran": False, "exit_code": -1}
        if argv is None:
            row["command"] = f"unrunnable: {why}"
        else:
            row["command"] = shlex.join(argv)
            verdict = agentpolicy.command_verdict(contract, argv)
            budget["tool_calls"] = int(budget.get("tool_calls", 0)) + 1
            allowed = verdict.allowed and agentpolicy.budget_verdict(contract, budget).allowed
            if not allowed:
                reason = verdict.reason if not verdict.allowed else "budget exhausted"
                row["command"] = f"refused: {reason}"
                agentaudit.append(stream, "policy_denied", {"gate": gate, "reason": reason})
            elif execute:
                agentaudit.append(stream, "command_started", {"gate": gate, "argv": agentaudit.digest(argv)})
                done = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False)
                row.update({"ran": True, "exit_code": done.returncode})
                agentaudit.append(stream, "command_finished", {
                    "gate": gate, "exit_code": done.returncode,
                    "stdout": agentaudit.digest(done.stdout), "stderr": agentaudit.digest(done.stderr)})
        agentaudit.append(stream, "gate_result", {k: row[k] for k in ("gate", "ran", "exit_code")})
        rows.append(row)
    return rows


def execute_contract(path: Path, execute: bool) -> tuple[dict, int]:
    """Validate, resolve, run under the controls, and write the outcome into the same record."""
    contract = json.loads(path.read_text(encoding="utf-8"))
    problems = agentpolicy.contract_errors(contract)
    if problems:
        return {"refusals": problems}, 2
    stream = agentaudit.stream_path(str(contract["task_id"]))
    agentaudit.append(stream, "task_created", {"contract": agentpolicy.contract_hash(contract),
                                               "objective": contract.get("objective")})
    drift = plan_drift(contract)
    agentaudit.append(stream, "plan_resolved", {"drift": drift, "gates": agentpolicy.required_gates(contract)})
    environment = environment_fingerprint()
    budget: dict[str, int] = {"tool_calls": 0}
    started = time.monotonic()
    rows = run_gates(contract, stream, execute, budget)
    touched = changed_files()
    scope = agentpolicy.scope_verdict(contract, touched)
    if not scope.allowed:
        agentaudit.append(stream, "scope_expanded", {"reason": scope.reason, "files": len(touched)})
    unobserved = sorted(name for name, row in
                        ((agentpolicy.policy().get("sandbox_requirements") or {}).items())
                        if str((row or {}).get("observed_by")) == "host")
    denials = ([] if scope.allowed else [{"control": scope.control, "reason": scope.reason}])
    denials += [{"control": "plan", "reason": d} for d in drift]
    denials += [{"control": "narrow_tools", "reason": str(r["command"])}
                for r in rows if str(r["command"]).startswith("refused: ")]
    failed = [r for r in rows if r["ran"] and r["exit_code"] != 0]
    unran = [r for r in rows if not r["ran"]]
    # THE ONLY STATUS A DRY RUN MAY CLAIM. `verified` means the gates RAN and passed; a run that
    # exercised every control and no gate says exactly that and not one word more, because the
    # word it would otherwise borrow is the one a reader acts on.
    status = ("refused" if denials else
              "failed" if failed else
              "verified" if not unran else "controls_verified")
    contract["status"] = status
    contract["outcome"] = {
        "status": status,
        "mode": "full" if execute else "controls_only",
        "changed_files": touched,
        "scope_expanded": not scope.allowed,
        "gates": rows,
        "budgets_used": {**budget, "wall_clock_seconds": max(1, int(time.monotonic() - started))},
        "denials": denials,
        "audit_stream": agentaudit.stream_path(str(contract["task_id"])).relative_to(ROOT).as_posix(),
        "audit_head": agentaudit.head(stream),
        "environment": environment,
        "sandbox_unobserved": unobserved,
    }
    agentaudit.append(stream, "task_finished", {"status": status, "gates": len(rows)})
    return contract, 0 if status in ("verified", "controls_verified") else 1


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="agentrun.py")
    parser.add_argument("contract", nargs="?",
                        default=str((atlas().get("agent_policy") or {}).get("reference_contract")))
    parser.add_argument("--execute", action="store_true",
                        help="actually run each resolvable gate; off by default, and a gate that "
                             "does not run is recorded as not having run")
    parser.add_argument("--json", action="store_true", help="emit the completed contract")
    args = parser.parse_args(argv)
    record, code = execute_contract(Path(args.contract), args.execute)
    if args.json:
        print(json.dumps(record, indent=2, sort_keys=False))
        return code
    for refusal in record.get("refusals", []):
        print(f"- refused: {refusal}")
    outcome = record.get("outcome")
    if not outcome:
        return code
    workspace = workspace_report()
    print(f"task {record['task_id']}: {record['status']}")
    for row in outcome["gates"]:
        print(f"  gate {row['gate']:<28} ran={str(row['ran']):<5} exit={row['exit_code']:<4} {row['command']}")
    for denial in outcome["denials"]:
        print(f"  DENIED [{denial['control']}] {denial['reason']}")
    print(f"  gates: {sum(1 for r in outcome['gates'] if r['ran'])} of {len(outcome['gates'])} ran "
          f"(mode {outcome['mode']}) — a gate that did not run is not a gate that passed")
    print(f"  changed files: {len(outcome['changed_files'])} | budgets used: "
          + ", ".join(f"{k}={v}" for k, v in sorted(outcome["budgets_used"].items())))
    print(f"  environment {outcome['environment']['fingerprint'][:12]} | "
          f"audit {outcome['audit_stream']} head {outcome['audit_head'][:12]} "
          f"({len(agentaudit.verify(agentaudit.stream_path(record['task_id']))) or 'chain intact'})")
    print(f"  workspace isolated: {workspace['isolated']}")
    print(f"  UNOBSERVED by this runner ({len(outcome['sandbox_unobserved'])} host rows): "
          + ", ".join(outcome["sandbox_unobserved"]))
    return code


if __name__ == "__main__":
    sys.exit(main())
