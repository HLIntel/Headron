#!/usr/bin/env python3
"""Compact machine context for Codex and other runtimes.

A projection of Thea's existing declarations, not a second policy system.
"""

from __future__ import annotations

import argparse
import json

from agentpolicy import required_gates
from atlascore import atlas, known_labels, label_for, route_for
from dirscope import scope_for


def _scope(path: str) -> tuple[str | None, dict]:
    name, row = scope_for(path)
    return name or None, row


def _gates(change: str) -> list[str]:
    profiles = (atlas().get("verification_policy") or {}).get("profiles") or {}
    if change not in profiles:
        raise ValueError(f"unknown change class: {change}")
    return required_gates({"change_class": change})


def _runtime(runtime: str) -> dict:
    rows = {str(row.get("id")): row for row in atlas().get("runtime_entry") or []}
    if runtime not in rows:
        raise ValueError(f"unknown runtime: {runtime}")
    row = rows[runtime]
    native = ((atlas().get("native_agent_tools") or {}).get("runtimes") or {}).get(runtime) or {}
    return {
        "id": runtime,
        "runtime": row["runtime"],
        "loads": row["loads"],
        "adapter": row["adapter"],
        "thea_via": native.get("thea_via") or [],
    }


def brief(path: str, task: str, change: str, runtime: str) -> dict:
    data = atlas()
    if task and task not in (data.get("task_profiles") or {}):
        raise ValueError(f"unknown task profile: {task}")
    route = str(route_for(path) or "")
    scope_name, scope = _scope(path)
    known = known_labels()
    labels = [x for x in [label_for(path), scope.get("label")] if x and x in known]
    traps = [str(x) for x in scope.get("traps") or []]
    failures = data.get("agent_failure_modes") or {}
    trap_rows = [{"id": trap, "looks_like": str((failures.get(trap) or {}).get("looks_like") or "")} for trap in traps]
    gates = _gates(change)
    next_action = (
        "route"
        if not route
        else ("inspect-known-trap" if traps else ("run-required-gate" if gates else "inspect-target"))
    )
    return {
        "schema": 1,
        "id": "thea.brief",
        "version": str(data.get("version")),
        "path": path,
        "route": route,
        "scope": scope_name,
        "task": task,
        "change": change,
        "runtime": _runtime(runtime),
        "gates": gates,
        "labels": sorted(set(labels)),
        "traps": trap_rows,
        "next": next_action,
        "uncertainty": "route/gate declarations are authoritative; next is a deterministic suggestion, not proof",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codexbrief")
    parser.add_argument("--path", required=True)
    parser.add_argument("--task", default="")
    parser.add_argument("--change", default="source_change")
    parser.add_argument("--runtime", default="openai_codex")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        record = brief(args.path, args.task, args.change, args.runtime)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(record, indent=None if args.json else 2, separators=(",", ":") if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
