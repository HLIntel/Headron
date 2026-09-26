#!/usr/bin/env python3
"""The MCP route that may EDIT — separate, opt-in, and bounded by the task contract it is started with.

WHY (3.17.0). The read-only route (thea_mcp.py) cannot change a file by construction. An agent that runs
under a task contract still needs to write, and doing it through its own shell leaves the controls on the
honour system. This route makes every write pass the same five controls agentrun uses, BEFORE it lands:
  sandbox   agentpolicy.path_verdict — only allowed_paths, never forbidden_paths, never a traversal
  budget    agentpolicy.budget_verdict — files_changed and lines_changed counted before the write
  edit      safeedit.replace_once + write_verified — an anchor that matches once, a write read back
  audit     agentaudit.append — every write and every refusal sealed onto the task's hash chain
It holds NO credential and runs NO command: no git, no shell, no network. Landing stays with
`branchstate.py --land`. Started only on purpose, with the contract named:

  python scripts/thea_edit.py <contract.json>     serve on stdio (refused under THEA_READ_ONLY)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import agentaudit
import safeedit
from agentpolicy import budget_verdict, contract_errors, path_verdict
from atlascore import ROOT

STATE = {"contract": {}, "files": set(), "lines": 0}
TOOL = {"name": "apply_edit", "description": "replace one exact, unique span of a file the task contract allows",
        "inputSchema": {"type": "object", "additionalProperties": False, "required": ["path", "old", "new"],
                        "properties": {"path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}}},
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}}


def _audit(kind: str, body: dict) -> None:
    agentaudit.append(agentaudit.stream_path(str(STATE["contract"].get("task_id"))), kind, body)


def apply_edit(path: str, old: str, new: str) -> tuple[bool, str]:
    """(done, why). Every refusal names the control that made it, and is audited like a write."""
    contract = STATE["contract"]
    verdict = path_verdict(contract, path, "write")
    lines = STATE["lines"] + max(old.count("\n"), new.count("\n")) + 1
    if verdict.allowed:
        verdict = budget_verdict(contract, {"files_changed": len(STATE["files"] | {path}), "lines_changed": lines})
    if not verdict.allowed:
        _audit("policy_denied", {"path": path, "control": verdict.control, "why": verdict.reason})
        return False, f"REFUSED by {verdict.control}: {verdict.reason}"
    target = ROOT / path
    try:
        text = safeedit.replace_once(target.read_text(encoding="utf-8"), old, new, path)
        safeedit.write_verified(target, text)
    except (OSError, ValueError) as refused:
        _audit("policy_denied", {"path": path, "control": "edit", "why": str(refused)})
        return False, f"REFUSED by edit: {refused}"
    STATE["files"].add(path)
    STATE["lines"] = lines
    _audit("file_changed", {"path": path, "lines_changed": lines})
    return True, f"edited {path}; {len(STATE['files'])} file(s), {lines} line(s) used of the contract's budget"


def handle(message: dict) -> dict | None:
    method, ident, params = message.get("method"), message.get("id"), message.get("params") or {}
    if ident is None:
        return None
    if method == "initialize":
        result = {"protocolVersion": params.get("protocolVersion"), "capabilities": {"tools": {"listChanged": False}},
                  "serverInfo": {"name": "thea-edit", "version": "contract-bound"},
                  "instructions": f"Edits only within task {STATE['contract'].get('task_id')}; land with branchstate --land."}
    elif method == "tools/list":
        result = {"tools": [TOOL]}
    elif method == "tools/call" and params.get("name") == "apply_edit":
        args = params.get("arguments") or {}
        done, why = apply_edit(str(args.get("path")), str(args.get("old")), str(args.get("new")))
        result = {"content": [{"type": "text", "text": why}], "isError": not done}
    else:
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def start(contract_path: str) -> str | None:
    """Load and validate the contract; the reason it cannot start, or None."""
    if os.environ.get("THEA_READ_ONLY"):
        return "THEA_READ_ONLY is set: the edit route does not start in a read-only session"
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    problems = contract_errors(contract)
    if problems:
        return "the task contract does not validate: " + problems[0]
    STATE.update(contract=contract, files=set(), lines=0)
    return None


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.split("\n\n", 1)[0])
        sys.exit(2)
    reason = start(sys.argv[1])
    if reason:
        print(f"REFUSED: {reason}", file=sys.stderr)
        sys.exit(1)
    import thea_mcp
    sys.exit(thea_mcp.serve(handle))
