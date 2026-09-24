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

  python scripts/ghaudit.py                  # compare, print every row, exit 1 on any difference
  python scripts/ghaudit.py --json           # the same comparison as a record
  python scripts/ghaudit.py --print-ruleset  # the exact PUT body, generated from the declaration

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
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DECLARED = "config/github-controls.json"
# The GitHub Actions app, which is what a required check run belongs to. Pinning the
# integration prevents another app reporting a context with the same name.
ACTIONS_APP_ID = 15368
TIMEOUT = 30


def api(path: str) -> object:
    """One read-only GitHub API call through the gh CLI, or a refusal."""
    result = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=TIMEOUT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"gh api {path}: {result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'failed'}")
    return json.loads(result.stdout)


def ruleset_payload(declared: dict) -> dict:
    """The COMPLETE ruleset PUT body, generated from the declaration.

    WHY THIS EXISTS. The rulesets API replaces the rules it is given and drops every parameter the
    payload omits, so a hand-written partial body reverts settings it never mentions — silently,
    with a 200. That is exactly what happened to `dismiss_stale_reviews_on_push` and
    `required_review_thread_resolution`. A payload nobody types cannot be partial:

        python scripts/ghaudit.py --print-ruleset | gh api -X PUT repos/OWNER/REPO/rulesets/ID --input -
    """
    want = declared["ruleset"]
    parameters = dict(want.get("pull_request_parameters") or {})
    parameters.setdefault("require_extra_approval_for_unattributed_changes", False)
    rules: list[dict] = [{"type": kind} for kind in
                         ("deletion", "non_fast_forward", "required_linear_history")
                         if kind in want["rules"]]
    if "pull_request" in want["rules"]:
        rules.append({"type": "pull_request", "parameters": parameters})
    if "required_status_checks" in want["rules"]:
        rules.append({"type": "required_status_checks", "parameters": {
            "strict_required_status_checks_policy": True,
            "do_not_enforce_on_create": False,
            "required_status_checks": [{"context": context, "integration_id": ACTIONS_APP_ID}
                                       for context in sorted(want["required_status_checks"])],
        }})
    return {"name": want["name"], "target": "branch", "enforcement": want["enforcement"],
            "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
            "bypass_actors": want.get("bypass_actors", []), "rules": rules}


def print_arm_values(card: dict, live: dict, published: float) -> None:
    """What closing each open arm is WORTH, computed rather than guessed.

    THE MODEL IS CHECKED BEFORE IT IS TRUSTED. Scorecard's aggregate is a weighted mean over the
    checks that returned a score; inconclusive checks (-1) are excluded. If recomputing the
    published number from the declared weights disagrees with the published number, the weights
    are wrong — and this says so instead of projecting from a broken model, because a projection
    with no control is the most persuasive kind of wrong.
    """
    weights = {k: v for k, v in (card.get("check_weights") or {}).items() if not k.startswith("_")}
    scored = {name: score for name, score in live.items() if score >= 0 and name in weights}
    if not scored:
        return
    total = sum(weights[name] for name in scored)
    computed = sum(weights[name] * score for name, score in scored.items()) / total
    if abs(computed - published) > 0.05:
        print(f"     the declared weights recompute the aggregate as {computed:.2f} against a published "
              f"{published} — the weight model is WRONG, so no projection is printed")
        return
    print(f"     weight model reproduces the published score ({computed:.2f}); each open arm is worth:")
    for name, score in sorted(scored.items(), key=lambda kv: kv[1]):
        if score >= 10:
            continue
        lifted = dict(scored, **{name: 10})
        gain = sum(weights[n] * s for n, s in lifted.items()) / total - computed
        print(f"       +{gain:0.2f}  {name} at {score} -> 10 (weight {weights[name]})")
    for name in sorted(set(weights) - set(scored)):
        lifted = dict(scored, **{name: 10})
        gain = (sum(weights[n] * s for n, s in lifted.items()) / (total + weights[name])) - computed
        print(f"       +{gain:0.2f}  {name} inconclusive -> 10 (weight {weights[name]}, adds to the denominator)")
    print()


def main(argv: list[str]) -> int:
    declared = json.loads((ROOT / DECLARED).read_text(encoding="utf-8"))
    repo = declared["repository"]
    if "--print-ruleset" in argv:
        print(json.dumps(ruleset_payload(declared), indent=2))
        return 0
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

    for key, want in (declared.get("settings") or {}).items():
        if key.startswith("_"):
            continue
        rows.append((key.replace("_", " "), want, live.get(key)))

    hooks = api(f"repos/{repo}/hooks")
    rows.append(("webhooks", declared["webhooks"]["count"], len(hooks)))

    envs = api(f"repos/{repo}/environments")
    live_envs = sorted(e["name"] for e in (envs.get("environments") or []))
    rows.append(("environments", sorted(declared["environments"]["names"]), live_envs))
    # AN ENVIRONMENT IS WHERE A SECRET HIDES FROM A REPOSITORY-LEVEL SCAN, so each one is opened.
    #
    # THE VERDICT IS A PROPERTY, NOT A NUMBER, AND THAT IS NOT COSMETIC. CodeQL flagged the earlier
    # version — `py/clear-text-logging-sensitive-data`, twice — because a value read from an endpoint
    # named `secrets` reached a print. It was only a count, so the alert was a false positive by
    # name; the fix is still the right code. This audit needs to know whether an environment holds
    # anything, not how much, and a boolean cannot leak a value even if the shape of this function
    # changes later. A suppression comment would have left that possible and called it handled.
    for name in live_envs:
        quoted = quote(name, safe="")
        reachable, empty = True, True
        for kind in ("secrets", "variables"):
            try:
                empty = empty and api(f"repos/{repo}/environments/{quoted}/{kind}").get("total_count") == 0
            except RuntimeError:
                reachable = False
        rows.append((f"environment {name!r} holds no credentials", True,
                     empty if reachable else "could not be read"))

    tags = {t["name"] for t in api(f"repos/{repo}/tags")}
    released = {r["tag_name"] for r in api(f"repos/{repo}/releases")}
    if declared.get("releases", {}).get("every_tag_has_a_release"):
        rows.append(("tags with no release", [], sorted(tags - released)))

    card = declared.get("scorecard") or {}
    if card:
        # THE AGGREGATE HIDES WHICH CHECK FELL. One check dropping while another rises leaves the
        # total unmoved, so every check carries its own floor and every shortfall is its own row.
        try:
            live_card = json.loads(urlopen(
                f"https://api.securityscorecards.dev/projects/github.com/{repo}", timeout=TIMEOUT
            ).read().decode())
            live_checks = {c["name"]: c["score"] for c in live_card.get("checks", [])}
            rows.append((f"scorecard aggregate >= {card['minimum']}", True,
                         live_card["score"] >= card["minimum"]))
            for name, floor in sorted((card.get("check_floors") or {}).items()):
                got = live_checks.get(name)
                if got is None:
                    rows.append((f"scorecard {name}", f">= {floor}", "not reported"))
                elif got < floor:
                    rows.append((f"scorecard {name}", f">= {floor}", got))
            below = [n for n, f in (card.get("check_floors") or {}).items()
                     if live_checks.get(n) is not None and live_checks[n] < f]
            print(f"note scorecard aggregate {live_card['score']} (floor {card['minimum']}), "
                  f"{len(card.get('check_floors') or {})} checks with a floor, {len(below)} below it")
            print_arm_values(card, live_checks, live_card["score"])
        except (URLError, OSError, ValueError, KeyError) as exc:
            print(f"note scorecard unread ({exc.__class__.__name__}) — REPORTED as unknown, never as passing\n")

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

    # A RULE PRESENT WITH THE WRONG PARAMETERS IS NOT A RULE THAT IS PRESENT. Comparing rule TYPES
    # reported "ok" over two branch-protection settings that had been switched back off by a
    # partial PUT — the API replaces a rule and drops what the payload omits.
    live_pr = next((r["parameters"] for r in detail.get("rules", []) if r["type"] == "pull_request"), {})
    for key, want in (want_rules.get("pull_request_parameters") or {}).items():
        got = live_pr.get(key)
        rows.append((f"ruleset pull_request.{key}",
                     sorted(want) if isinstance(want, list) else want,
                     sorted(got) if isinstance(got, list) else got))

    bypass = detail.get("bypass_actors") or []
    if "bypass_actors" in want_rules:
        # A BYPASS RE-ADDED THROUGH THE UI IS A SILENT RETURN TO ADVISORY RULES, so the roster is
        # compared rather than merely printed.
        rows.append(("ruleset bypass actors", len(want_rules["bypass_actors"]), len(bypass)))
    differences = [(label, want, got) for label, want, got in rows if want != got]

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
