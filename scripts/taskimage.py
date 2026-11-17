#!/usr/bin/env python3
"""Task image: one task's contract, gate graph, results, obligations and receipt, kept as a git commit under a ref.

A task run used to leave its state in three places a later reader cannot join: the outcome on stdout, the audit
stream under .agent/audit, the obligation ledger under HEADRON_HOME. Each `compile`, `run` or `resume` writes the
joined state as one commit on refs/headron/tasks/<task_id>; the ref's history is the task's checkpoints. Git is the
store, so the image is content-addressed, copied with `git fetch`/`git push` of that ref, and never a tracked file.

  headron task compile <contract.headron>             # the image with every node NOT RUN
  headron task run     <contract.headron> [--execute] # run the gates through agentrun, record each node
  headron task resume  <contract.headron> [--execute] # refused unless the contract is the one the image recorded;
                                                      # gates run again when execution is requested
  headron task inspect <task_id> [--json]             # reads the ref only, never the working tree

The image tree holds contract.json (the compiled contract), state.json (contract hash, tree, status, the node
order and one result per node), outcome.json (agentrun's outcome), receipt.json and, when the task has one,
obligations.jsonl (the ledger snapshot). Gates run only through agentrun.execute_contract, the one caller that
executes anything under the policy; this module never runs a gate itself.

proves: an image whose contract hash differs from the contract given refuses resume; a node with no recorded
  result, or a gate that did not run, reads NOT RUN and never PASS; resume does not reuse gate results;
  a blob, message or identity privacy_guard would refuse is never written; a ref moved by another writer
  refuses the update instead of overwriting it
does_not_prove: that a recorded gate checks what the task needs, or that a fetched image was produced by the
  run it describes; a signature identifies a signer, not a truthful execution
closed_by: taskimage_test.py, which plants a stale contract, a missing node, a dry run, a stale pass, a home
  path in a contract and a concurrent ref update
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import agentpolicy
import gitobject
import headronlang
import obligations
import privacy_guard
from atlascore import ROOT

PREFIX = "refs/headron/tasks/"
SCHEMA = "headron-task/1"
# A FIXED, NOREPLY IDENTITY. The image is written by the tool, not by whoever runs it, and a ref that can be pushed
# from a public repository must not carry the operator's address (privacy_guard.check_identity).
IDENTITY = {
    "GIT_AUTHOR_NAME": "headron task image",
    "GIT_AUTHOR_EMAIL": "noreply@example.invalid",
    "GIT_COMMITTER_NAME": "headron task image",
    "GIT_COMMITTER_EMAIL": "noreply@example.invalid",
}
LONG_HEX = re.compile(r"[0-9a-f]{40,}")
NOT_RUN = "NOT RUN"


class Refused(Exception):
    """A write or resume the image cannot stand behind; the message says why."""


def _git(repo: Path, *args: str, data: bytes | None = None, env: dict[str, str] | None = None) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=data,
        capture_output=True,
        check=False,
        timeout=60,
        env={**os.environ, **(env or {})},
    )
    if done.returncode != 0:
        raise Refused(f"git {args[0]}: {done.stderr.decode(errors='replace').strip()}")
    return done.stdout.decode().strip()


def ref_for(task_id: str, repo: Path = ROOT) -> str:
    ref = PREFIX + task_id
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", task_id) or task_id.endswith((".", ".lock")):
        raise Refused(f"task id {task_id!r} is not a ref-safe slug")
    _git(repo, "check-ref-format", ref)
    return ref


def node_state(row: dict) -> str:
    """One gate row to one state. Only a gate that RAN and exited 0 is PASS; a row that did not run is NOT RUN."""
    if "control" in row:
        return "REFUSED"
    if not row.get("ran"):
        return NOT_RUN
    return "PASS" if row.get("exit_code") == 0 else "FAIL"


def nodes_of(state: dict) -> list[tuple[str, dict]]:
    """Every node in the recorded order; one the image has no result for reads NOT RUN, never a pass."""
    recorded = state.get("nodes") or {}
    return [(name, recorded.get(name) or {"state": NOT_RUN, "why": "no recorded result"}) for name in state["order"]]


def privacy_findings(files: dict[str, bytes], message: str) -> list[str]:
    """What privacy_guard refuses in a blob line or the message. Its escape comment is not honoured here: the
    content is generated from a contract, so a contract cannot opt its own text out of the scan."""
    findings: list[str] = []
    names = privacy_guard.load_denylist()
    for name, body in sorted(files.items()):
        for n, line in enumerate(body.decode(errors="replace").splitlines(), 1):
            privacy_guard.scan_line(f"{name}:{n}", line.replace(privacy_guard.ESCAPE, ""), names, findings)
    privacy_guard.scan_line("message", message.replace(privacy_guard.ESCAPE, ""), names, findings)
    if LONG_HEX.search(message):
        findings.append("message: a full object id or digest belongs in state.json, not the message")
    for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        privacy_guard.check_identity(key, IDENTITY[key], findings)
    return findings


def read(task_id: str, repo: Path = ROOT) -> tuple[str, dict[str, bytes]] | None:
    """The image at the ref, as (commit, {name: bytes}); None when there is none. Reads git objects only."""
    ref = ref_for(task_id, repo)
    try:
        commit = _git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}")
    except Refused:
        return None
    files: dict[str, bytes] = {}
    for line in _git(repo, "ls-tree", commit).splitlines():
        meta, name = line.split("\t", 1)
        blob = meta.split()[2]
        files[name] = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "blob", blob], capture_output=True, check=True, timeout=60
        ).stdout
    return commit, files


def write(task_id: str, files: dict[str, bytes], message: str, expect: str | None, repo: Path = ROOT) -> str:
    """One commit on the task's ref. `expect` is the commit the caller read (None: no image yet); another writer
    having moved the ref since refuses, so two runs cannot silently overwrite one another."""
    findings = privacy_findings(files, message)
    if findings:
        raise Refused("privacy_guard refuses the image: " + "; ".join(findings[:5]))
    ref = ref_for(task_id, repo)
    entries = "".join(
        f"100644 blob {_git(repo, 'hash-object', '-w', '--stdin', data=body)}\t{name}\n"
        for name, body in sorted(files.items())
    )
    tree = _git(repo, "mktree", data=entries.encode())
    parents = ["-p", expect] if expect else []
    commit = _git(repo, "commit-tree", tree, *parents, "-m", message, env=IDENTITY)
    old = expect or gitobject.absent(_git(repo, "rev-parse", "--show-object-format"))
    _git(repo, "update-ref", ref, commit, old)
    return commit


def _dump(obj: object) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()


def image_files(contract: dict, rows: list[dict], outcome: dict | None, tree: str) -> dict[str, bytes]:
    order = [str(g) for g in agentpolicy.required_gates(contract)]
    nodes = {str(r["gate"]): {"state": node_state(r), "exit_code": r["exit_code"], "tree": tree} for r in rows}
    state = {
        "schema": SCHEMA,
        "task_id": contract["task_id"],
        "contract": agentpolicy.contract_hash(contract),
        "tree": tree,
        "status": (outcome or {}).get("status", "compiled"),
        "order": order,
        "nodes": nodes,
    }
    files = {"contract.json": _dump(contract), "state.json": _dump(state)}
    if outcome is not None:
        files["outcome.json"] = _dump(outcome)
        files["receipt.json"] = _dump(outcome.get("receipt") or {})
    ledger = obligations.path(str(contract["task_id"]))
    if ledger.is_file():
        files["obligations.jsonl"] = ledger.read_bytes()
    return files


def stale_reason(state: dict, contract: dict) -> str | None:
    recorded, given = state.get("contract"), agentpolicy.contract_hash(contract)
    if recorded != given:
        return f"the image was recorded for contract {str(recorded)[:12]}, this contract is {given[:12]}"
    return None


def compile_image(path: Path, repo: Path = ROOT) -> tuple[dict, int]:
    contract = headronlang.load_contract(path)
    found = read(str(contract["task_id"]), repo)
    files = image_files(contract, [], None, obligations.tree(repo))
    write(str(contract["task_id"]), files, f"task {contract['task_id']}: compile", found[0] if found else None, repo)
    return json.loads(files["state.json"]), 0


def run_image(path: Path, execute: bool, resume: bool, repo: Path = ROOT) -> tuple[dict, int]:
    import agentrun  # noqa: PLC0415 - the runner pulls in the policy stack; inspect never needs it

    contract = headronlang.load_contract(path)
    task_id = str(contract["task_id"])
    found = read(task_id, repo)
    tree = obligations.tree(repo)
    if resume:
        if found is None:
            raise Refused(f"no image at {PREFIX}{task_id}: compile or run it first")
        state = json.loads(found[1]["state.json"])
        reason = stale_reason(state, contract)
        if reason:
            raise Refused(f"stale contract, resume refused: {reason}")
    record, code = agentrun.execute_contract(path, execute)
    if "outcome" not in record:
        raise Refused("agentrun refused the contract: " + "; ".join(map(str, record.get("refusals") or [])))
    outcome = record["outcome"]
    if outcome["status"] == "verified" and (
        tree == obligations.UNKNOWN_TREE or tree.endswith("+dirty") or obligations.tree(repo) != tree
    ):
        raise Refused("verified task requires a clean source tree unchanged during execution")
    files = image_files(contract, outcome["gates"], outcome, tree)
    verb = "resume" if resume else "run"
    write(task_id, files, f"task {task_id}: {verb} ({outcome['status']})", found[0] if found else None, repo)
    return json.loads(files["state.json"]), code


def inspect(task_id: str, repo: Path = ROOT) -> tuple[dict, int]:
    found = read(task_id, repo)
    if found is None:
        raise Refused(f"no image at {PREFIX}{task_id}")
    commit, files = found
    state = json.loads(files["state.json"])
    checkpoints = int(_git(repo, "rev-list", "--count", commit))
    view = {**state, "commit": commit, "checkpoints": checkpoints, "files": sorted(files)}
    view["nodes"] = dict(nodes_of(state))
    passed = all(node.get("state") == "PASS" for node in view["nodes"].values())
    return view, 0 if state.get("status") == "verified" and passed and view["nodes"] else 1


def show(view: dict) -> None:
    print(f"task {view['task_id']}  {view['status']}  tree {view['tree'][:12]}  contract {view['contract'][:12]}")
    for name, node in view["nodes"].items():
        print(f"  {node['state']:<8} {name}")
    if "checkpoints" in view:
        print(f"  {view['checkpoints']} checkpoint(s) on {PREFIX}{view['task_id']}; files {', '.join(view['files'])}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taskimage.py", description=(__doc__ or "").split("\n", 1)[0])
    parser.add_argument("action", choices=("compile", "run", "resume", "inspect"))
    parser.add_argument("target", help="a .headron or .json contract; for inspect, a task id")
    parser.add_argument("--execute", action="store_true", help="run each resolvable gate (default: controls only)")
    parser.add_argument("--json", action="store_true", help="emit the image state as JSON")
    args = parser.parse_args(argv)
    return cli(args.action, args.target, args.execute, args.json)


def cli(action: str, target: str, execute: bool, as_json: bool) -> int:
    try:
        if action == "inspect":
            view, code = inspect(target)
        elif action == "compile":
            view, code = compile_image(Path(target))
        else:
            view, code = run_image(Path(target), execute, resume=action == "resume")
    except Refused as why:
        if as_json:
            print(json.dumps({"schema": SCHEMA, "command": "task", "action": action, "refused": str(why)}, indent=2))
        print(f"task {action}: REFUSED {why}", file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps({**view, "command": "task", "action": action}, indent=2, sort_keys=True))
    else:
        show(view if "checkpoints" in view else {**view, "nodes": dict(nodes_of(view))})
    return code


if __name__ == "__main__":
    sys.exit(main())
