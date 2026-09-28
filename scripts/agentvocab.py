#!/usr/bin/env python3
"""The words a task contract may use for WHO does it, WITH WHAT, and IN WHICH LANGUAGES.

WHY (3.36.0). A contract could say what it touches, what it may do and what it must prove — and not
one word about the agent, the model, the skills loaded, or the languages the work spans. Every one of
those had a roster in this atlas already: `agent_roles`, `model_routes`, `skills/`, and the 36
routes. The vocabulary was declared everywhere and namable nowhere, so a program could not carry the
identity of the thing that would run it.

NOTHING HERE IS A NEW ROSTER. Each word resolves against one that exists, which is the whole bar for
adding a word at all: a keyword that resolves against nothing is free text, and free text in a
contract is the field nobody can refuse.

THE TWO CROSS-CHECKS ARE THE POINT.
  * A ROLE CARRIES A TASK PROFILE. `agent_roles/implementer` declares `task_profile:
    implementation`; a contract naming that role and a different profile is claiming a role it is
    not running as, and both fields read as satisfied on their own.
  * MORE THAN ONE `use` IS A BOUNDARY. `authority_classes/boundary` states it plainly — NOTHING IN
    ONE PACK answers a boundary, because a boundary is a contract between two. So a program spanning
    two packs must carry the polyglot profile, whose boundary test is what closes it.

WHAT IT DOES NOT PROVE: that the named model ran, or that the named skills were loaded. Those are the
host's to observe, exactly like the sandbox rows `agentrun` prints UNOBSERVED. This proves the
declaration is INTERNALLY consistent and resolves — never that the world matched it.
"""
from __future__ import annotations

import sys

from atlascore import ROOT, atlas, route_targets


def _skill_names() -> set[str]:
    """Every skill in the tree, FROM the tree. A typed list here would narrow the moment one is
    added beside it, which is the roster shape this repository refuses six times over."""
    root = ROOT / "skills"
    if not root.is_dir():
        return set()
    # DIRECTORIES ONLY. The first draft took every entry's stem and picked up the generated
    # `skills/THEA.md` as a skill named THEA — a roster that counted a page as a capability.
    return {p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")}


def uses_errors(contract: dict) -> list[str]:
    """`use <route>`: every language the work spans, and the boundary that more than one implies."""
    errors: list[str] = []
    uses = [str(u) for u in contract.get("uses") or []]
    packs = set(route_targets())
    for route in uses:
        if route not in packs:
            errors.append(f"contract.uses names '{route}', which is not a route in this atlas — "
                          "a language the work spans but the router cannot resolve has no gates, "
                          "no manifest and no authority to answer for it")
    route = str(contract.get("route") or "")
    if uses and route and route not in uses:
        errors.append(f"contract.route is '{route}' and contract.uses does not name it — the pack "
                      "the task was ROUTED to must be one of the packs it declares it spans")
    if len(uses) > 1 and str(contract.get("task_profile")) != "polyglot":
        errors.append(f"contract.uses spans {len(uses)} packs and task_profile is "
                      f"'{contract.get('task_profile')}' — atlas.yaml/authority_classes/boundary "
                      "says nothing in ONE pack answers a boundary, because a boundary is a "
                      "contract between two; the polyglot profile is what carries its test")
    return errors


def identity_errors(contract: dict) -> list[str]:
    """`model`, `agent`, `skill`: who runs this, on what, with which instructions loaded."""
    errors: list[str] = []
    model = str(contract.get("model") or "")
    routes = atlas().get("model_routes") or {}
    if model and model not in routes:
        errors.append(f"contract.model names '{model}', which atlas.yaml/model_routes does not "
                      f"declare (declared: {', '.join(sorted(routes))})")
    role_name = str(contract.get("agent_role") or "")
    roles = atlas().get("agent_roles") or {}
    if role_name:
        role = roles.get(role_name)
        if not isinstance(role, dict):
            errors.append(f"contract.agent_role names '{role_name}', which atlas.yaml/agent_roles "
                          f"does not declare (declared: {', '.join(sorted(roles))})")
        else:
            declared_profile = str(role.get("task_profile") or "")
            if declared_profile and declared_profile != str(contract.get("task_profile")):
                errors.append(
                    f"contract.agent_role is '{role_name}', which runs as task_profile "
                    f"'{declared_profile}', and this contract declares "
                    f"'{contract.get('task_profile')}' — a role and a profile that disagree both "
                    "read as satisfied on their own, and the one that bounds the work is the profile")
    available = _skill_names()
    for skill in (str(s) for s in contract.get("skills") or []):
        if skill not in available:
            errors.append(f"contract.skills names '{skill}', which is not in skills/ — an "
                          "instruction set a task says it loads and the tree does not carry is a "
                          "capability nobody can produce")
    return errors


def _parts(version: str) -> tuple:
    try:
        return tuple(int(piece) for piece in str(version).split("."))
    except ValueError:
        return ()


def floor_errors(contract: dict) -> list[str]:
    """A checker older than the contract's declared floor REFUSES, never reports a partial pass.

    HARVESTED FROM Go's `go`/`toolchain` directive (mandatory since 1.21): a module declaring a
    newer Go version is refused outright rather than built best-effort, so an old toolchain never
    silently checks the subset of rules it happens to understand.

    THE HOLE IT CLOSES WAS MEASURED, not imagined: at contract 3.37.0 the installed `thea` on this
    machine reported 3.35.0 — two versions behind, answering questions about rules it did not carry,
    with nothing in either one saying so. `atlas_version` records which atlas WROTE a contract; this
    records which atlas may JUDGE it, and they are different questions.

    IT IS THE OTHER DIRECTION FROM A BLIND CHECK. A check whose INPUT is missing reports NOT RUN; a
    check whose RULES are missing must refuse — otherwise absence of a rule reads as absence of a
    finding.
    """
    floor = str(contract.get("min_contract_version") or "")
    if not floor:
        return []
    here = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    want, have = _parts(floor), _parts(here)
    if not want:
        return [f"contract.min_contract_version '{floor}' is not a version this checker can compare"]
    if have < want:
        return [f"contract.min_contract_version is {floor} and this checker is {here} — REFUSED "
                "rather than judged, because a checker older than the rules a contract was written "
                "against can only report that it found nothing wrong in the part it understands"]
    return []


def contract_vocabulary_errors(contract: dict) -> list[str]:
    """Every half, for `agentpolicy.contract_errors` to call once."""
    return uses_errors(contract) + identity_errors(contract) + floor_errors(contract)


def main(argv: list[str]) -> int:
    """`thea agentvocab <contract>` — the words this contract uses, and whether each resolves."""
    import json

    import thealang
    if not argv:
        print(f"routes {len(route_targets())} | models {len(atlas().get('model_routes') or {})} | "
              f"roles {len(atlas().get('agent_roles') or {})} | skills {len(_skill_names())}")
        return 0
    contract = thealang.load_contract(argv[0])
    problems = contract_vocabulary_errors(contract)
    print(json.dumps({"uses": contract.get("uses") or [], "model": contract.get("model"),
                      "agent_role": contract.get("agent_role"),
                      "skills": contract.get("skills") or [],
                      "findings": problems}, indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
