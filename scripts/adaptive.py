"""Deterministic second-stage process selection for Mind."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mind import Classification
    from mind_diagnostics import Failure

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
class AdaptiveSchedule:
    """Optimal execution ordering and parallel grouping derived from measured costs."""

    batches: tuple[tuple[str, ...], ...]
    fail_fast_order: tuple[str, ...]
    estimated_latency_s: float
    estimated_tokens: int
    status: str = "scheduled"

    def to_dict(self) -> dict:
        return {
            "batches": [list(b) for b in self.batches],
            "fail_fast_order": list(self.fail_fast_order),
            "estimated_latency_s": self.estimated_latency_s,
            "estimated_tokens": self.estimated_tokens,
            "status": self.status,
        }


def schedule_execution(
    gates: list[dict], historical_costs: dict[str, dict] | None = None, max_parallel: int = 4
) -> AdaptiveSchedule:
    """Schedule gate execution adaptively to minimize latency and token consumption.

    Cheap, high-signal checks are ordered first (fail-fast). Non-mutating gates
    are grouped into concurrent batches; mutating gates run sequentially.
    """
    costs = historical_costs or {}
    scored: list[tuple[float, str, bool, float, int]] = []

    for gate in gates:
        gid = str(gate.get("id") or gate.get("gate") or "unknown")
        cost = costs.get(gid, {})
        lat = float(cost.get("latency_s") or 1.0)
        tok = int(cost.get("tokens") or 0)
        fail_prob = float(cost.get("failure_rate") or 0.1)
        mutates = bool(gate.get("mutates"))
        # Fail-fast score: prioritize gates that fail frequently and execute quickly
        score = -(fail_prob / max(0.1, lat))
        scored.append((score, gid, mutates, lat, tok))

    scored.sort(key=lambda item: item[0])
    fail_fast_order = tuple(item[1] for item in scored)

    batches: list[tuple[str, ...]] = []
    current_read_only: list[str] = []
    total_latency = 0.0
    total_tokens = sum(item[4] for item in scored)

    for _, gid, mutates, lat, _ in scored:
        if mutates:
            if current_read_only:
                batches.append(tuple(current_read_only))
                current_read_only = []
            batches.append((gid,))
            total_latency += lat
        else:
            current_read_only.append(gid)
            if len(current_read_only) >= max_parallel:
                batches.append(tuple(current_read_only))
                current_read_only = []

    if current_read_only:
        batches.append(tuple(current_read_only))

    # Add parallel batch latencies assuming maximum gate latency in batch dominates
    for batch in batches:
        if len(batch) > 1:
            batch_lat = max(float(costs.get(g, {}).get("latency_s") or 1.0) for g in batch)
            total_latency += batch_lat

    return AdaptiveSchedule(
        batches=tuple(batches),
        fail_fast_order=fail_fast_order,
        estimated_latency_s=round(total_latency, 2),
        estimated_tokens=total_tokens,
    )


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
    failure: Failure, *, replan_count: int = 0, new_evidence: bool = False, objective_preserved: bool = True
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
    # Enforce parallel_only_when policy conditions: independent_inputs, no_shared_mutation, no_dependency_ordering
    candidate_tasks = [t for t in rows if not t.get("depends_on") and not t.get("writes")]
    parallel_group: list[str] = []
    seen_reads: set[str] = set()
    for task in candidate_tasks:
        task_reads = {str(x) for x in (task.get("reads") or task.get("inputs") or ()) if x}
        if not task_reads:
            task_reads = {str(x) for x in (task.get("scope") or (task.get("id"),)) if x}
        if task_reads & seen_reads:
            continue
        seen_reads.update(task_reads)
        parallel_group.append(str(task["id"]))
    if len(parallel_group) > 1:
        groups.append(tuple(parallel_group))
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


def _process_mode(process: str) -> str:
    profile = (atlas().get("processes") or {})[process]["task_profile"]
    return (atlas().get("task_profiles") or {})[profile]["context"]


def _class_owner(category: str, selectable: dict[str, Any]) -> str | None:
    """The first process declared for a class. source_change is shared, so it names no owner."""
    if category == "source_change":
        return None
    return next((k for k, v in selectable.items() if v.get("change_class") == category), None)


def select_process(
    classification: Classification,
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
    intent = task_intent.strip().lower()
    selectable = {k: v for k, v in (atlas().get("processes") or {}).items() if not v.get("host_calls")}

    # Determine process based on classification, risk profile, and declared intent
    if classification.category == "security_sensitive":
        proc, mode, reason, app = "security", "focused", "security_boundary", True
    elif classification.unknown or uncertainty >= 0.5:
        proc, mode, reason, app = "investigation", "isolated", "insufficient_evidence", False
    elif dependency_depth >= 2 or len(components) >= 2:
        proc, mode, reason, app = "architecture_assessment", "semantic", "cross_component_or_deep_dependency", False
    elif intent in ("investigate", "research", "unclear", "ambiguous"):
        proc, mode, reason, app = "investigation", "isolated", "investigative_intent", False
    elif intent in selectable:
        proc, mode, reason, app = intent, _process_mode(intent), "declared_intent", False
    elif owner := _class_owner(classification.category, selectable):
        proc, mode, reason, app = owner, _process_mode(owner), "change_class", False
    else:
        proc, mode, reason, app = "implementation", "focused", "low_risk_and_local", False

    # Production risk requires approval without overriding ordinary change processes to security
    if production_risk:
        app = True
        if proc == "security":
            reason = "production_risk"

    return AdaptiveDecision(proc, mode, reason, requires_approval=app)
