#!/usr/bin/env python3
"""Headless runner — run one task contract non-interactively, and say which sandbox it ran under.

WHY. agentrun.py is the reference runner, but it has no declared answer to "what isolation did this
run get?" A caller that wants to script a run has to guess, and a sandboxless run could read as a
sandboxed one. This entry point makes the isolation an explicit argument and labels it in the record.

MODES.
  none     run the contract on this host, with NO sandbox. Refused unless --accept-no-sandbox is given,
           and the record says UNSANDBOXED. This is the only mode this script executes itself.
  docker   print the `docker run` argv that sandboxgen.py builds; the host runs it. Exit 3, because a
           run this script did not perform cannot be reported as having run.
  macos    print the sandbox-exec profile that sandboxgen.py builds; the host applies it. Exit 3.

EXIT CODES. The exit code of agentrun for a sandboxless run: 0 the contract completed, 1 it did not
(a gate failed, a gate did not run, or the runner refused the contract). 2 usage or a refused mode.
3 a sandboxed mode that this script hands to the host and did not run itself.

    python scripts/headless.py tools/agent-task.example.headron --sandbox none --accept-no-sandbox --json
    python scripts/headless.py tools/agent-task.example.headron --sandbox docker
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

MODES = ("docker", "macos", "none")
LABELS = {
    "docker": "sandbox provided by host (docker run)",
    "macos": "sandbox provided by host (sandbox-exec)",
    "none": "UNSANDBOXED: host controls not applied",
}


def plan(mode: str, accept_no_sandbox: bool) -> tuple[bool, str]:
    """Whether a run may start in this mode, and the isolation label its record must carry."""
    if mode not in MODES:
        return False, f"unknown sandbox {mode!r}; one of {', '.join(MODES)}"
    if mode == "none" and not accept_no_sandbox:
        return False, "a sandboxless run needs --accept-no-sandbox; it is never the default"
    return True, LABELS[mode]


def _hand_to_host(contract_path: str, mode: str) -> dict:
    """The sandbox command for a host to run. Built, never executed, here."""
    import sandboxgen

    contract, config = sandboxgen._load(contract_path)
    worktree = str(Path.cwd())
    if mode == "docker":
        argv = sandboxgen.docker_argv(contract, config, worktree, "python:3.12-slim")
        return {"command": " ".join(argv)}
    return {"profile": sandboxgen.macos_profile(contract, config, worktree, str(Path.home()))}


def run(contract_path: str, mode: str, accept_no_sandbox: bool, execute: bool) -> tuple[dict, int]:
    """The record of one headless run, and its exit code. Pure apart from the calls it names."""
    ok, label = plan(mode, accept_no_sandbox)
    record: dict = {"sandbox": mode, "isolation": label, "contract": contract_path}
    if not ok:
        record["refused"] = label
        return record, 2
    if mode != "none":
        record.update(_hand_to_host(contract_path, mode))
        record["ran"] = False
        return record, 3
    import agentrun

    outcome, code = agentrun.execute_contract(Path(contract_path), execute)
    record["ran"] = True
    record["outcome"] = outcome
    return record, code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="headless.py")
    parser.add_argument("contract")
    parser.add_argument("--sandbox", default="docker", choices=MODES)
    parser.add_argument("--accept-no-sandbox", action="store_true")
    parser.add_argument("--execute", action="store_true", help="run the gates; off by default")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    record, code = run(args.contract, args.sandbox, args.accept_no_sandbox, args.execute)
    print(json.dumps(record, indent=2, sort_keys=True, default=str) if args.json else record["isolation"])
    return code


if __name__ == "__main__":
    sys.exit(main())
