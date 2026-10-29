"""Declared workflow records and their stopping conditions."""

from atlascore import atlas


def _profile_fields(name: str) -> dict:
    """The task profile's fields, split by the roster each one resolves against."""
    profile = (atlas().get("task_profiles") or {}).get(name) or {}
    if not isinstance(profile, dict):  # pragma: no cover - declcheck refuses this shape
        return {"tools": [str(x) for x in profile or []]}
    return {
        "tools": [str(x) for x in profile.get("tools") or []],
        "pack_actions": [str(x) for x in profile.get("actions") or []],
        "profile_gates": [str(x) for x in profile.get("gates") or []],
        "context_mode": str(profile.get("context") or ""),
        "class_floor": str(profile.get("class_floor") or ""),
    }


def process_record(name: str) -> dict:
    """One named process, joined from the four rosters that describe it, as a record.

    THE EXTERNAL REFERENCE. A consuming repository should depend on the id `implementation` and on
    gate ids, never on a paragraph of README that can be re-worded without notice. Everything a
    caller needs to act is in here, so nothing has to be parsed out of a rendered document.
    """
    from agentpolicy import policy, required_gates

    spec = (atlas().get("processes") or {}).get(str(name)) or {}
    steps = atlas().get("process_steps") or {}
    contract = {
        "change_class": spec.get("change_class"),
        "risk_modifiers": [],
        "task_profile": spec.get("task_profile"),
    }
    return {
        "schema": 1,
        "command": "process",
        "atlas_version": str(atlas().get("version")),
        "process": str(name),
        "task_profile": str(spec.get("task_profile")),
        # THE PROFILE'S FIELDS, EACH FROM ITS OWN ROSTER (3.61.0). This key was one flat list, so a
        # caller was handed `focused_context` and `semantic_context` as TOOLS. They are neither.
        **_profile_fields(str(spec.get("task_profile"))),
        "change_class": str(spec.get("change_class")),
        "required_gates": required_gates(contract),
        "sequence": [{"step": str(s), "means": str(steps.get(str(s)) or "")} for s in spec.get("sequence") or []],
        "artifacts": [str(a) for a in spec.get("artifacts") or []],
        "stop_when": [str(s) for s in spec.get("stop_when") or []],
        "escalate_when": [str(s) for s in spec.get("escalate_when") or []],
        "task_contract_schema": str(policy().get("schema")),
        **({"host_calls": [dict(c) for c in spec["host_calls"]]} if spec.get("host_calls") else {}),
    }


def process_condition_errors() -> list[str]:
    """Every stop and escalate condition names a FUNCTION that decides it, or a closer that owns it.

    Found at 2.27.0: `reproduction_not_obtained` was a stop condition nothing decided — the same
    shape as a gate resolving to silence, in a second roster. Three states, as for gate roles: a
    decider that resolves, a named closer, or refused. A condition nobody owns never fires.
    """
    from agentpolicy import _resolves

    table = atlas().get("process_conditions") or {}
    named = {
        str(c)
        for spec in (atlas().get("processes") or {}).values()
        for key in ("stop_when", "escalate_when")
        for c in (spec or {}).get(key) or []
    }
    errors = [
        f"process condition '{c}' is used by a process and no decider or closer is declared in "
        "atlas.yaml/process_conditions — a stop that nothing decides never fires"
        for c in sorted(named - set(table))
    ]
    for condition, spec in table.items():
        decider, closer = (spec or {}).get("decided_by"), str((spec or {}).get("closed_by") or "").strip()
        if decider and not _resolves(str(decider)):
            errors.append(
                f"process_conditions/{condition} is decided_by {decider}, which is not a "
                "function in this tree — an enforcer that is only a name"
            )
        if not decider and not closer:
            errors.append(f"process_conditions/{condition} names neither a decider nor a closer")
    return errors


def process_errors() -> list[str]:
    """Every process names a real profile, a real class and real steps — and declares a STOP.

    A process with no stopping condition is one that expands until something else notices, which
    is the failure the agent controls exist for. The step vocabulary is checked both ways: a step
    no process uses is debris, and a step no vocabulary declares is a sentence with a bullet.
    """
    errors_from_conditions = process_condition_errors()
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
            errors.append(
                f"processes/{name} names task_profile '{spec.get('task_profile')}', which atlas.yaml does not declare"
            )
        if str(spec.get("change_class")) not in classes:
            errors.append(
                f"processes/{name} names change_class "
                f"'{spec.get('change_class')}', which verification_policy does not declare"
            )
        for step in spec.get("sequence") or []:
            used.add(str(step))
            if str(step) not in steps:
                errors.append(f"processes/{name} names step '{step}', which process_steps does not declare")
        for field in ("sequence", "artifacts", "stop_when", "escalate_when"):
            if not (spec.get(field) or []):
                errors.append(
                    f"processes/{name} declares no {field} — a process that never says "
                    "when to stop expands until something else notices"
                )
    for step, meaning in steps.items():
        if str(step) not in used:
            errors.append(f"process_steps declares '{step}', which no process uses")
        if not str(meaning or "").strip():
            errors.append(f"process_steps/{step} says nothing about what the step means")
    if not registry:
        errors.append("atlas.yaml declares no processes — a consumer then depends on prose")
    return errors + errors_from_conditions
