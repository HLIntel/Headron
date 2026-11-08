"""Claims: what Headron believes, the evidence for it, and everything that rests on it.

A claim is one belief a gate, a decision or a record was built on. It names its evidence, its label
(CONFIRMED, REPORTED, INFERRED or UNCERTAIN), where it was learned, and every dependent that rests on it.
An optional `refuted_if` lets an instrument refute it: the claim is false while `file` matches `matches`.

`headron revise <claim>` prints every dependent that rests on the claim, transitively through other
claims, and its exit code is the verdict: 0 when nothing needs revising, 1 when a refuted claim still
carries dependents, 2 for an unknown claim. `--on <ref>` names the claims a ref rests on, before an edit.

MEASURED ON fix/gate-adoption: "an .editorconfig adopts no formatter" was false. Headron's own shfmt is
configured by `switch_case_indent`, and only a full suite run after the edit found it. With that belief
recorded as a claim, `revise --on symbol:gateplace.unadopted` names it before the edit.

An adaptation (docs/systems/adaptations.yaml) is a change that says it made Headron better. It carries its
proof: hypothesis, intervention, expected gain, required proof, experiment, evidence, uncertainty, rollback
and validity scope, and rests on no refuted claim. The land runs `atlas check`, so a record that drops one is
refused before it merges.

proves: every claim is complete, every ref it names resolves, an instrument-refuted claim is not marked
  holds, and a refuted claim carries no dependent and names a holding successor; every adaptation names
  every proof field, evidence that resolves, and claims that hold
does_not_prove: that a claim marked holds is true, or that an adaptation's gain was real. Only a claim with
  `refuted_if` is checked against the tree, and an adaptation's evidence is checked to exist, not re-run
closed_by: claims_test.py, which plants each defect, the .editorconfig refutation and each adaptation defect
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from atlascore import ROOT, atlas, strict_yaml, text_of

REGISTRY = "docs/systems/claims.yaml"
LABELS = ("CONFIRMED", "REPORTED", "INFERRED", "UNCERTAIN")
STATUSES = ("holds", "refuted")
FIELDS = ("statement", "label", "evidence", "provenance", "status")
KINDS = ("claim", "decision", "judgment", "atlas", "file", "symbol")
ADAPTATIONS = "docs/systems/adaptations.yaml"
PROOF = ("hypothesis", "intervention", "expected_gain", "required_proof", "experiment", "evidence", "uncertainty")
ADAPTATION_FIELDS = (*PROOF, "rollback", "validity_scope")
ADAPTATION_OPTIONAL = ("rests_on", "landed_as")


def _yaml(path: Path) -> dict:
    return (strict_yaml(text_of(path), str(path)) or {}) if path.is_file() else {}


def records(root: Path = ROOT) -> dict:
    return _yaml(root / REGISTRY)


def unresolved(ref: str, claims: dict, root: Path = ROOT) -> str | None:
    """Why `ref` names nothing, or None when it names a real thing in the tree."""
    kind, _, name = str(ref).partition(":")
    if kind not in KINDS or not name:
        return f"{ref!r} is not <{'|'.join(KINDS)}>:<name>"
    if kind == "claim":
        return None if name in claims else f"{ref} names no claim"
    if kind in ("decision", "judgment"):
        return (
            None
            if name in _yaml(root / "docs" / "systems" / f"{kind}s.yaml")
            else f"{ref} names no record in docs/systems/{kind}s.yaml"
        )
    if kind == "file":
        return None if (root / name).is_file() else f"{ref} is not a file in the tree"
    if kind == "atlas":
        node: object = atlas() if root == ROOT else strict_yaml(text_of(root / "atlas.yaml"), "atlas.yaml")
        for key in name.split("/"):
            if not isinstance(node, dict) or key not in node:
                return f"{ref} names no atlas.yaml key ({key!r} is missing)"
            node = node[key]
        return None
    module, _, symbol = name.rpartition(".")
    source = root / "scripts" / f"{module}.py"
    if not module or not source.is_file():
        return f"{ref} names no module under scripts/"
    if not re.search(rf"(?m)^(?:def|class) {re.escape(symbol)}\b|^{re.escape(symbol)}\s*[:=]", text_of(source)):
        return f"{ref} names no top-level def, class or name in scripts/{module}.py"
    return None


def refuted_by(spec: dict, root: Path = ROOT) -> str | None:
    """What in the tree refutes the claim now, or None when no declared instrument does."""
    test = spec.get("refuted_if") or {}
    if not test:
        return None
    path = root / str(test.get("file", ""))
    try:
        hit = re.search(str(test.get("matches", "")), text_of(path, errors="replace"))
    except OSError:
        return None
    return f"{test['file']} matches /{test['matches']}/" if hit else None


def standing(spec: dict, root: Path = ROOT) -> str:
    return "refuted" if spec.get("status") == "refuted" or refuted_by(spec, root) else "holds"


def dependents(name: str, claims: dict) -> list[str]:
    """Every ref that rests on `name`, through any chain of claims, in first-reached order."""
    seen, order, queue = {name}, [], [name]
    while queue:
        for ref in (claims.get(queue.pop(0)) or {}).get("dependents") or []:
            ref = str(ref)
            if ref in order:
                continue
            order.append(ref)
            kind, _, child = ref.partition(":")
            if kind == "claim" and child not in seen:
                seen.add(child)
                queue.append(child)
    return order


def resting_on(ref: str, claims: dict) -> list[str]:
    """The claims `ref` rests on, directly or through a claim that rests on another."""
    return [name for name in claims if ref in dependents(name, claims)]


def claim_errors(claims: dict | None = None, root: Path = ROOT) -> list[str]:
    """Each claim complete and resolvable; a refuted one carries nothing and names a successor that holds."""
    claims = records(root) if claims is None else claims
    if not claims:
        return [f"{REGISTRY} holds no claims"]
    errors: list[str] = []
    for name, spec in claims.items():
        spec = spec or {}
        errors += [f"claim {name} declares no {f}" for f in FIELDS if not spec.get(f)]
        if spec.get("label") not in LABELS:
            errors.append(f"claim {name} label {spec.get('label')!r} is not one of {', '.join(LABELS)}")
        if spec.get("status") not in STATUSES:
            errors.append(f"claim {name} status {spec.get('status')!r} is not holds or refuted")
        refs = [*(spec.get("evidence") or []), *(spec.get("dependents") or [])]
        errors += [f"claim {name}: {why}" for r in refs if (why := unresolved(r, claims, root))]
        if (refuted := refuted_by(spec, root)) and spec.get("status") == "holds":
            errors.append(f"claim {name} is refuted ({refuted}) and still says it holds: `headron revise {name}`")
        if standing(spec, root) == "refuted":
            if live := dependents(name, claims):
                errors.append(f"claim {name} is refuted and {len(live)} dependents still rest on it: {', '.join(live)}")
            successor = str(spec.get("superseded_by") or "")
            if successor not in claims or standing(claims[successor] or {}, root) != "holds":
                errors.append(f"claim {name} is refuted and names no holding superseded_by claim")
    return errors


def adaptation_errors(adaptations: dict | None = None, claims: dict | None = None, root: Path = ROOT) -> list[str]:
    """Each adaptation names every proof field, evidence the tree holds, and claims that hold; nothing else."""
    adaptations = _yaml(root / ADAPTATIONS) if adaptations is None else adaptations
    claims = records(root) if claims is None else claims
    if not adaptations:
        return [f"{ADAPTATIONS} holds no adaptations"]
    errors: list[str] = []
    for name, spec in adaptations.items():
        spec = spec if isinstance(spec, dict) else {}
        errors += [f"adaptation {name} declares no {f}" for f in ADAPTATION_FIELDS if not spec.get(f)]
        known = (*ADAPTATION_FIELDS, *ADAPTATION_OPTIONAL)
        errors += [
            f"adaptation {name} names unknown field {f!r}; known: {', '.join(known)}" for f in spec if f not in known
        ]
        evidence = spec.get("evidence") or []
        if not isinstance(evidence, list):
            errors.append(f"adaptation {name} evidence is not a list of refs")
            evidence = []
        errors += [f"adaptation {name}: {why}" for r in evidence if (why := unresolved(r, claims, root))]
        for claim in spec.get("rests_on") or []:
            if claim not in claims:
                errors.append(f"adaptation {name} rests on {claim!r}, which names no claim in {REGISTRY}")
            elif standing(claims[claim] or {}, root) != "holds":
                errors.append(f"adaptation {name} rests on refuted claim {claim}: `headron revise {claim}`")
        landed = spec.get("landed_as")
        if landed is not None and not re.fullmatch(r"[\w.-]+/[\w.-]+#\d+", str(landed)):
            errors.append(f"adaptation {name} landed_as {landed!r} is not <owner>/<repo>#<number>")
    return errors


def revise(name: str | None, on: str | None, as_json: bool, root: Path = ROOT) -> int:
    """`headron revise [<claim>] [--on <ref>]`: what rests on a claim, or which claims a ref rests on."""
    claims = records(root)
    if on:
        found = resting_on(on, claims)
        row = {"schema": 1, "command": "revise", "on": on, "rests_on": found, "exit": 0}
        print(json.dumps(row) if as_json else "\n".join([f"{on} rests on {len(found)} claims", *found]))
        return 0
    if name is None:
        errors = claim_errors(claims, root)
        verdict = 1 if errors else 0
        print(
            json.dumps({"schema": 1, "command": "revise", "errors": errors, "exit": verdict})
            if as_json
            else "\n".join(errors or [f"{len(claims)} claims; nothing to revise"])
        )
        return verdict
    if name not in claims:
        why = f"no claim {name!r} in {REGISTRY}"
        print(
            json.dumps({"schema": 1, "command": "revise", "claim": name, "errors": [why], "exit": 2})
            if as_json
            else why
        )
        return 2
    spec, rest = claims[name] or {}, dependents(name, claims)
    state = standing(spec, root)
    verdict = 1 if state == "refuted" and rest else 0
    row = {
        "schema": 1,
        "command": "revise",
        "claim": name,
        "standing": state,
        "refuted_by": refuted_by(spec, root),
        "superseded_by": spec.get("superseded_by"),
        "dependents": rest,
        "exit": verdict,
    }
    if as_json:
        print(json.dumps(row))
    else:
        print(f"{name}: {state} ({spec.get('label')}) — {spec.get('statement')}")
        print(
            *(f"  {'revise' if state == 'refuted' else 'rests on it'}: {r}" for r in rest), sep="\n"
        ) if rest else None
        print(f"  superseded_by: {spec['superseded_by']}") if spec.get("superseded_by") else None
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="headron revise")
    parser.add_argument("claim", nargs="?")
    parser.add_argument("--on", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    return revise(args.claim, args.on, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
