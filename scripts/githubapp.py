#!/usr/bin/env python3
"""GitHub App groundwork: verify a pull-request diff, emit a check-run + THEA REPORT + metrics.

SCAFFOLD (3.56.0). The companion `atlas.yaml/companions/github_app` already names the install surface;
this module is the clean entry point that surface will call. It does not talk to the GitHub API yet —
it builds the three artifacts a future App handler posts:

  1. check-run payload   — name "Thea verify", conclusion from the verify exit code
  2. THEA REPORT comment — changed files, required gates, verdict, merge blocked/allowed
  3. metrics record      — verifications, pass/fail, blocked, agent — for a future dashboard

USAGE (local / CI dry-run):
  python scripts/githubapp.py --base <sha> [--head HEAD] [--json]
  THEA_BASE=<sha> THEA_AGENT=<id> python scripts/githubapp.py --base <sha>

WHAT IT DOES NOT PROVE: that GitHub accepted the check-run or that branch protection requires it.
`ghaudit.py` and the live App installation close those. This scaffold proves the verdict shape.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from atlascore import ROOT, atlas, diff_names
from runtime import resolve

CHECK_NAME = "Thea verify"
REPORT_HEADING = "## THEA REPORT"


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True, check=False, timeout=600)


def changed_files(base: str, head: str = "HEAD", tree: Path | None = None) -> list[str]:
    """Files the PR changes: base...head. An unresolvable base refuses rather than inventing []."""
    return diff_names(tree or ROOT, f"{base}...{head}")


def required_gates(files: list[str]) -> list[str]:
    """Gate ids the change class for these files would run — projection, not execution."""
    from agentpolicy import required_gates as _required  # noqa: PLC0415
    from branchstate import _consumer_change_class  # noqa: PLC0415

    change = _consumer_change_class() if files else "source_change"
    return list(_required({"change_class": change, "risk_modifiers": []}))


def run_verify(base: str, tree: Path | None = None) -> dict:
    """Run Thea verify against the PR base; capture exit and last marker when present."""
    env = {**os.environ, "THEA_BASE": base}
    cwd = tree or ROOT
    done = subprocess.run(  # noqa: S603
        [sys.executable, str(ROOT / "scripts" / "verify.py"), "--json", "--changed"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
        env=env,
    )
    payload: dict = {}
    if done.stdout.strip():
        try:
            payload = json.loads(done.stdout)
        except json.JSONDecodeError:
            payload = {"raw": done.stdout[-2000:]}
    return {"exit": done.returncode, "stderr_tail": (done.stderr or "")[-1000:], "verify": payload}


def verdict_of(exit_code: int) -> str:
    """PASS / FAIL / NOT RUN from verify's exit convention."""
    if exit_code == 0:
        return "PASS"
    if exit_code == 2:
        return "NOT RUN"
    return "FAIL"


def merge_allowed(verdict: str) -> bool:
    """Anything but PASS refuses the merge — same rule as agent run, commit hook, and CI."""
    return verdict == "PASS"


def check_run_payload(report: dict) -> dict:
    """GitHub check-run body shape (scaffold): name, conclusion, output summary."""
    verdict = report["verdict"]
    conclusion = {"PASS": "success", "FAIL": "failure", "NOT RUN": "neutral"}.get(verdict, "failure")
    return {
        "name": CHECK_NAME,
        "head_sha": report.get("head_sha"),
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": f"{CHECK_NAME}: {verdict}",
            "summary": report["comment_markdown"].split("\n", 2)[-1][:1000],
            "text": report["comment_markdown"],
        },
    }


def comment_markdown(report: dict) -> str:
    """THEA REPORT body posted on the pull request."""
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
    lines += ["", f"_Contract v{atlas().get('version')} · scaffold only — posts when the App is wired._"]
    return "\n".join(lines) + "\n"


def metrics_record(report: dict) -> dict:
    """Minimal metrics a future dashboard reads: counts, blocked, agent."""
    tally = (report.get("verify") or {}).get("tally") or {}
    passed = int(tally.get("PASS") or 0) + int(tally.get("REUSED") or 0)
    failed = int(tally.get("FAIL") or 0)
    not_run = int(tally.get("NOT RUN") or 0)
    return {
        "schema": 1,
        "kind": "thea_verification",
        "atlas_version": str(atlas().get("version")),
        "verifications": passed + failed + not_run,
        "pass": passed,
        "fail": failed,
        "not_run": not_run,
        "blocked": not report["merge_allowed"],
        "verdict": report["verdict"],
        "agent": (report.get("agent") or {}).get("agent"),
        "runtime": (report.get("agent") or {}).get("runtime"),
    }


def build_report(base: str, head: str = "HEAD", tree: Path | None = None, execute: bool = True) -> dict:
    """Assemble check-run, comment, and metrics from a PR base/head pair."""
    tree = tree or ROOT
    head_sha = _git("rev-parse", head, cwd=tree).stdout.strip() or head
    try:
        files = changed_files(base, head, tree)
        files_error = ""
    except ValueError as err:
        files, files_error = [], str(err)
    gates = required_gates(files)
    agent = resolve()
    verify_result = run_verify(base, tree) if execute else {"exit": 2, "verify": {}, "stderr_tail": "dry-run"}
    if files_error and execute:
        # An unresolvable base is incomplete, never a green merge.
        verify_result = {**verify_result, "exit": 2, "files_error": files_error}
    verdict = verdict_of(int(verify_result.get("exit") or 1))
    report = {
        "base": base,
        "head": head,
        "head_sha": head_sha,
        "changed_files": files,
        "required_gates": gates,
        "verdict": verdict,
        "merge_allowed": merge_allowed(verdict),
        "agent": agent,
        "verify": verify_result.get("verify") or {},
        "files_error": files_error,
    }
    report["comment_markdown"] = comment_markdown(report)
    report["check_run"] = check_run_payload(report)
    report["metrics"] = metrics_record(report)
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="githubapp.py", description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--base", required=True, help="PR base commit or ref (sets THEA_BASE for verify)")
    parser.add_argument("--head", default="HEAD", help="PR head commit or ref")
    parser.add_argument("--dry-run", action="store_true", help="shape only: skip running verify")
    parser.add_argument("--json", action="store_true", help="emit the full report record")
    parser.add_argument("--metrics-only", action="store_true", help="emit only the metrics record")
    args = parser.parse_args(argv)
    report = build_report(args.base, args.head, execute=not args.dry_run)
    if args.metrics_only:
        print(json.dumps(report["metrics"], indent=2, sort_keys=True))
    elif args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(report["comment_markdown"], end="")
        print(f"check-run conclusion: {report['check_run']['conclusion']}")
        print(f"metrics: {json.dumps(report['metrics'], sort_keys=True)}")
    return 0 if report["merge_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
