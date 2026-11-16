#!/usr/bin/env python3
"""Receipt loading, validation, and PR comment rendering for the Headron GitHub App."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

from atlascore import atlas

RECEIPT_CANDIDATES = (
    Path("receipts/verify.json"),
    Path(".headron/receipt.json"),
    Path("receipt.json"),
    Path("receipts/headron.receipt"),
)
REPORT_HEADING = "## HEADRON REPORT"


def load_receipt(tree: Path, head_sha: str, base_sha: str | None) -> tuple[dict | None, str | None]:
    """Look for an intact receipt in `tree` bound to base_sha. Returns (receipt_dict, error_message)."""
    import receipt

    for rel in RECEIPT_CANDIDATES:
        path = tree / rel
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError as err:
            return None, f"cannot read receipt {rel}: {err}"
        findings = receipt.verify_bytes(data)
        if findings:
            return None, f"receipt {rel} invalid: {'; '.join(findings)}"
        try:
            rec = json.loads(data.decode("utf-8"))
        except Exception as err:
            return None, f"receipt {rel} unparseable: {err}"
        if base_sha and rec.get("base_commit") != base_sha:
            return None, f"receipt base_commit {rec.get('base_commit')} does not match base {base_sha}"
        sig_path = path.with_name(path.name + ".sig")
        trust_file = os.environ.get("HEADRON_TRUST_FILE")
        signer = os.environ.get("HEADRON_SIGNER")
        if sig_path.is_file() and trust_file and signer:
            import receiptsign

            sig_findings = receiptsign.verify_detached(
                data, sig_path, signer, Path(trust_file), None, receiptsign.NAMESPACE
            )
            if sig_findings:
                return None, "; ".join(sig_findings)
        return rec, None
    return None, None


def comment_markdown(report: dict) -> str:
    """HEADRON REPORT body for the pull request."""
    files = report.get("changed_files") or []
    gates = report.get("required_gates") or []
    blocked = "blocked" if not report["merge_allowed"] else "allowed"
    agent = report.get("agent") or {}
    lines = [
        REPORT_HEADING,
        "",
        f"**Verdict:** {report['verdict']}",
        f"**Merge:** {blocked}",
        f"**Agent:** `{agent.get('agent', 'unknown')}` (runtime `{agent.get('runtime', 'unknown')}`)",
        "",
        "### Changed files",
    ]
    lines += [f"- `{f}`" for f in files[:50]] or ["- _(none)_"]
    if len(files) > 50:
        lines.append(f"- … and {len(files) - 50} more")
    lines += ["", "### Required gates"]
    lines += [f"- `{g}`" for g in gates] or ["- _(none declared)_"]
    lines += ["", f"_Contract v{atlas().get('version')} · posted by the Headron GitHub App._"]
    return "\n".join(lines) + "\n"


def post_pr_comment(transport: Callable, token: str, work: Mapping, report: dict) -> None:
    """Post or update the HEADRON REPORT receipt summary comment on the pull request."""
    pr_number = work.get("pr")
    if not pr_number:
        return
    body = report.get("comment_markdown") or ""
    if not body:
        return
    from githubapp import call

    try:
        comments = call(transport, token, "GET", f"/repos/{work['repo']}/issues/{pr_number}/comments")
        existing = next(
            (c for c in (comments if isinstance(comments, list) else []) if REPORT_HEADING in (c.get("body") or "")),
            None,
        )
        if existing and existing.get("id"):
            call(transport, token, "PATCH", f"/repos/{work['repo']}/issues/comments/{existing['id']}", {"body": body})
        else:
            call(transport, token, "POST", f"/repos/{work['repo']}/issues/{pr_number}/comments", {"body": body})
    except Exception as exc:
        sys.stderr.write(f"githubreceipt: comment post failed: {exc}\n")


def metrics_record(report: dict) -> dict:
    """Minimal metrics a future dashboard reads: counts, blocked, agent."""
    tally = (report.get("verify") or {}).get("tally") or {}
    passed = int(tally.get("PASS") or 0) + int(tally.get("REUSED") or 0)
    failed = int(tally.get("FAIL") or 0)
    not_run_count = int(tally.get("NOT RUN") or 0)
    return {
        "schema": 1,
        "kind": "headron_verification",
        "atlas_version": str(atlas().get("version")),
        "verifications": passed + failed + not_run_count,
        "pass": passed,
        "fail": failed,
        "not_run": not_run_count,
        "blocked": not report["merge_allowed"],
        "verdict": report["verdict"],
        "agent": (report.get("agent") or {}).get("agent"),
        "runtime": (report.get("agent") or {}).get("runtime"),
    }
