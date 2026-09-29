#!/usr/bin/env python3
"""Compact machine context for Codex and other runtimes.

A projection of Thea's existing declarations, not a second policy system.
"""
from __future__ import annotations

import argparse
import json

from atlascore import atlas, label_for, route_for, known_labels


def _scope(path: str) -> tuple[str | None, dict]:
    scopes = atlas().get("directory_scopes") or {}
    normalized = path.rstrip("/") + "/"
    matches = [(name, row or {}) for name, row in scopes.items()
               if normalized.startswith(str(name).rstrip("/") + "/") or normalized == str(name).rstrip("/")]
    return max(matches, key=lambda x: len(str(x[0]))) if matches else (None, {})


def _gates(change: str) -> list[str]:
    profile = ((atlas().get("verification_policy") or {}).get("profiles") or {}).get(change) or {}
    values = profile.get("gates") or profile.get("required_gates") or []
    if isinstance(values, dict):
        values = list(values)
    return [str(v) for v in values]


def _runtime(runtime: str) -> dict:
    row = (atlas().get("runtime_entry") or {}).get(runtime) or {}
    return {
        "id": runtime,
        "role": row.get("role"),
        "tools": row.get("default_tools") or [],
        "mcp": row.get("mcp"),
        "verification": row.get("verification"),
    }


def brief(path: str, task: str, change: str, runtime: str) -> dict:
    data = atlas()
    route = str(route_for(path) or "")
    scope_name, scope = _scope(path)
    known = known_labels()
    labels = [x for x in [label_for(path), scope.get("label")] if x and x in known]
    traps = [str(x) for x in scope.get("traps") or []]
    failures = data.get("agent_failure_modes") or {}
    trap_rows = [
        {"id": trap, "looks_like": str((failures.get(trap) or {}).get("looks_like") or "")}
        for trap in traps
    ]
    gates = _gates(change)
    next_action = "route" if not route else (
        "inspect-known-trap" if traps else ("run-required-gate" if gates else "inspect-target")
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
    record = brief(args.path, args.task, args.change, args.runtime)
    print(json.dumps(record, indent=None if args.json else 2, separators=(",", ":") if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
