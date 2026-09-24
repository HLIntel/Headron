#!/usr/bin/env python3
"""The agent execution policy: five verdicts, decided from a declaration rather than from prose.

WHY THIS EXISTS (2.9.0). `atlas.yaml/task_profiles/autonomous_agent` has named five controls
since 2.0.0 — narrow_tools, sandbox, budget, approval, audit — and nothing in this tree enforced
one of them. An agent that never opened CLAUDE.md was subject to none of them, and from outside
a declared control and an enforced control print the same word. That is the same shape this
repository already refuses three times over: an invariant with no check, an instrument with no
closer, a roster with no count.

WHAT IT DECIDES AND WHAT IT CANNOT. Every function here is PURE: it takes a contract, a subject
and the declaration, and returns a verdict naming the control that refused. It therefore proves
exactly one thing — that a caller which ASKS is bounded. An agent that does not ask is bounded
by the host, which is why `agent_policy/sandbox_requirements` marks each row with who observes it
and why `agentrun.py` prints the host-observed ones as UNOBSERVED rather than as satisfied.

THE CONTRACT'S OWN BUDGETS ARE A PREFERENCE. A contract is written by the same agent these
controls bound, so `effective_budgets` takes the LOWER of the declaration and the contract —
never the contract alone.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import re
import shlex
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

from atlascore import ROOT, atlas, read, strict_yaml
from packmanifest import entry_commands, manifest_schema, validate

# A shell in `allowed_commands` allows every command, so the allowance means nothing. These names
# are refused AS ALLOWANCES — the contract is rejected, rather than the call being refused later,
# because a contract that would permit everything should not validate in the first place.
SHELL_NAMES = frozenset({"sh", "bash", "zsh", "fish", "dash", "ksh", "csh", "tcsh",
                         "env", "eval", "exec", "xargs", "nohup", "setsid"})
CONTRACT_SCHEMA = "tools/agent-task.schema.json"


class Verdict(NamedTuple):
    """A decision and the CONTROL that made it.

    `allowed` alone would be a boolean nobody can act on: a refusal that does not name which of the
    five controls fired cannot be argued with, cannot be audited, and gets worked around.
    """
    allowed: bool
    control: str
    reason: str


def policy() -> dict:
    """atlas.yaml/agent_policy — the one declaration these verdicts read."""
    return atlas().get("agent_policy") or {}


@lru_cache(maxsize=1)
def contract_schema() -> dict:
    return json.loads((ROOT / CONTRACT_SCHEMA).read_text(encoding="utf-8"))


def contract_errors(contract: object) -> list[str]:
    """Schema violations, plus the two rules a schema cannot state.

    A JSON Schema can say a command name is well formed. It cannot say that allowing a shell
    allows everything, and it cannot say that a plan arriving with its own outcome already
    written is a result wearing a plan's status.
    """
    errors = validate(contract, contract_schema(), "contract")
    if errors or not isinstance(contract, dict):
        return errors
    for name in contract.get("allowed_commands") or []:
        if str(name).rsplit("/", 1)[-1] in SHELL_NAMES:
            errors.append(f"contract.allowed_commands: '{name}' is a shell — allowing it allows "
                          "every command, so the allowance declares nothing")
    for prefix in _never_writable():
        covering = [a for a in contract.get("allowed_paths") or []
                    if str(a).rstrip("/") == prefix or prefix.startswith(str(a).rstrip("/") + "/")
                    or str(a).rstrip("/").startswith(prefix + "/")]
        if covering and not _prefixed(prefix, contract.get("forbidden_paths")):
            errors.append(f"contract.allowed_paths {covering[0]!r} reaches '{prefix}', which no "
                          "contract may write: it is either the policy that bounds this task, the "
                          "audit that records it, or a generated file whose declaration lives "
                          "elsewhere and would silently revert the edit")
    if contract.get("status") == "planned" and "outcome" in contract:
        errors.append("contract: status is 'planned' and an outcome is already present — the "
                      "runner writes that field, and a plan carrying one is a result in disguise")
    return errors


def _never_writable() -> list[str]:
    """The declared list PLUS every generated file, both read from atlas.yaml.

    This used to import the generator to get the second half, which was correct until the
    generator became development-only: a consumer validating a task contract would then have
    crashed on a module that is not in their wheel. One roster, in the declaration, read by the
    generator and by this without either importing the other.
    """
    declared = [str(p).rstrip("/") for p in (policy().get("never_writable") or [])]
    return sorted(set(declared) | {str(p) for p in atlas().get("generated_files") or []})


def contract_hash(contract: dict) -> str:
    """The identity an approval token binds to. Canonical JSON, so key order cannot change it."""
    body = {k: v for k, v in sorted(contract.items()) if k != "outcome"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def effective_budgets(contract: dict) -> dict[str, int]:
    """The lower of the declared ceiling and the contract, per budget."""
    ceilings = dict(policy().get("default_budgets") or {})
    asked = dict(contract.get("budgets") or {})
    return {name: min(int(ceiling), int(asked.get(name, ceiling))) for name, ceiling in ceilings.items()}


def _prefixed(path: str, prefixes: object) -> str | None:
    """The first prefix covering `path`, or None. A prefix covers itself and its children only."""
    for prefix in prefixes or []:
        text = str(prefix).rstrip("/")
        if path == text or path.startswith(text + "/"):
            return text
    return None


def path_verdict(contract: dict, candidate: str, mode: str = "write") -> Verdict:
    """The sandbox control, for every path the task touches — reads included.

    A read outside the scope has already expanded the task: it is how a plan that named two files
    becomes a change informed by two hundred, with nothing in the diff to show for it.
    """
    raw = str(candidate)
    try:
        resolved = (ROOT / raw).resolve()
        inside = resolved.relative_to(ROOT.resolve()).as_posix()
    except (ValueError, OSError):
        return Verdict(False, "sandbox", f"{raw!r} resolves outside the repository root")
    if Path(raw).is_absolute() or ".." in Path(raw).parts:
        return Verdict(False, "sandbox", f"{raw!r} is absolute or traverses; paths are repository-relative")
    if inside != raw.strip("/"):
        return Verdict(False, "sandbox", f"{raw!r} resolves to {inside!r} — a symlink or normalisation "
                                         "moved it, and the policy decides on where it LANDS")
    forbidden = _prefixed(inside, contract.get("forbidden_paths"))
    if forbidden:
        return Verdict(False, "sandbox", f"{inside} is under forbidden_paths/{forbidden}")
    allowed = _prefixed(inside, contract.get("allowed_paths"))
    if not allowed:
        return Verdict(False, "sandbox", f"{inside} is under no allowed_paths prefix ({mode})")
    return Verdict(True, "sandbox", f"{inside} is under allowed_paths/{allowed} ({mode})")


def command_verdict(contract: dict, argv: list[str]) -> Verdict:
    """The narrow-tools control: the declared floor first, the contract's allowance second."""
    if not argv or not all(isinstance(a, str) for a in argv):
        return Verdict(False, "narrow_tools", "an empty or non-string argv is not a command")
    quoted = shlex.join(argv)
    for name, rule in (policy().get("denied_commands") or {}).items():
        if re.search(str((rule or {}).get("pattern") or r"(?!x)x"), quoted):
            return Verdict(False, "narrow_tools", f"denied_commands/{name}: {(rule or {}).get('why')}")
    binary = argv[0].rsplit("/", 1)[-1]
    if binary not in (contract.get("allowed_commands") or []):
        return Verdict(False, "narrow_tools", f"{binary!r} is not in the contract's allowed_commands")
    return Verdict(True, "narrow_tools", f"{binary!r} is allowed and matches no denial")


def budget_verdict(contract: dict, projected: dict) -> Verdict:
    """The budget control, asked BEFORE the call: `projected` includes the one about to run.

    A budget compared after the fact is a report. The measured cost of that distinction is a task
    that notices it is over budget having already made the change that put it there.
    """
    ceilings = effective_budgets(contract)
    for name, ceiling in sorted(ceilings.items()):
        used = int(projected.get(name, 0))
        if used > ceiling:
            return Verdict(False, "budget", f"{name} would reach {used} against a ceiling of {ceiling} "
                                            "— stop and re-plan rather than expanding scope")
    return Verdict(True, "budget", f"within every one of {len(ceilings)} declared budgets")


def approval_verdict(contract: dict, action: str, token: object, now: int,
                     diff_hash: str | None = None) -> Verdict:
    """The approval control. A token is bound to what was approved, or it is a habit.

    Every field in `agent_policy/approval/binds_to` is compared, and each comparison is one of the
    ways a generic "yes, proceed" survives the thing it approved changing underneath it.
    """
    rules = policy().get("approval") or {}
    needed = set(rules.get("required_for") or []) | set(contract.get("approval_required") or [])
    if action not in needed:
        return Verdict(True, "approval", f"{action!r} is in no approval roster")
    if not isinstance(token, dict):
        return Verdict(False, "approval", f"{action!r} requires approval and no token was presented")
    expected = {
        "contract_hash": contract_hash(contract),
        "repository": (ROOT / "VERSION").parent.name,
        "base_commit": contract.get("base_commit"),
        "action": action,
        "diff_hash": diff_hash,
    }
    age = now - int(token.get("issued_at", 0))
    if age > int(rules.get("expires_after_seconds") or 0) or age < 0:
        return Verdict(False, "approval", f"the token is {age}s old against a lifetime of "
                                          f"{rules.get('expires_after_seconds')}s")
    if str(token.get("approver_role")) not in (rules.get("approver_roles") or []):
        return Verdict(False, "approval", f"approver_role {token.get('approver_role')!r} is not one "
                                          f"of {rules.get('approver_roles')}")
    for field in rules.get("binds_to") or []:
        want = expected.get(str(field))
        # AN UNBINDABLE FIELD IS NOT A SATISFIED ONE. Skipping a binding the contract cannot
        # supply is how "bound to the base commit" becomes true of a contract that declares none.
        if want is None:
            return Verdict(False, "approval", f"nothing supplies {field!r}, so the token cannot bind "
                                              "to it — an unbindable field is a missing one")
        if token.get(str(field)) != want:
            return Verdict(False, "approval", f"the token binds {field}={token.get(str(field))!r}, "
                                              f"this action has {want!r} — approval does not survive it changing")
    return Verdict(True, "approval", f"a token bound to {len(rules.get('binds_to') or [])} fields, {age}s old")


def scope_verdict(contract: dict, changed_files: list[str]) -> Verdict:
    """Did the diff stay inside the plan? Asked of the RESULT, which is the only honest moment.

    A plan that looks right and a change that went elsewhere are the failure this answers: without
    it, `plan --json` is a good-looking record an agent can produce and then ignore.
    """
    outside = [f for f in changed_files if not path_verdict(contract, f).allowed]
    if outside:
        return Verdict(False, "sandbox", f"{len(outside)} changed file(s) outside the plan: "
                                         + ", ".join(sorted(outside)[:5]))
    return budget_verdict(contract, {"files_changed": len(changed_files)})


def required_gates(contract: dict) -> list[str]:
    """The change class's gates plus every modifier's. A modifier only ever ADDS."""
    profiles = (atlas().get("verification_policy") or {}).get("profiles") or {}
    gates = list((profiles.get(str(contract.get("change_class"))) or {}).get("required") or [])
    modifiers = atlas().get("risk_modifiers") or {}
    for name in contract.get("risk_modifiers") or []:
        for gate in (modifiers.get(str(name)) or {}).get("adds") or []:
            if gate not in gates:
                gates.append(str(gate))
    return gates



def process_record(name: str) -> dict:
    """One named process, joined from the four rosters that describe it, as a record.

    THE EXTERNAL REFERENCE. A consuming repository should depend on the id `implementation` and on
    gate ids, never on a paragraph of README that can be re-worded without notice. Everything a
    caller needs to act is in here, so nothing has to be parsed out of a rendered document.
    """
    spec = (atlas().get("processes") or {}).get(str(name)) or {}
    steps = atlas().get("process_steps") or {}
    contract = {"change_class": spec.get("change_class"), "risk_modifiers": []}
    return {
        "schema": 1,
        "command": "process",
        "atlas_version": str(atlas().get("version")),
        "process": str(name),
        "task_profile": str(spec.get("task_profile")),
        "tools": list((atlas().get("task_profiles") or {}).get(str(spec.get("task_profile"))) or []),
        "change_class": str(spec.get("change_class")),
        "required_gates": required_gates(contract),
        "sequence": [{"step": str(s), "means": str(steps.get(str(s)) or "")} for s in spec.get("sequence") or []],
        "artifacts": [str(a) for a in spec.get("artifacts") or []],
        "stop_when": [str(s) for s in spec.get("stop_when") or []],
        "escalate_when": [str(s) for s in spec.get("escalate_when") or []],
        "task_contract_schema": str(policy().get("schema")),
    }


def process_errors() -> list[str]:
    """Every process names a real profile, a real class and real steps — and declares a STOP.

    A process with no stopping condition is one that expands until something else notices, which
    is the failure the agent controls exist for. The step vocabulary is checked both ways: a step
    no process uses is debris, and a step no vocabulary declares is a sentence with a bullet.
    """
    errors: list[str] = []
    registry = atlas().get("processes") or {}
    steps = atlas().get("process_steps") or {}
    profiles = atlas().get("task_profiles") or {}
    classes = (atlas().get("verification_policy") or {}).get("profiles") or {}
    used: set[str] = set()
    for name, spec in registry.items():
        if not isinstance(spec, dict):
            errors.append(f"processes/{name} is not a mapping")
            continue
        if str(spec.get("task_profile")) not in profiles:
            errors.append(f"processes/{name} names task_profile "
                          f"'{spec.get('task_profile')}', which atlas.yaml does not declare")
        if str(spec.get("change_class")) not in classes:
            errors.append(f"processes/{name} names change_class "
                          f"'{spec.get('change_class')}', which verification_policy does not declare")
        for step in spec.get("sequence") or []:
            used.add(str(step))
            if str(step) not in steps:
                errors.append(f"processes/{name} names step '{step}', which process_steps does not declare")
        for field in ("sequence", "artifacts", "stop_when", "escalate_when"):
            if not (spec.get(field) or []):
                errors.append(f"processes/{name} declares no {field} — a process that never says "
                              "when to stop expands until something else notices")
    for step, meaning in steps.items():
        if str(step) not in used:
            errors.append(f"process_steps declares '{step}', which no process uses")
        if not str(meaning or "").strip():
            errors.append(f"process_steps/{step} says nothing about what the step means")
    if not registry:
        errors.append("atlas.yaml declares no processes — a consumer then depends on prose")
    return errors


def _resolves(reference: str) -> bool:
    """Does `module.function` name a callable in this tree? The whole point of the roster."""
    module_name, _, attribute = str(reference).partition(".")
    try:
        return callable(getattr(importlib.import_module(module_name), attribute, None))
    except ImportError:
        return False


def agent_policy_errors() -> list[str]:
    """Every control the autonomous profile names is WIRED, and the declaration is self-consistent.

    Called by `atlas.py check`, and it is what makes `autonomous_profile_is_enforced` a check
    rather than a twenty-sixth promise.
    """
    errors: list[str] = []
    declared = policy()
    controls = declared.get("controls") or {}
    for control in (atlas().get("task_profiles") or {}).get("autonomous_agent") or []:
        spec = controls.get(str(control))
        if not isinstance(spec, dict):
            errors.append(f"task_profiles/autonomous_agent names '{control}', which "
                          "agent_policy/controls does not declare — a control nothing enforces")
        elif not _resolves(str(spec.get("enforced_by"))):
            errors.append(f"agent_policy/controls/{control}/enforced_by "
                          f"'{spec.get('enforced_by')}' does not resolve to a callable")
    for name, row in (declared.get("sandbox_requirements") or {}).items():
        observer = str((row or {}).get("observed_by") or "")
        reference = str((row or {}).get("reference") or "")
        if observer == "host" and not reference:
            errors.append(f"agent_policy/sandbox_requirements/{name} is the host's to observe and "
                          "names no reference configuration — a row nobody here can check and "
                          "nobody outside is told how to satisfy is an unclosed blind spot")
        elif reference and not (ROOT / reference).exists():
            errors.append(f"agent_policy/sandbox_requirements/{name} references {reference}, "
                          "which does not exist")
        if observer != "host" and not _resolves(observer):
            errors.append(f"agent_policy/sandbox_requirements/{name} is observed by "
                          f"'{observer}', which is neither 'host' nor a callable in this tree")
    for name, rule in (declared.get("denied_commands") or {}).items():
        try:
            re.compile(str((rule or {}).get("pattern")))
        except re.error as exc:
            errors.append(f"agent_policy/denied_commands/{name} is not a regular expression: {exc}")
        if not str((rule or {}).get("why") or "").strip():
            errors.append(f"agent_policy/denied_commands/{name} states no reason — a deny list "
                          "whose rows carry no reason is edited by whoever is blocked by it")
    budget_fields = set(contract_schema()["properties"]["budgets"]["properties"])
    extra = set(declared.get("default_budgets") or {}) - budget_fields
    if extra:
        errors.append(f"agent_policy/default_budgets declares {sorted(extra)}, which the task "
                      "contract schema has no field for — a ceiling no contract can name")
    classes = set((atlas().get("verification_policy") or {}).get("profiles") or {})
    for name, modifier in (atlas().get("risk_modifiers") or {}).items():
        if str((modifier or {}).get("applies_to")) not in classes:
            errors.append(f"risk_modifiers/{name} applies_to "
                          f"'{(modifier or {}).get('applies_to')}', which is not a change class")
        if not ((modifier or {}).get("adds") or []):
            errors.append(f"risk_modifiers/{name} adds no gate, so selecting it changes nothing")
    for path_key in ("schema", "reference_contract"):
        if not (ROOT / str(declared.get(path_key) or "")).exists():
            errors.append(f"agent_policy/{path_key} names a file that does not exist")
    reference = json.loads((ROOT / str(declared.get("reference_contract"))).read_text(encoding="utf-8"))
    errors += [f"reference contract: {e}" for e in contract_errors(reference)]
    # A SECOND DECLARATION OF THE VERSION, AND IT DRIFTED. The reference contract carries
    # `atlas_version`, five version bumps went past it, and the runner correctly refused the whole
    # task as a stale plan — in CI, on a pull request, after every local gate had passed. It is a
    # version SITE, so it belongs in the check that asserts them rather than in whoever remembers.
    version = read("VERSION").strip()
    if str(reference.get("atlas_version")) != version:
        errors.append(f"reference contract declares atlas_version "
                      f"{reference.get('atlas_version')} against VERSION {version} — the runner "
                      "refuses a plan resolved against another contract version, so this one "
                      "cannot pass its own CI step until the two agree")
    return errors


def authority_class_errors() -> list[str]:
    """Every manifest authority role belongs to EXACTLY ONE class, and every class names its closer.

    `native_language_tools_are_authoritative` is true and was read as more than it says. A compiler
    accepting a program proves it is well formed, never that it behaves; collapsing those into one
    word per pack is how a passing gate becomes a claim nobody made. A class with NO role is the
    useful half of the table: it says so, and names what answers instead.
    """
    errors: list[str] = []
    classes = atlas().get("authority_classes") or {}
    roles = set(manifest_schema()["properties"]["authority"]["properties"])
    claimed: dict[str, str] = {}
    for name, spec in classes.items():
        if not isinstance(spec, dict) or "roles" not in spec:
            errors.append(f"authority_classes/{name} declares no roles list")
            continue
        if not str(spec.get("closed_by") or "").strip():
            errors.append(f"authority_classes/{name} names no closer — an authority with no stated "
                          "limit is read as answering for everything below it")
        for role in spec.get("roles") or []:
            if str(role) not in roles:
                errors.append(f"authority_classes/{name} claims role '{role}', which no manifest has")
            elif str(role) in claimed:
                errors.append(f"role '{role}' is claimed by both authority_classes/{claimed[str(role)]} "
                              f"and /{name} — two authorities for one tool is none")
            claimed[str(role)] = name
    for role in sorted(roles - set(claimed)):
        errors.append(f"manifest authority role '{role}' belongs to no class in "
                      "atlas.yaml/authority_classes, so what it is authoritative FOR is unstated")
    return errors



def pack_manifest(route: str) -> dict:
    """One pack's declared tools, or an empty mapping when the pack ships none."""
    path = ROOT / "languages" / str(route) / "tools.yaml"
    if not path.exists():
        return {}
    data = strict_yaml(path.read_text(encoding="utf-8"), str(path))
    return data if isinstance(data, dict) else {}


def gate_command(route: str, gate: str) -> tuple[list[str] | None, str]:
    """The argv that RUNS a gate for one route, or None and the reason it cannot be run.

    THIS IS WHAT MAKES THE MANIFESTS LOAD-BEARING. Before it, `verification_policy` named gates and
    the packs named tools and nothing joined them, so "unit_tests passed" was satisfied by an agent
    saying so. The join is declared in atlas.yaml/gate_tools; change a pack's test runner and the
    gate resolves to the new one, with no second roster to update.
    """
    spec = (atlas().get("gate_tools") or {}).get(str(gate))
    if not isinstance(spec, dict):
        return None, f"no gate_tools entry — nothing declares what runs '{gate}'"
    role = str(spec.get("role"))
    if role == "none":
        return None, f"no pack tool answers this gate; closed by: {spec.get('closed_by')}"
    entry = (pack_manifest(route).get("authority") or {}).get(role)
    if entry is None:
        return None, f"the {route} pack declares no '{role}'"
    first = str(entry[0] if isinstance(entry, list) else entry)
    commands = entry_commands(first)
    if not commands:
        return None, f"the {route} pack's '{role}' is {first!r}, which is not a runnable command"
    return commands[0], f"{role} -> {first}"


def claim_errors() -> list[str]:
    """The claim ladder is ordered and every rung names its owner and what proves it.

    A pack that claims a rung asserts every rung below it, so the order is load-bearing rather
    than presentational: `passed` without `available` is a claim about a tool nobody found.
    """
    errors: list[str] = []
    rungs = atlas().get("tool_claims") or {}
    for name, spec in rungs.items():
        for field in ("means", "owner", "proven_by"):
            if not str((spec or {}).get(field) or "").strip():
                errors.append(f"tool_claims/{name} declares no {field} — a rung with no owner is "
                              "the collapse this ladder exists to undo")
    if list(rungs)[:1] != ["declared"]:
        errors.append("tool_claims must begin at 'declared': a rung below the one a manifest "
                      "actually makes would be asserted by every pack for free")
    for manifest in sorted((ROOT / "languages").rglob("tools.yaml")):
        data = strict_yaml(manifest.read_text(encoding="utf-8"), str(manifest))
        claimed = str(((data or {}).get("verification") or {}).get("status") or "")
        if not claimed:
            continue
        if claimed not in rungs:
            errors.append(f"{manifest.parent.name}: verification.status '{claimed}' is not a "
                          "declared rung of tool_claims")
        elif claimed != "declared" and not ((data or {}).get("verification") or {}).get("environment"):
            errors.append(f"{manifest.parent.name}: claims '{claimed}' with no environment — every "
                          "rung above 'declared' is a fact about a MACHINE, not about a pack")
    return errors


def action_command(route: str, action: str, path_value: str | None) -> tuple[list[str] | None, str]:
    """The argv `atlas do <file> <action>` would run for one route, or why it cannot be run.

    THE SAME JOIN AS A GATE, POINTED AT A PERSON INSTEAD OF AT CI. A pack declares its formatter
    once; the gate resolves it for verification and this resolves it for use, and neither holds a
    second roster. A pack that changes its test runner changes both in the same edit.
    """
    spec = (atlas().get("pack_actions") or {}).get(str(action))
    if not isinstance(spec, dict):
        return None, f"'{action}' is not a declared pack action"
    entry = (pack_manifest(route).get("authority") or {}).get(str(spec.get("role")))
    if entry is None:
        return None, f"the {route} pack declares no '{spec.get('role')}'"
    first = str(entry[0] if isinstance(entry, list) else entry)
    commands = entry_commands(first)
    if not commands:
        return None, f"the {route} pack's '{spec.get('role')}' is {first!r}, which is not a command"
    argv = list(commands[0])
    if spec.get("takes_file") and path_value:
        argv.append(str(path_value))
    return argv, f"{spec.get('role')} -> {first}"


def action_errors() -> list[str]:
    """Every action names a real authority role, and no two actions claim one role twice over."""
    errors: list[str] = []
    roles = set(manifest_schema()["properties"]["authority"]["properties"])
    for name, spec in (atlas().get("pack_actions") or {}).items():
        if not isinstance(spec, dict) or str(spec.get("role")) not in roles:
            errors.append(f"pack_actions/{name} names role '{(spec or {}).get('role')}', "
                          "which is not a manifest authority role")
        if not isinstance((spec or {}).get("takes_file"), bool):
            errors.append(f"pack_actions/{name} does not declare takes_file — appending a path to "
                          "a project-wide runner is how a green suite becomes a run of nothing")
    if not (atlas().get("pack_actions") or {}):
        errors.append("atlas.yaml declares no pack_actions, so 35 manifests are read by the "
                      "contract and by nothing a person can run")
    return errors


def gate_tool_errors() -> list[str]:
    """Every gate any profile, tier or modifier names can be RESOLVED, and every entry is named.

    Both directions, because the one-way version is the one that rots: a gate with no entry is a
    word a runner cannot act on, and an entry no policy names is a mapping nobody will notice is
    wrong.
    """
    errors: list[str] = []
    table = atlas().get("gate_tools") or {}
    verification = atlas().get("verification_policy") or {}
    tiers = verification.get("tiers") or {}
    named: set[str] = set()
    for profile in (verification.get("profiles") or {}).values():
        named |= {str(g) for g in (profile or {}).get("required") or []}
    for modifier in (atlas().get("risk_modifiers") or {}).values():
        named |= {str(g) for g in (modifier or {}).get("adds") or []}
    for tier in tiers.values():
        named |= {str(g) for g in tier or [] if str(g) not in tiers}
    roles = set(manifest_schema()["properties"]["authority"]["properties"]) | {"none"}
    for gate in sorted(named - set(table)):
        errors.append(f"gate '{gate}' is required by a profile, tier or modifier and "
                      "atlas.yaml/gate_tools says nothing runs it")
    for gate in sorted(set(table) - named):
        errors.append(f"gate_tools declares '{gate}', which no profile, tier or modifier requires")
    for gate, spec in table.items():
        role = str((spec or {}).get("role"))
        if role not in roles:
            errors.append(f"gate_tools/{gate} names role '{role}', which is not a manifest authority role")
        if role == "none" and not str((spec or {}).get("closed_by") or "").strip():
            errors.append(f"gate_tools/{gate} resolves to no tool and names no closer — "
                          "an unrunnable gate with no owner reads as one that passed")
    return errors


def main(argv: list[str] | None = None) -> int:
    """Explain the policy as it applies to one contract: budgets, floor, and what nobody here sees."""
    import argparse
    parser = argparse.ArgumentParser(prog="agentpolicy.py")
    parser.add_argument("contract", nargs="?", default=str(policy().get("reference_contract")))
    args = parser.parse_args(argv)
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    problems = (contract_errors(contract) + agent_policy_errors()
                + authority_class_errors() + gate_tool_errors())
    for problem in problems:
        print(f"- {problem}")
    print(f"contract: {args.contract} ({contract.get('task_id')})")
    print("effective budgets: " + ", ".join(f"{k}={v}" for k, v in sorted(effective_budgets(contract).items())))
    for gate in required_gates(contract):
        argv, why = gate_command(str(contract.get("route")), gate)
        print(f"gate {gate}: " + (shlex.join(argv) if argv else f"NOT RUNNABLE HERE — {why}"))
    print(f"denial floor: {len(policy().get('denied_commands') or {})} patterns refused whatever the contract allows")
    unobserved = [n for n, r in (policy().get("sandbox_requirements") or {}).items()
                  if str((r or {}).get("observed_by")) == "host"]
    print(f"sandbox: {len(unobserved)} of {len(policy().get('sandbox_requirements') or {})} rows are "
          f"HOST-observed and unproven here: {', '.join(sorted(unobserved))}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
