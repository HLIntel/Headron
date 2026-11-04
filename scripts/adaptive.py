"""Deterministic second-stage process selection for Mind."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlascore import atlas


@dataclass(frozen=True)
class AdaptiveDecision:
    """Second-stage process selection after initial classification and routing."""

    process: str | None
    context_mode: str | None
    reason: str
    requires_approval: bool = False
    status: str = "selected"

    def to_dict(self) -> dict:
        return {
            "process": self.process,
            "context_mode": self.context_mode,
            "reason": self.reason,
            "requires_approval": self.requires_approval,
            "status": self.status,
        }


@dataclass(frozen=True)
class RecoveryDecision:
    """Bounded adaptation after an execution or verification result."""

    action: str
    reason: str
    replan_count: int
    objective_preserved: bool
    requires_new_evidence: bool
    status: str = "selected"

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "reason": self.reason,
            "replan_count": self.replan_count,
            "objective_preserved": self.objective_preserved,
            "requires_new_evidence": self.requires_new_evidence,
            "status": self.status,
        }


@dataclass(frozen=True)
class DecompositionPlan:
    """Validated bounded subtasks and their safe execution groups."""

    objective: str
    tasks: tuple[dict, ...]
    parallel_groups: tuple[tuple[str, ...], ...]
    conflicts: tuple[str, ...] = ()
    status: str = "ready"

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "tasks": list(self.tasks),
            "parallel_groups": [list(group) for group in self.parallel_groups],
            "conflicts": list(self.conflicts),
            "status": self.status,
        }


@dataclass(frozen=True)
class ReconciliationResult:
    """Deterministic validation of delegated subtask results."""

    accepted: bool
    missing: tuple[str, ...] = ()
    invalid: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "missing": list(self.missing),
            "invalid": list(self.invalid),
            "conflicts": list(self.conflicts),
        }


def adapt_recovery(
    failure: Any, *, replan_count: int = 0, new_evidence: bool = False, objective_preserved: bool = True
) -> RecoveryDecision:
    """Choose one bounded recovery move without changing acceptance criteria."""
    policy = atlas().get("adaptive_recovery") or {}
    max_replans = int(policy.get("max_replans") or 0)
    if type(replan_count) is not int or replan_count < 0:
        return RecoveryDecision("stop", "invalid_replan_count", replan_count, objective_preserved, True, "refused")
    if not objective_preserved:
        return RecoveryDecision("escalate", "original_objective_changed", replan_count, False, True)
    if not new_evidence and replan_count:
        return RecoveryDecision("stop", "replan_requires_new_evidence", replan_count, True, True, "refused")
    if failure.failure_type == "none":
        return RecoveryDecision("continue", "evidence_supports_current_plan", replan_count, True, False)
    if new_evidence and replan_count < max_replans:
        return RecoveryDecision("replan", "material_assumption_changed", replan_count + 1, True, True)
    if replan_count >= max_replans:
        return RecoveryDecision("stop", "replan_budget_exhausted", replan_count, True, True)
    if failure.failure_type in ("timeout", "assertion_failure") and failure.retryable:
        return RecoveryDecision("retry", failure.failure_type, replan_count, True, False)
    if failure.requires_agent:
        return RecoveryDecision("escalate", "approval_or_authority_required", replan_count, True, True)
    return RecoveryDecision("escalate", "insufficient_recovery_evidence", replan_count, True, True)


def decompose(
    objective: str, subtasks: list[dict[str, Any]] | tuple[dict[str, Any], ...], *, depth: int = 1
) -> DecompositionPlan:
    """Validate bounded subtasks and identify only independent parallel work."""
    policy = atlas().get("decomposition_policy") or {}
    max_depth = int(policy.get("max_depth") or 0)
    required = tuple(str(name) for name in policy.get("required") or ())
    objective = str(objective).strip()
    rows = tuple(dict(task) for task in subtasks)
    errors: list[str] = []
    if not objective:
        errors.append("missing_objective")
    if type(depth) is not int or depth < 1 or depth > max_depth:
        errors.append("depth_out_of_bounds")
    identifiers: set[str] = set()
    for task in rows:
        task_id = str(task.get("id") or "").strip()
        if not task_id or task_id in identifiers:
            errors.append("duplicate_or_missing_task_id")
        identifiers.add(task_id)
        for field in required:
            value = task.get(field)
            if value is None or value == "" or value == []:
                errors.append(f"{task_id or 'task'}_missing_{field}")
        for dependency in task.get("depends_on") or ():
            if str(dependency) not in identifiers and str(dependency) not in {
                str(other.get("id") or "") for other in rows
            }:
                errors.append(f"{task_id}_unknown_dependency")
    if errors:
        return DecompositionPlan(objective, rows, (), tuple(dict.fromkeys(errors)), "refused")
    groups: list[tuple[str, ...]] = []
    for task in rows:
        if task.get("depends_on") or task.get("writes"):
            continue
        group = [str(other["id"]) for other in rows if not other.get("depends_on") and not other.get("writes")]
        if len(group) > 1 and tuple(group) not in groups:
            groups.append(tuple(group))
    return DecompositionPlan(objective, rows, tuple(groups))


def reconcile(plan: DecompositionPlan, results: dict[str, Any]) -> ReconciliationResult:
    """Require complete, valid, non-conflicting results before accepting a plan."""
    expected = {str(task["id"]) for task in plan.tasks}
    provided = {str(key) for key in results}
    missing = tuple(sorted(expected - provided))
    invalid: list[str] = []
    conflicts: list[str] = []
    for task_id in sorted(expected & provided):
        result = results[task_id]
        if not isinstance(result, dict) or result.get("valid") is not True or not result.get("artifact"):
            invalid.append(task_id)
            continue
        if result.get("conflict"):
            conflicts.append(task_id)
    if provided - expected:
        invalid.extend(f"unknown:{task_id}" for task_id in sorted(provided - expected))
    return ReconciliationResult(
        not missing and not invalid and not conflicts, missing, tuple(invalid), tuple(conflicts)
    )


def select_process(
    classification: Any,
    *,
    task_intent: str = "",
    affected_components: list[str] | tuple[str, ...] = (),
    dependency_depth: int = 0,
    uncertainty: float = 0.0,
    production_risk: bool = False,
) -> AdaptiveDecision:
    """Select the smallest declared process using deterministic task signals."""
    if type(dependency_depth) is not int or dependency_depth < 0:
        return AdaptiveDecision(None, None, "invalid_dependency_depth", status="refused")
    if type(uncertainty) not in (int, float) or not 0 <= uncertainty <= 1:
        return AdaptiveDecision(None, None, "invalid_uncertainty", status="refused")
    components = tuple(dict.fromkeys(str(c).strip() for c in affected_components if str(c).strip()))
    if production_risk:
        return AdaptiveDecision("security", "focused", "production_risk", requires_approval=True)
    if classification.category == "security_sensitive":
        return AdaptiveDecision("security", "focused", "security_boundary", requires_approval=True)
    if classification.unknown or uncertainty >= 0.5:
        return AdaptiveDecision("investigation", "isolated", "insufficient_evidence")
    if dependency_depth >= 2 or len(components) >= 2:
        return AdaptiveDecision("architecture_assessment", "semantic", "cross_component_or_deep_dependency")
    if classification.category == "dependency_change":
        return AdaptiveDecision("architecture_assessment", "semantic", "external_dependency")
    intent = task_intent.strip().lower()
    if intent and any(word in intent for word in ("investigate", "research", "unclear", "ambiguous")):
        return AdaptiveDecision("investigation", "isolated", "investigative_intent")
    return AdaptiveDecision("implementation", "focused", "low_risk_and_local")
