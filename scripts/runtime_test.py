#!/usr/bin/env python3
"""Planted cases for runtime attribution and the GitHub App scaffold (3.56.0)."""

from __future__ import annotations

import os
from typing import Any, cast

ROOT = CASES = mutated = atlas = cast(Any, None)


def run(module) -> None:
    """Bind the running atlas_test module, then plant runtime and githubapp cases (3.56.0)."""
    global ROOT, CASES, mutated, atlas
    ROOT = module.ROOT
    CASES = module.CASES
    mutated = module.mutated
    atlas = module.atlas
    before = len(CASES)
    runtime_cases()
    githubapp_cases()
    if len(CASES) - before != 4:
        raise SystemExit(f"runtime_test registered {len(CASES) - before} cases, want 4")


def runtime_cases() -> None:
    import runtime

    saved = {k: os.environ.get(k) for k in ("HEADRON_AGENT", "CLAUDE_CODE_SESSION_ID", "HERMES_HOME", "GITHUB_BASE_REF")}
    try:
        for key in saved:
            os.environ.pop(key, None)
        absent = runtime.resolve()
        if absent["agent"] != "unknown" or absent["source"] != "absent":
            raise SystemExit(f"FAIL absent HEADRON_AGENT must resolve unknown, got {absent}")
        CASES.append(
            ("absent HEADRON_AGENT resolves to unknown, never claude-code", "silent vendor default on every hook")
        )

        os.environ["HEADRON_AGENT"] = "Grok Bot"
        grok = runtime.resolve()
        if grok["agent"] != "grok-bot" or grok["family"] != "cursor":
            raise SystemExit(f"FAIL grok-bot must roll up to cursor family, got {grok}")
        CASES.append(("grok-bot rolls up to the cursor family", "a Cursor-hosted engine scored as a stranger"))

        os.environ.pop("HEADRON_AGENT", None)
        os.environ["CLAUDE_CODE_SESSION_ID"] = "sess-1"
        claude = runtime.resolve()
        if claude["agent"] != "claude-code" or claude["source"] != "CLAUDE_CODE_SESSION_ID":
            raise SystemExit(f"FAIL CLAUDE_CODE_SESSION_ID must imply claude-code, got {claude}")
        CASES.append(("CLAUDE_CODE_SESSION_ID attributes claude-code", "a Claude session recorded as unknown"))
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    print("  ok    runtime attribution cases")


def githubapp_cases() -> None:
    import githubapp

    report = githubapp.build_report("HEAD", execute=False)
    if not report["comment_markdown"].startswith(githubapp.REPORT_HEADING):
        raise SystemExit("FAIL HEADRON REPORT must start with the declared heading")
    if report["check_run"]["name"] != githubapp.CHECK_NAME:
        raise SystemExit("FAIL check-run name drifted from Headron verify")
    metrics = report["metrics"]
    for key in ("verifications", "pass", "fail", "blocked", "agent", "runtime"):
        if key not in metrics:
            raise SystemExit(f"FAIL metrics record missing {key}")
    if "merge_allowed" not in report or "required_gates" not in report:
        raise SystemExit("FAIL report missing merge_allowed or required_gates")
    CASES.append(
        ("githubapp scaffold emits check-run, HEADRON REPORT and metrics", "an App with no verdict shape to post")
    )
    print("  ok    githubapp scaffold cases")
