#!/usr/bin/env python3
"""CLI commands for the decision engine and pipeline.

Moved from atlas.py to keep it under MAX_CODE_LINES (rule 6: never raise a cap).

proves: the decide-engine and pipeline CLI commands work correctly
does_not_prove: that the verdicts are correct for the task — only that the commands run
closed_by: atlas_test.py, which asserts the commands are reachable
"""

from __future__ import annotations

import json


def decide_engine(target: str, mode: str, as_json: bool) -> int:
    """`thea decide-engine <target>` — classify a file or command using the compiled decision engine."""
    from decide import command_verdict, reset_caches  # noqa: PLC0415
    from reflex import classify_change, classify_diff, forbidden_path_touched  # noqa: PLC0415

    reset_caches()
    if mode == "command":
        cat, risk = command_verdict(target)
        record = {"command": "decide-engine", "cmd": target, "category": cat, "risk": risk, "type": "command"}
    else:
        files = [target]
        diff_meta = {"files": files}
        verdicts = classify_diff(diff_meta)
        change_verdict = classify_change("source_change", files, diff_meta)
        is_forbidden = forbidden_path_touched(target)
        record = {
            "command": "decide-engine",
            "file": target,
            "verdicts": verdicts,
            "change_verdict": change_verdict.value,
            "forbidden_path": is_forbidden,
            "type": "file",
        }
    if as_json:
        print(json.dumps(record, indent=2))
    else:
        if mode == "command":
            print(f"command: {target}")
            print(f"category: {record['category']} (risk {record['risk']})")
        else:
            print(f"file: {target}")
            print(f"change verdict: {record['change_verdict']}")
            print(f"forbidden path: {record['forbidden_path']}")
            for gate, verdict in record["verdicts"].items():
                print(f"  {gate}: {verdict}")
    return 0


def run_pipeline_cmd(path: str, change_class: str, as_json: bool) -> int:
    """`thea pipeline <path>` — run the state-to-action pipeline."""
    from pipeline import run_pipeline  # noqa: PLC0415

    record = run_pipeline(change_class, [path])
    if as_json:
        print(
            json.dumps(
                {
                    "command": "pipeline",
                    "state": record.state,
                    "verdicts": record.verdicts,
                    "artifact": record.artifact,
                    "next_state": record.next_state,
                    "history": record.history,
                },
                indent=2,
            )
        )
    else:
        print(f"pipeline: {path} ({change_class})")
        print(f"state: {record.state}")
        print(f"history: {' → '.join(record.history)}")
        for gate, verdict in record.verdicts.items():
            print(f"  {gate}: {verdict}")
    return 0
