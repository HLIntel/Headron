"""Propose: a loop that reads what Headron believes, drafts the revision, and never lands it.

`headron propose` finds every claim the tree refutes that still carries dependents, the case
`headron revise` exits 1 on, and writes one adaptation draft per claim under HEADRON_HOME/drafts/.
A draft names the refutation, the dependents to revise and the holding successor. It leaves the
expected gain, the proof, the experiment, the uncertainty, the rollback and the validity scope empty,
because only a person who runs the change can fill them. `headron propose --check <draft>` holds a
draft to the adaptation contract in docs/systems/adaptations.yaml and names every field it still lacks.

Drafts live outside the tree. A drafts directory that resolves inside the atlas or the worktree is
refused and nothing is written, so a draft cannot reach a commit by being in the checkout. The loop
cannot land either: forbidden_calls/propose_never_lands refuses any process call in this file, so a
commit, a push or a deploy is a lane a person starts, as the adaptations header says.

proves: every refuted claim that still carries dependents gets one draft, the drafts land under
  HEADRON_HOME and never inside the atlas or the worktree, and a draft is held to every adaptation proof
  field before a person promotes it
does_not_prove: that a draft's revision is right, or that the person who promotes it filled the proof
  honestly. forbidden_calls sees `module.attr(...)` calls only, so a call by bare name
  (`from subprocess import run`) or through another module that lands is not refused by the row
closed_by: propose_test.py, which plants a refuted claim, a drafts directory inside the tree and an
  incomplete draft; atlas_rules_test.py, which plants a git commit into this file
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import atomicfile
import claims
from atlascore import ROOT, headron_home, resolved_once, strict_yaml, text_of, worktree

# A person fills these: the loop observed the refutation, it did not run the change.
LEFT_FOR_A_PERSON = ("expected_gain", "required_proof", "experiment", "uncertainty", "rollback", "validity_scope")


def drafts_dir() -> Path:
    return headron_home() / "drafts"


def inside_tree(path: Path, root: Path = ROOT) -> str | None:
    """The tree a path resolves into, the atlas or the worktree a command acts on, or None outside both."""
    trees = [resolved_once(root)]
    try:
        trees.append(worktree())
    except ValueError:
        pass  # outside any git repository: the atlas is the only tree to keep drafts out of
    real = path.resolve()
    return next((str(t) for t in trees if real == t or t in real.parents), None)


def observed(root: Path = ROOT) -> dict[str, dict]:
    """claim -> draft for every refuted claim that still carries dependents."""
    registry = claims.records(root)
    out: dict[str, dict] = {}
    for name, spec in sorted(registry.items()):
        spec = spec if isinstance(spec, dict) else {}
        rest = claims.dependents(name, registry)
        if claims.standing(spec, root) != "refuted" or not rest:
            continue
        successor = str(spec.get("superseded_by") or "")
        holding = successor in registry and claims.standing(registry[successor] or {}, root) == "holds"
        why = claims.refuted_by(spec, root) or "its status is refuted"
        draft = {
            "hypothesis": f"claim {name} is refuted ({why}), so the {len(rest)} dependents resting on it rest on a "
            "false belief",
            "intervention": "revise each dependent onto "
            + (f"the holding claim {successor}" if holding else "a holding claim this draft does not name")
            + ": "
            + ", ".join(rest),
            "evidence": [f"claim:{name}"],
            **({"rests_on": [successor]} if holding else {}),
            **dict.fromkeys(LEFT_FOR_A_PERSON, ""),
        }
        out[name] = {f"revise_{name}": draft}
    return out


def propose(as_json: bool, root: Path = ROOT, target: Path | None = None) -> int:
    """Write one draft per refuted claim with dependents. 0 nothing to propose, 1 drafts wait, 2 refused."""
    target = drafts_dir() if target is None else target
    row: dict = {"schema": 1, "command": "propose", "drafts_dir": str(target)}
    if tree := inside_tree(target, root):
        why = f"{target} resolves inside {tree}; a draft lives outside the tree, so HEADRON_HOME must too"
        row |= {"drafts": [], "errors": [why], "exit": 2}
        print(json.dumps(row) if as_json else f"REFUSED: {why}")
        return 2
    found = observed(root)
    written = []
    for name, draft in found.items():
        path = target / f"revise-{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomicfile.write_text(path, json.dumps(draft, indent=2) + "\n")
        written.append(str(path))
    verdict = 1 if written else 0
    row |= {"proposed": sorted(found), "drafts": written, "exit": verdict}
    lines = [f"draft for {n}: {p}" for n, p in zip(sorted(found), written, strict=True)]
    print(
        json.dumps(row) if as_json else "\n".join(lines or ["nothing to propose: no refuted claim carries dependents"])
    )
    return verdict


def check(draft: str, as_json: bool, root: Path = ROOT) -> int:
    """Hold a draft to the adaptation contract: every proof field, resolving evidence, holding claims."""
    path = Path(draft)
    try:
        parsed = strict_yaml(text_of(path), str(path))
    except (OSError, ValueError) as error:
        parsed, errors = None, [f"{draft} does not read as a draft: {error}"]
    else:
        errors = (
            claims.adaptation_errors(parsed, claims.records(root), root)
            if isinstance(parsed, dict) and parsed
            else [f"{draft} holds no adaptation"]
        )
    verdict = 1 if errors else 0
    row = {"schema": 1, "command": "propose", "check": draft, "errors": errors, "exit": verdict}
    print(json.dumps(row) if as_json else "\n".join(errors or [f"{draft} is complete; a person promotes it"]))
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="headron propose")
    parser.add_argument("--check", default=None, metavar="DRAFT")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    return check(args.check, args.json) if args.check else propose(args.json)


if __name__ == "__main__":
    raise SystemExit(main())
