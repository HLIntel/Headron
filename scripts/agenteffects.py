#!/usr/bin/env python3
"""Effects: what a task may DO, as a kind rather than as a path or a command name.

WHY (3.36.0). `network` was the only effect a contract could name and `acceptance/side_effects` the
only thing that said anything survived the run, so a task allowed to deploy, to spend or to start
another agent read exactly like one allowed to run a formatter — and the difference had to be
inferred from a command name, which is branching on a rendering (code-quality §3).

EVERY EFFECT IS DERIVED FROM THE CONTRACT'S OWN FIELDS, and the declaration is checked against the
derivation in BOTH directions. Under-declaring is the obvious failure. Over-declaring is refused
too: authority asked for and never exercised is the least-privilege invariant one level up, and it
is how an effect list becomes a habit nobody reads.

ITS OWN MODULE BECAUSE agentpolicy REACHED ITS LINE CAP, and a cap is never raised to fit new code.

WHAT IT DOES NOT PROVE: that a command exercises only the effects its name suggests. A pattern
reads the argv it is given; a program that shells out from inside is bounded by the host and by
`denied_commands`, not by this.
"""
from __future__ import annotations

import re
import shlex

from agentpolicy import Verdict, _resolves, policy


def effect_classes() -> dict:
    """atlas.yaml/agent_policy/effect_classes — the one roster of what a task may DO."""
    return policy().get("effect_classes") or {}


def argv_effects(argv: list[str]) -> set[str]:
    """The effects ONE command exercises, by the declared patterns. Public because `agentrun` reads
    it to report what a run actually exercised beside what its contract declared.

    A pattern rather than a roster of tool names: an enumerated list narrows the moment a new
    deployer or a new cloud CLI is installed beside it, and it narrows silently (code-quality §8).
    Running anything at all is `execute`, which is why the cheapest contract still names one effect
    rather than an empty list that reads as 'nothing decided'.
    """
    joined = shlex.join([str(a) for a in argv])
    found = {"execute"} if argv else set()
    for name, pattern in (policy().get("effect_patterns") or {}).items():
        if re.search(str(pattern), joined):
            found.add(str(name))
    return found & set(effect_classes())


def implied_effects(contract: dict) -> set[str]:
    """What the contract's OWN FIELDS say it may do — never what its prose says.

    Derived, so the declaration can be checked against it in both directions. The fields are the
    identity; `effects` is the claim, and a claim nothing derives is a label (code-quality §3).
    """
    commands = [str(c) for c in contract.get("allowed_commands") or []]
    implied = argv_effects(commands)
    if str(contract.get("network") or "denied") != "denied":
        implied.add("network")
    if str((contract.get("acceptance") or {}).get("side_effects")) == "external_with_approval":
        implied.add("external")
    return implied & set(effect_classes())


def contract_effect_errors(contract: dict) -> list[str]:
    """Both directions, and the approval each effect binds.

    UNDER-declaring is the obvious failure: a task that may deploy reading like one that may run a
    formatter. OVER-declaring is the quieter one and is refused too — authority asked for and not
    exercised is the least-privilege invariant one level up, and it is how an effect list becomes
    a habit nobody reads.
    """
    classes = effect_classes()
    errors: list[str] = []
    claimed = [str(e) for e in contract.get("effects") or []]
    for name in claimed:
        if name not in classes:
            errors.append(f"contract.effects names '{name}', which agent_policy/effect_classes "
                          f"does not declare (declared: {', '.join(sorted(classes))})")
    implied = implied_effects(contract)
    for name in sorted(implied - set(claimed)):
        errors.append(f"contract.effects omits '{name}', which this contract's own fields imply "
                      f"({classes[name]['implied_by']}) — an effect a reader must infer from a "
                      "command name is one the contract never declared")
    for name in sorted(set(claimed) & set(classes) - implied):
        errors.append(f"contract.effects claims '{name}', which nothing in this contract exercises "
                      "— authority asked for and not used is authority nobody will notice being used")
    errors += delegation_errors(contract)
    approvals = {str(a) for a in contract.get("approval_required") or []}
    for name in sorted(set(claimed) & set(classes)):
        if (classes[name] or {}).get("requires_approval") and name not in approvals:
            errors.append(f"contract.effects declares '{name}', which requires approval, and "
                          "approval_required does not name it — a high-impact effect with no token "
                          "to bind is the approval control declared and not reached")
    return errors


def effect_verdict(contract: dict, argv: list[str]) -> Verdict:
    """The sixth verdict: a command may not exercise an effect the contract did not declare.

    `command_verdict` answers whether the PROGRAM is allowed. This answers what running it DOES,
    which is a different question: `git` is an ordinary allowance and `git push` reaches a reader
    outside this repository. Both must pass before anything runs.
    """
    undeclared = sorted(argv_effects(argv) - {str(e) for e in contract.get("effects") or []})
    if undeclared:
        return Verdict(False, "effects", f"{shlex.join([str(a) for a in argv])!r} exercises "
                       f"{', '.join(undeclared)}, which this contract does not declare")
    return Verdict(True, "effects", "every effect this command exercises is declared")


def delegation_errors(contract: dict) -> list[str]:
    """A task that starts another task hands down a ceiling, and the ceiling is never larger.

    HARVESTED FROM Go's `context.Context` (mechanism, not syntax): a derived context carries a
    deadline no LATER than the one it derives from, so a child cannot outlive its parent by being
    asked nicely. Here the same shape in a declaration — `delegate_budget` is bounded by the
    contract's own budget on every axis it names.

    WHY IT WAS A HOLE. `delegate` has been a declarable effect since this module shipped, and
    `delegation_contract` names six things a handoff must carry — goal, scope, acceptance, returns,
    forbidden, read_only — and NOT ONE of them is a budget. So a bounded task could start an
    unbounded one and every control above it still read as satisfied. One process backing off does
    nothing if its siblings do not; the vendor, the quota and the clock see the SUM.
    """
    errors: list[str] = []
    declares = "delegate" in {str(e) for e in contract.get("effects") or []}
    handed = contract.get("delegate_budget")
    if declares and not handed:
        return ["contract declares the 'delegate' effect and no delegate_budget — a task that can "
                "start another task and states no ceiling for it is bounded on paper only, because "
                "every control it passes bounds the parent and none of them reaches the child"]
    if handed and not declares:
        errors.append("contract carries a delegate_budget and does not declare the 'delegate' "
                      "effect — a ceiling for a child it may not start bounds nothing")
    own = dict(contract.get("budgets") or {})
    for axis, value in (handed or {}).items():
        mine = own.get(axis)
        if mine is not None and int(value) > int(mine):
            errors.append(f"contract.delegate_budget.{axis} is {value} against its own {mine} — a "
                          "child may never be handed more than its parent holds, on any axis")
    return errors


def declaration_errors(declared: dict) -> list[str]:
    """The roster itself: every effect states its derivation, its refuser and whether it binds a
    token; every pattern compiles and names an effect the roster declares.

    A control with no enforcer is refused, and this section is subject to that rule like every
    other one — which is why `refused_by` is resolved against the tree rather than read.
    """
    errors: list[str] = []
    # EVERY CONTROL SAYS WHEN IT CAN STILL REFUSE. Harvested from Pingora, where a filter's power to
    # stop a request is a property of its PHASE rather than of what the filter does. This repository
    # had written that rule for exactly one control — "a budget checked afterwards is a report, not
    # a control" — and left the other five to be inferred, which is where a control that only
    # DESCRIBES gets read as one that PREVENTS.
    #
    # THIS CHECK WAS ITSELF AN UNSHIPPED ARM FOR ONE COMMIT: the declaration landed and the enforcer
    # did not, because its anchor had moved to this module in an earlier split. The planted case
    # refused to pass, which is exactly what a planted case is for.
    phases = [str(p) for p in declared.get("refusal_phases") or []]
    if not phases:
        errors.append("agent_policy declares no refusal_phases, so no control can say whether it "
                      "prevents an action or only describes one that already happened")
    for control, spec in (declared.get("controls") or {}).items():
        at = str((spec or {}).get("refuses_at") or "")
        if at not in phases:
            errors.append(f"agent_policy/controls/{control}/refuses_at '{at}' is not one of the "
                          f"declared refusal_phases ({', '.join(phases)}) — a control whose phase "
                          "nobody declared is one a reader assumes prevents something")
        if not str((spec or {}).get("phase_note") or "").strip():
            errors.append(f"agent_policy/controls/{control} states no phase_note — a phase is a "
                          "word until something says what it means for THIS control")
    classes = declared.get("effect_classes") or {}
    for name, row in classes.items():
        for field in ("means", "implied_by", "refused_by"):
            if not str((row or {}).get(field) or "").strip():
                errors.append(f"agent_policy/effect_classes/{name} leaves '{field}' empty — an "
                              "effect with no stated derivation or no refuser is a word in a list")
        if not _resolves(str((row or {}).get("refused_by"))):
            errors.append(f"agent_policy/effect_classes/{name}/refused_by "
                          f"'{(row or {}).get('refused_by')}' does not resolve to a callable")
        if not isinstance((row or {}).get("requires_approval"), bool):
            errors.append(f"agent_policy/effect_classes/{name}/requires_approval is not a boolean "
                          "— an effect that does not say whether it needs a token is decided by "
                          "whoever reads it next")
    for name, pattern in (declared.get("effect_patterns") or {}).items():
        if name not in classes:
            errors.append(f"agent_policy/effect_patterns/{name} implies an effect "
                          "agent_policy/effect_classes does not declare")
        try:
            re.compile(str(pattern))
        except re.error as exc:
            errors.append(f"agent_policy/effect_patterns/{name} is not a regular expression: {exc}")
    return errors
