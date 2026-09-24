#!/usr/bin/env python3
"""ghaudit — does the LIVE GitHub configuration match config/github-controls.json?

WHY THIS EXISTS (1.3.0). The platform state used to be typed into SECURITY.md and
docs/GITHUB-FINALIZATION.md with a measurement date beside it. That is honest on the day it is
written and unfalsifiable afterwards: three lines of a previous audit had gone stale and read as
current, and the only way to notice was to re-run the commands by hand and compare by eye. State
in prose cannot be compared by a machine, so it rots quietly. This file makes the comparison
mechanical, and the documents now name the instrument instead of repeating its answer.

THREE LAYERS, KEPT SEPARATE, because a control can exist in the first two and stop nothing:
  declared   — config/github-controls.json, in Git, reviewed like code
  configured — what the GitHub API reports right now
  enforced   — a merge is actually refused without it, which required_status_checks decides

IT REFUSES RATHER THAN REPORTS when it cannot reach the API (exit 2). A green line printed by an
audit that never called anything is the exact failure this repository exists to prevent.

  python scripts/ghaudit.py            # compare, print every row, exit 1 on any difference
  python scripts/ghaudit.py --json     # the same comparison as a record

BYPASS IS PRINTED, NOT ASSUMED AWAY: a rule with a bypass actor is enforced for everyone except
that actor, and the reader has to be told who that is.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECLARED = "config/github-controls.json"
TIMEOUT = 30


def api(path: str) -> object:
    """One read-only GitHub API call through the gh CLI, or a refusal."""
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=TIMEOUT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"gh api {path}: {result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'failed'}")
    return json.loads(result.stdout)


def main(argv: list[str]) -> int:
    declared = json.loads((ROOT / DECLARED).read_text(encoding="utf-8"))
    repo = declared["repository"]
    if not shutil.which("gh"):
        print("ghaudit: the gh CLI is not installed — REFUSING rather than reporting a state it did not measure")
        return 2
    try:
        live = api(f"repos/{repo}")
        rulesets = api(f"repos/{repo}/rulesets")
        pvr = api(f"repos/{repo}/private-vulnerability-reporting")
    except (RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"ghaudit: cannot read the GitHub API — REFUSING rather than guessing ({exc})")
        print("  authenticate with `gh auth login`; a report is worthless if the call did not happen")
        return 2

    rows: list[tuple[str, object, object]] = [
        ("visibility", declared["visibility"], live.get("visibility")),
        ("default branch", declared["default_branch"], live.get("default_branch")),
        ("licence", declared["license_spdx"], (live.get("license") or {}).get("spdx_id")),
        ("topics", sorted(declared["topics"]), sorted(live.get("topics") or [])),
        ("private vulnerability reporting",
         declared["private_vulnerability_reporting"],
         "enabled" if (pvr or {}).get("enabled") else "disabled"),
    ]
    analysis = live.get("security_and_analysis") or {}
    blocked: list[tuple[str, str, str]] = []
    for key, want in declared["security_and_analysis"].items():
        got = (analysis.get(key) or {}).get("status")
        # A DECLARED CONTROL THE PLATFORM REFUSES IS NOT A FAILING CHECK — a row that can never go
        # green gets ignored, and an ignored row hides the ones that matter. It is reported as
        # BLOCKED with the cause that was measured, and it becomes a DIFF the day the cause ends.
        if isinstance(want, dict):
            if got == want.get("accept"):
                blocked.append((key.replace("_", " "), str(want.get("want")), str(want.get("blocked_by"))))
                continue
            want = want.get("want")
        rows.append((key.replace("_", " "), want, got))

    want_rules = declared["ruleset"]
    found = next((r for r in rulesets if r.get("name") == want_rules["name"]), None)
    detail = api(f"repos/{repo}/rulesets/{found['id']}") if found else {}
    rows.append((f"ruleset {want_rules['name']}", want_rules["enforcement"],
                 (found or {}).get("enforcement", "absent")))
    rows.append(("ruleset rules", sorted(want_rules["rules"]),
                 sorted(r["type"] for r in detail.get("rules", []))))
    live_checks = [c["context"] for rule in detail.get("rules", [])
                   if rule["type"] == "required_status_checks"
                   for c in rule["parameters"]["required_status_checks"]]
    rows.append(("required status checks", sorted(want_rules["required_status_checks"]), sorted(live_checks)))

    differences = [(label, want, got) for label, want, got in rows if want != got]
    bypass = detail.get("bypass_actors") or []

    if "--json" in argv:
        print(json.dumps({
            "schema": 1, "command": "ghaudit", "repository": repo,
            "rows": [{"control": label, "declared": want, "measured": got, "match": want == got}
                     for label, want, got in rows],
            "blocked": [{"control": label, "wanted": want, "blocked_by": why} for label, want, why in blocked],
            "differences": len(differences), "bypass_actors": bypass,
        }, indent=2))
        return 1 if differences else 0

    print(f"ghaudit — {repo}, declared in {DECLARED}, measured through `gh api`\n")
    width = max(len(label) for label, _, _ in rows)
    for label, want, got in rows:
        mark = "ok  " if want == got else "DIFF"
        shown_want = ", ".join(want) if isinstance(want, list) else want
        shown_got = ", ".join(got) if isinstance(got, list) else got
        print(f"{mark} {label.ljust(width)}  declared {shown_want}")
        if want != got:
            print(f"     {' ' * width}  measured {shown_got}")
    for label, want, why in blocked:
        print(f"BLKD {label.ljust(width)}  wanted {want}, and the platform refuses it")
        for line in textwrap.wrap(why, 96, initial_indent="     " + " " * width + "  ", subsequent_indent="     " + " " * width + "  "):
            print(line)
    print(f"\n{len(rows) - len(differences)}/{len(rows)} declared controls match, "
          f"{len(blocked)} blocked by the platform with the cause printed above")
    for actor in bypass:
        print(f"BYPASS  {actor.get('actor_type')} id={actor.get('actor_id')} mode={actor.get('bypass_mode')} "
              "— every rule above is advisory for this actor, by design")
    if differences:
        print(f"\n{len(differences)} DIFF row(s): a control declared here that the platform does not")
        print("have. Fix it at the platform, or change the declaration and say why — leaving the two")
        print("apart is how a control ends up on the roster and stops nothing.")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
