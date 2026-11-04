#!/usr/bin/env python3
"""Headron Mind API Diagnostics & Recovery — failure diagnosis and remediation.

WHY (3.61.0). Split out of mind.py when failure ledger signatures and success moves
were integrated, to keep both modules strictly bounded under MAX_CODE_LINES.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mind import Classification


@dataclass(frozen=True)
class Failure:
    """Result of mind.diagnose() — structured failure analysis."""

    failure_type: str
    retryable: bool
    requires_agent: bool
    evidence: tuple[str, ...]
    error_message: str = ""

    def to_dict(self) -> dict:
        return {
            "failure_type": self.failure_type,
            "retryable": self.retryable,
            "requires_agent": self.requires_agent,
            "evidence": list(self.evidence),
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class RecoveryAction:
    """Result of mind.recover() — recommended recovery action."""

    action_type: str  # retry, rollback, isolate, escalate, apply_success_move
    parameters: dict
    success_probability: float  # 0.0 to 1.0 estimate

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "parameters": self.parameters,
            "success_probability": self.success_probability,
        }


@dataclass(frozen=True)
class Escalation:
    """Result of mind.escalate() — escalation to another agent."""

    target_agent: str
    context_package: dict
    priority: str  # low, medium, high, critical

    def to_dict(self) -> dict:
        return {"target_agent": self.target_agent, "context_package": self.context_package, "priority": self.priority}


@dataclass(frozen=True)
class Refusal:
    """Result of mind.refuse() — refusal with explanation."""

    reason: str
    suggested_fix: str | None = None
    blocked_by_rule: str | None = None

    def to_dict(self) -> dict:
        return {"reason": self.reason, "suggested_fix": self.suggested_fix, "blocked_by_rule": self.blocked_by_rule}


def diagnose(execution_result: dict[str, Any]) -> Failure:
    """Diagnose an execution failure and determine recovery options.

    Args:
        execution_result: Dict with keys:
            - exit_code: Integer exit code
            - stdout: Standard output string
            - stderr: Standard error string
            - gate: Name of the gate that failed
            - files: List of files involved

    Returns:
        Failure with type, retryability, and evidence.

    proves: diagnosis follows declared failure mode patterns
    does_not_prove: that the diagnosis is the root cause
    closed_by: mind_test.py, which plants failures and verifies diagnosis
    """
    exit_code = execution_result.get("exit_code")
    if type(exit_code) is not int:
        return Failure(
            failure_type="incomplete_evidence",
            retryable=False,
            requires_agent=True,
            evidence=("missing_or_invalid_exit_code",),
            error_message="Execution result requires an integer exit code.",
        )
    stderr = execution_result.get("stderr", "")
    stdout = execution_result.get("stdout", "")
    _ = execution_result.get("gate", "unknown")

    if exit_code == 0:
        return Failure(failure_type="none", retryable=False, requires_agent=False, evidence=(), error_message="")

    err_low = stderr.lower()
    if "timeout" in err_low or exit_code == 124:
        failure_type, retryable, requires_agent, evidence = "timeout", True, False, ["timeout", "timeout_exit_124"]
    elif "syntax" in err_low or "parse" in err_low:
        failure_type, retryable, requires_agent, evidence = "syntax_error", False, True, ["syntax_violation"]
    elif any(k in err_low for k in ("import", "module not found", "modulenotfounderror")):
        failure_type, retryable, requires_agent, evidence = "dependency_error", False, True, ["dependency_error"]
    elif "permission" in err_low or "denied" in err_low:
        failure_type, retryable, requires_agent, evidence = "permission_error", False, False, ["permission_denied"]
    elif exit_code in (1, 2):
        failure_type, retryable, requires_agent, evidence = "assertion_failure", True, False, ["test_failure"]
    else:
        failure_type, retryable, requires_agent, evidence = (
            f"exit_code_{exit_code}",
            exit_code < 10,
            False,
            [stderr[:200] if stderr else "no_error_output"],
        )

    # Check declared ledger failure signatures (knowledge.failure_ids)
    try:
        from knowledge import failure_ids  # noqa: PLC0415

        matched_shapes = failure_ids(f"{stderr}\n{stdout}")
        if matched_shapes:
            evidence.extend(matched_shapes)
            if failure_type in ("assertion_failure",) or failure_type.startswith("exit_code_"):
                failure_type = matched_shapes[0]
                retryable = False
                requires_agent = True
    except Exception:
        pass

    return Failure(
        failure_type=failure_type,
        retryable=retryable,
        requires_agent=requires_agent,
        evidence=tuple(evidence),
        error_message=stderr[:500] if stderr else stdout[:500],
    )


def recover(failure: Failure, budget: int = 3) -> RecoveryAction:
    """Select a recovery action for a diagnosed failure.

    Args:
        failure: Result from mind.diagnose()
        budget: Remaining retry budget

    Returns:
        RecoveryAction with type, parameters, and success probability.

    proves: recovery action matches failure type per declared policy
    does_not_prove: that recovery will succeed
    closed_by: mind_test.py, which verifies recovery selection logic
    """
    if budget <= 0:
        return RecoveryAction(
            action_type="escalate", parameters={"reason": "budget_exhausted"}, success_probability=0.0
        )

    actions = {
        "timeout": ("retry", {"increase_timeout": True, "multiplier": 1.5}, 0.7),
        "syntax_error": ("rollback", {"restore_last_known_good": True}, 0.9),
        "dependency_error": ("isolate", {"install_missing": True, "verify_lock": True}, 0.6),
        "assertion_failure": ("retry", {"rerun_with_debug": True}, 0.5),
    }
    if failure.failure_type in actions:
        act, params, prob = actions[failure.failure_type]
        return RecoveryAction(action_type=act, parameters=params, success_probability=prob)

    # Check declared success moves for known ledger failure shapes
    try:
        from knowledge import moves_for  # noqa: PLC0415

        moves = moves_for(failure.failure_type)
        if moves:
            best_id, spec = moves[0]
            return RecoveryAction(
                action_type="apply_success_move",
                parameters={"success_id": best_id, "move": spec.get("move", ""), "failure_shape": failure.failure_type},
                success_probability=0.85,
            )
    except Exception:
        pass

    if failure.requires_agent:
        return RecoveryAction(
            action_type="escalate", parameters={"reason": "requires_human_judgment"}, success_probability=0.8
        )
    if failure.retryable and budget > 0:
        return RecoveryAction(action_type="retry", parameters={"use_fresh_context": True}, success_probability=0.4)
    return RecoveryAction(action_type="rollback", parameters={"full_revert": True}, success_probability=0.95)


def escalate(failure: Failure) -> Escalation:
    """Escalate a failure to a higher-level agent or human reviewer.

    Args:
        failure: Result from mind.diagnose()

    Returns:
        Escalation with target agent, context package, and priority.

    proves: escalation follows agent_policy hierarchy
    does_not_prove: that escalated agent can resolve the issue
    closed_by: mind_test.py, which verifies escalation routing
    """
    import time  # noqa: PLC0415

    if failure.failure_type in ("syntax_error", "permission_error"):
        priority = "high"
        target = "senior-engineer-agent"
    elif failure.requires_agent:
        priority = "critical"
        target = "human-review"
    else:
        priority = "medium"
        target = "hermes-agent"

    context_package = {
        "failure_type": failure.failure_type,
        "evidence": list(failure.evidence),
        "error_message": failure.error_message,
        "timestamp": time.time(),
    }

    return Escalation(target_agent=target, context_package=context_package, priority=priority)


def refuse(classification_or_failure: Classification | Failure) -> Refusal:
    """Refuse a change or action that cannot be safely processed.

    Args:
        classification_or_failure: Either Classification (for unknown changes)
                                  or Failure (for unresolvable errors)

    Returns:
        Refusal with reason, suggested fix, and blocking rule.

    proves: refusal follows declared safety policies
    does_not_prove: that the refused item is actually dangerous
    closed_by: mind_test.py, which verifies refusal messages
    """
    from mind import Classification  # noqa: PLC0415

    if isinstance(classification_or_failure, Classification):
        classification = classification_or_failure
        if classification.unknown:
            return Refusal(
                reason="Change could not be classified against known categories",
                suggested_fix="Provide explicit change_class in the request",
                blocked_by_rule="unknown_change_refusal",
            )
        return Refusal(
            reason=f"Change category '{classification.category}' exceeds risk threshold",
            suggested_fix="Split into smaller, lower-risk changes",
            blocked_by_rule="risk_threshold_exceeded",
        )
    failure = classification_or_failure
    if failure.failure_type == "syntax_error":
        return Refusal(
            reason="Syntax errors cannot be auto-corrected safely",
            suggested_fix="Review and fix syntax manually before resubmitting",
            blocked_by_rule="syntax_error_refusal",
        )
    if failure.failure_type == "permission_error":
        return Refusal(
            reason="Permission denied — insufficient authorization",
            suggested_fix="Request elevated permissions or adjust scope",
            blocked_by_rule="permission_denial",
        )
    return Refusal(
        reason=f"Unresolvable failure: {failure.failure_type}",
        suggested_fix="Manual review required",
        blocked_by_rule="general_safety_refusal",
    )
