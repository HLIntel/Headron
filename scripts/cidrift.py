#!/usr/bin/env python3
"""Drift guard: every script a CI workflow runs is a declared gate, or is named as CI-only.

CI and the local done set are two lists of the same gates. Before this guard a script added to a
workflow ran only there, so the same tree went green locally and was never judged on the other side.
A `scripts/*.py` the workflow runs must be either named by a done_set argv (run here too) or listed
under verification_policy.ci_only with the reason it runs only in CI. A ci_only entry no workflow
still runs is stale and fails too, so the list cannot quietly outlive the step it explains.

  python scripts/cidrift.py check     exit 0 when the two lists agree, 1 with the drift named
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from atlascore import strict_yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = re.compile(r"(?<![\w/.-])(scripts/[\w.-]+\.py)\b")


def workflow_files(root: Path = ROOT) -> list[Path]:
    """Every workflow-schema file: what GitHub can start (.github/workflows) and what only the local replay
    starts (ci/). The checks hold both to one standard, so moving a job out of reach of a runner never
    moves it out of reach of a check."""
    return sorted(p for d in (root / ".github" / "workflows", root / "ci") for p in d.glob("*.y*ml"))


def script_refs(workflow_text: str) -> set[str]:
    """Every scripts/*.py named inside a `run:` step of one workflow."""
    doc = strict_yaml(workflow_text, "workflow") or {}
    refs: set[str] = set()
    for job in (doc.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            run = step.get("run")
            if isinstance(run, str):
                refs.update(SCRIPT.findall(run))
    return refs


def declared(done_argvs: list[list[str]], ci_only: dict[str, str]) -> set[str]:
    """Scripts the local done set runs, plus the ones named as CI-only."""
    names = set(ci_only)
    for argv in done_argvs:
        names.update(arg for arg in argv if arg.startswith("scripts/"))
    return names


def drift(
    workflow_texts: list[str], done_argvs: list[list[str]], ci_only: dict[str, str]
) -> tuple[list[str], list[str]]:
    """(undeclared, stale): CI-run scripts nothing declares, and ci_only entries CI no longer runs."""
    seen: set[str] = set()
    for text in workflow_texts:
        seen |= script_refs(text)
    undeclared = sorted(seen - declared(done_argvs, ci_only))
    stale = sorted(name for name in ci_only if name.startswith("scripts/") and name not in seen)
    return undeclared, stale


def check(root: Path = ROOT) -> tuple[int, str]:
    policy = strict_yaml((root / "atlas.yaml").read_text(), "atlas.yaml")["verification_policy"]
    done_argvs = [row["argv"] for row in policy["done_set"]]
    ci_only = policy.get("ci_only") or {}
    workflows = [path.read_text() for path in workflow_files(root)]
    undeclared, stale = drift(workflows, done_argvs, ci_only)
    if not undeclared and not stale:
        return 0, f"cidrift: {len(ci_only)} CI-only scripts declared, every CI script is a gate or named CI-only"
    lines = [f"  undeclared (CI runs it, done set does not): {name}" for name in undeclared]
    lines += [f"  stale ci_only (no workflow runs it): {name}" for name in stale]
    return 1, "cidrift: CI and the done set disagree\n" + "\n".join(lines)


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):  # a script with no parser would RUN on --help
        print((__doc__ or "").strip())
        sys.exit(0)
    if sys.argv[1:] != ["check"]:
        sys.exit("usage: python scripts/cidrift.py check")
    code, message = check()
    print(message)
    sys.exit(code)
