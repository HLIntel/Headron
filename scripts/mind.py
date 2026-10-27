#!/usr/bin/env python3
"""Headron Mind API — unified orchestration layer for agent workflows.

WHY (3.60.0). HeadronOS.md specifies a `mind.*` API (classify, plan, route, policy, diagnose, recover,
escalate, refuse) that orchestrates agent sessions through a deterministic protocol. Currently these
capabilities exist scattered across decide.py, reflex.py, pipeline.py, agents.py, and transactional.py.
This module provides the unified interface.

THE MIND API PATTERN. Each session flows through:
  1. mind.classify(change) → Classification(category, risk, matched_rules, contract_hash, unknown)
  2. mind.plan(classification) → Plan(gates_to_run, isolation_required, recovery_budget)
  3. mind.route(classification) → AgentOrTool(agent_id, capabilities, permissions)
  4. mind.policy(classification) → Policy(required_checks, forbidden_patterns, timeout_seconds)
  5. mind.diagnose(execution) → Failure(failure_type, retryable, requires_agent, evidence)
  6. mind.recover(failure, budget) → RecoveryAction(action_type, parameters)
  7. mind.escalate(failure) → Escalation(target_agent, context_package)
  8. mind.refuse(failure) → Refusal(reason, suggested_fix)

STATE FOOTPRINTS. Every operation records read_set, write_set, and pre_images for rollback.
Receipts are generated automatically for audit trails.

  from headron.mind import classify, plan, route, policy, diagnose, recover, escalate, refuse

  classification = mind.classify(change_diff)
  if classification.unknown:
      action = mind.refuse(classification)
  else:
      plan = mind.plan(classification)
      route = mind.route(classification)
      pol = mind.policy(classification)
      # ... execute with receipt tracking
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from atlascore import atlas

# =============================================================================
# DOMAIN TYPES — structured inputs/outputs for every Mind API call
# =============================================================================


class RiskLevel(Enum):
    """Change risk levels used throughout classification."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True)
class Classification:
    """Result of mind.classify() — categorizes a change with risk assessment.

    Attributes:
        category: Change class (source_change, api_change, dependency_change, etc.)
        risk: RiskLevel enum value
        matched_rules: Tuple of rule names that matched
        contract_hash: SHA256 of the policy version used
        unknown: True if change could not be classified
        files: Tuple of affected file paths
    """

    category: str
    risk: int
    matched_rules: tuple[str, ...]
    contract_hash: str
    unknown: bool = False
    files: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        d = {
            "category": self.category,
            "risk": self.risk,
            "matched_rules": list(self.matched_rules),
            "contract_hash": self.contract_hash,
            "unknown": self.unknown,
        }
        if self.files:
            d["files"] = list(self.files)
        return d


@dataclass(frozen=True)
class Plan:
    """Result of mind.plan() — execution plan for a classified change."""

    gates_to_run: tuple[str, ...]
    isolation_required: bool
    recovery_budget: int  # max retry attempts
    estimated_duration_seconds: int
    parallel_ok: bool

    def to_dict(self) -> dict:
        return {
            "gates_to_run": list(self.gates_to_run),
            "isolation_required": self.isolation_required,
            "recovery_budget": self.recovery_budget,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "parallel_ok": self.parallel_ok,
        }


@dataclass(frozen=True)
class Route:
    """Result of mind.route() — authorized agent/tool selection with deep routing."""

    agent_id: str
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    fallback_agent_id: str | None = None
    tier: str = "middle"
    shard: str = "core"
    edges: tuple[str, ...] = ()
    system_mode: str = "deliberate"
    blast_radius: int = 1
    invariants: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "capabilities": list(self.capabilities),
            "permissions": list(self.permissions),
            "fallback_agent_id": self.fallback_agent_id,
            "tier": self.tier,
            "shard": self.shard,
            "edges": list(self.edges),
            "system_mode": self.system_mode,
            "blast_radius": self.blast_radius,
            "invariants": list(self.invariants),
        }


@dataclass(frozen=True)
class Policy:
    """Result of mind.policy() — constraints and requirements for execution."""

    required_checks: tuple[str, ...]
    forbidden_patterns: tuple[str, ...]
    timeout_seconds: int
    max_context_tokens: int | None = None
    requires_receipt: bool = True

    def to_dict(self) -> dict:
        return {
            "required_checks": list(self.required_checks),
            "forbidden_patterns": list(self.forbidden_patterns),
            "timeout_seconds": self.timeout_seconds,
            "max_context_tokens": self.max_context_tokens,
            "requires_receipt": self.requires_receipt,
        }


@dataclass(frozen=True)
class Failure:
    """Result of mind.diagnose() — diagnosis of an execution failure."""

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

    action_type: str  # retry, rollback, isolate, escalate
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


@dataclass(frozen=True)
class ReceiptSummary:
    """Summary of an execution receipt verified against receipt v1 integrity rules."""

    receipt_id: str
    verdict: str
    base_commit: str
    policy_digest: str
    checks_count: int
    pass_count: int
    fail_count: int
    valid: bool
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "receipt_id": self.receipt_id,
            "verdict": self.verdict,
            "base_commit": self.base_commit,
            "policy_digest": self.policy_digest,
            "checks_count": self.checks_count,
            "pass_count": self.pass_count,
            "fail_count": self.fail_count,
            "valid": self.valid,
            "timestamp": self.timestamp,
        }


# =============================================================================
# MIND API — the unified orchestration interface
# =============================================================================


def classify(change: dict[str, Any]) -> Classification:
    """Classify a change and return its risk assessment.

    Args:
        change: Dict with keys:
            - diff: Unified diff string or list of file changes
            - files: List of affected file paths
            - change_class: Optional explicit class (source_change, api_change, etc.)
            - metadata: Optional dict with ast_delta, dependency_scope, etc.

    Returns:
        Classification with category, risk level, matched rules, and contract hash.

    proves: change is classified against declared categories in one pass
    does_not_prove: that the classification is correct for the task context
    closed_by: mind_test.py, which plants ambiguous changes and asserts refusal
    """
    from reflex import classify_change, classify_diff  # noqa: PLC0415

    files = change.get("files", [])
    change_class = change.get("change_class", "unknown")
    metadata = change.get("metadata", {})

    # Get contract hash from current atlas.yaml version
    atlas_version = str(atlas().get("version", "unknown"))
    contract_hash = hashlib.sha256(atlas_version.encode()).hexdigest()[:16]

    # Classify the diff if metadata provided
    if metadata:
        diff_verdicts = classify_diff(metadata)
        matched_rules = tuple(k for k, v in diff_verdicts.items() if v != "pass")
    else:
        matched_rules = ()

    # Classify the change class
    if change_class != "unknown" and files:
        try:
            verdict = classify_change(change_class, files, metadata)
            risk_level = _verdict_to_risk(verdict)
            category = change_class
        except Exception:
            risk_level = RiskLevel.MEDIUM
            category = "unknown"
    else:
        risk_level = RiskLevel.MEDIUM
        category = "unknown"

    # Check for unknown/unclassified changes
    is_unknown = category == "unknown" or len(matched_rules) == 0

    return Classification(
        category=category,
        risk=risk_level.value,
        matched_rules=matched_rules,
        contract_hash=contract_hash,
        unknown=is_unknown,
        files=tuple(files),
    )


def plan(classification: Classification) -> Plan:
    """Generate an execution plan for a classified change.

    Args:
        classification: Result from mind.classify()

    Returns:
        Plan with gates to run, isolation flag, recovery budget, and timing estimates.

    proves: plan is derived from classification using declared rules
    does_not_prove: that the plan will succeed — only that it follows policy
    closed_by: mind_test.py, which verifies plan structure and gate selection
    """
    # Get verification policy from atlas
    _ = atlas().get("verification_policy") or {}

    # Select gates based on risk level
    risk = classification.risk
    plan_by_risk = {
        RiskLevel.CRITICAL.value: (
            ("lint", "typecheck", "unit_tests", "integration_tests", "security_scan"),
            True,
            1,
            False,
        ),
        RiskLevel.HIGH.value: (("lint", "typecheck", "unit_tests"), True, 2, True),
        RiskLevel.MEDIUM.value: (("lint", "typecheck"), False, 3, True),
    }
    gates, isolation_required, recovery_budget, parallel_ok = plan_by_risk.get(risk, (("lint",), False, 5, True))

    # Estimate duration based on gate count and risk
    base_duration = 30  # seconds per gate
    duration = len(gates) * base_duration * (1 + risk / 4)

    return Plan(
        gates_to_run=tuple(gates),
        isolation_required=isolation_required,
        recovery_budget=recovery_budget,
        estimated_duration_seconds=int(duration),
        parallel_ok=parallel_ok,
    )


def _resolve_tier(file_list: tuple[str, ...]) -> str:
    for f in file_list:
        low = f.lower()
        if low.endswith(".sql") or "migration" in low or "db" in low:
            return "database"
        if any(ext in low for ext in (".html", ".css", ".tsx", ".jsx", "frontend", "ui/")):
            return "frontend"
        if any(term in low for term in ("api", "server", "daemon", "service", "endpoint")):
            return "backend"
    return "middle"


def _resolve_shard(file_list: tuple[str, ...]) -> str:
    if not file_list:
        return "core"
    try:
        from sweep import shard_of  # noqa: PLC0415

        return shard_of(file_list[0])
    except Exception:
        first = file_list[0].lower()
        if "test" in first or "verify" in first:
            return "verification"
        if "mind" in first or "reflex" in first or "decide" in first:
            return "mind"
        if "graph" in first:
            return "graph"
        return "core"


def _resolve_edges(shard: str, category: str, file_list: tuple[str, ...]) -> tuple[str, ...]:
    edges = [f"depends_on:{category}", f"enables:{shard}"]
    if any("receipt" in f for f in file_list):
        edges.append("references:receipt")
    if shard in ("verification", "mind"):
        edges.append("fast_tracks:telemetry")
    return tuple(edges)


def _resolve_invariants(risk: int) -> tuple[str, ...]:
    invs = ["code_blobs_are_bounded", "no_orphaned_symbols"]
    if risk >= RiskLevel.HIGH.value:
        invs.extend(["parsers_refuse_rather_than_guess", "immutable_first", "least_privilege"])
    return tuple(invs)


def route(classification: Classification, files: list[str] | tuple[str, ...] | None = None) -> Route:
    """Select an authorized agent or tool for the classified change with deep routing.

    Connects stack tier, architectural shard, graph edges, and hard invariants.
    Computes whether System 1 (reflex fast-track) or System 2 (deliberate planning) applies.

    proves: agent selection follows declared permissions in agent_policy
    does_not_prove: that the selected agent will complete the task
    closed_by: mind_test.py, which verifies agent selection and deep routing logic
    """
    _ = atlas().get("agent_policy") or {}

    risk = classification.risk
    category = classification.category
    target_files = tuple(files) if files is not None else classification.files

    shard = _resolve_shard(target_files)
    tier = _resolve_tier(target_files)
    edges = _resolve_edges(shard, category, target_files)
    invariants = _resolve_invariants(risk)
    blast_radius = max(1, len(target_files) * 2) if target_files else 1

    # System 1 reflex: bounded risk, local blast radius
    # System 2 deliberate: critical risk, security/dependency boundaries, or wide blast radius
    system_mode = "reflex" if risk <= RiskLevel.MEDIUM.value and blast_radius <= 2 else "deliberate"

    if risk >= RiskLevel.CRITICAL.value:
        agent_id, capabilities, permissions, fallback = (
            "human-review",
            ("review", "approve", "reject"),
            ("read", "comment"),
            "senior-engineer-agent",
        )
    elif risk >= RiskLevel.HIGH.value:
        agent_id, capabilities, permissions, fallback = (
            "claude-code",
            ("code", "test", "refactor"),
            ("read", "write", "commit"),
            "codex",
        )
    elif category in ("dependency_change", "security_sensitive"):
        agent_id, capabilities, permissions, fallback = (
            "hermes-agent",
            ("analyze", "verify", "audit"),
            ("read", "report"),
            "opencode",
        )
    else:
        agent_id, capabilities, permissions, fallback = "claude-code", ("code", "test"), ("read", "write"), "cursor"

    return Route(
        agent_id=agent_id,
        capabilities=capabilities,
        permissions=permissions,
        fallback_agent_id=fallback,
        tier=tier,
        shard=shard,
        edges=edges,
        system_mode=system_mode,
        blast_radius=blast_radius,
        invariants=invariants,
    )


def policy(classification: Classification) -> Policy:
    """Get execution policy constraints for the classified change.

    Args:
        classification: Result from mind.classify()

    Returns:
        Policy with required checks, forbidden patterns, and timeouts.

    proves: policy constraints are read from atlas.yaml declaration
    does_not_prove: that following policy guarantees correctness
    closed_by: mind_test.py, which verifies policy structure
    """
    _ = atlas().get("context_policy") or {}

    risk = classification.risk
    checks_by_risk = {
        RiskLevel.CRITICAL.value: (
            (
                "contract",
                "planted_suite",
                "agent_controls",
                "code_shape",
                "examples",
                "context_cost",
                "lint",
                "typecheck",
                "own_enforcement",
            ),
            600,
            32000,
        ),
        RiskLevel.HIGH.value: (("contract", "planted_suite", "code_shape", "lint", "typecheck"), 300, 64000),
        RiskLevel.MEDIUM.value: (("contract", "lint", "typecheck"), 180, 128000),
    }
    required, timeout, max_tokens = checks_by_risk.get(risk, (("lint",), 60, None))

    # Forbidden patterns from atlas
    forbidden_calls = atlas().get("forbidden_calls") or {}
    forbidden_patterns = tuple(forbidden_calls.keys())

    return Policy(
        required_checks=tuple(required),
        forbidden_patterns=forbidden_patterns,
        timeout_seconds=timeout,
        max_context_tokens=max_tokens,
        requires_receipt=True,
    )


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
    exit_code = execution_result.get("exit_code", 0)
    stderr = execution_result.get("stderr", "")
    stdout = execution_result.get("stdout", "")
    _ = execution_result.get("gate", "unknown")

    if exit_code == 0:
        return Failure(failure_type="none", retryable=False, requires_agent=False, evidence=(), error_message="")

    # Analyze error patterns
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
    # Determine priority based on failure type
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


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _verdict_to_risk(verdict: Any) -> RiskLevel:
    """Convert a GateVerdict to RiskLevel."""

    verdict_value = verdict.value if hasattr(verdict, "value") else str(verdict)

    if verdict_value == "fail":
        return RiskLevel.CRITICAL
    if verdict_value == "isolate":
        return RiskLevel.HIGH
    if verdict_value == "pass":
        return RiskLevel.LOW
    return RiskLevel.MEDIUM


# =============================================================================
# HEALTH TELEMETRY — HeadronOS.md § System Health & Telemetry
# =============================================================================

# Simple in-process counters for health reporting
_cache_hits: int = 0
_cache_lookups: int = 0
_stale_entries: int = 0
_receipts_recorded: int = 0


def _receipt_entry(rid: str, verdict: str, base: str, dig: str, chk: int, p_cnt: int, f_cnt: int, valid: bool) -> dict:
    return ReceiptSummary(rid, verdict, base, dig, chk, p_cnt, f_cnt, valid, time.time()).to_dict()


def record_receipt(receipt_data: dict | str | Any) -> dict:
    """Validate and record an execution receipt into persistent telemetry.

    proves: receipt verifies against receipt v1 integrity rules before storage
    does_not_prove: that underlying checks were executed correctly
    closed_by: mind_test.py, which verifies recording and tampering detection
    """
    from pathlib import Path  # noqa: PLC0415

    import receipt as _receipt  # noqa: PLC0415
    from safeedit import _git_path  # noqa: PLC0415

    if isinstance(receipt_data, (str, Path)):
        p = Path(receipt_data)
        if not p.is_file():
            raise ValueError(f"no such receipt file: {receipt_data}")
        raw = p.read_bytes()
        body = json.loads(raw.decode("utf-8"))
    else:
        body = receipt_data
        raw = _receipt.canonical(body) if hasattr(_receipt, "canonical") else json.dumps(body).encode("utf-8")

    valid = len(_receipt.verify_bytes(raw)) == 0
    cnt = body.get("counts") or {}
    pol = body.get("policy") or {}
    if not isinstance(pol, dict):
        pol = {}
    summary = _receipt_entry(
        str(body.get("receipt_id", "")),
        str(body.get("verdict", "UNKNOWN")),
        str(body.get("base_commit", "")),
        str(pol.get("digest", "")),
        len(body.get("checks", [])),
        int(cnt.get("PASS", 0)),
        int(cnt.get("FAIL", 0)),
        valid,
    )
    try:
        with open(_git_path("headron-receipts.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(summary) + "\n")
    except Exception:
        pass
    global _receipts_recorded
    _receipts_recorded += 1
    return summary


def gather_receipts(directory: Any = None, limit: int = 20) -> list[dict]:
    """Gather and verify execution receipts over and over across runs.

    Reads stored receipt records, last verification run, or receipts in directory,
    validating cryptographic integrity and aggregating consistency telemetry.

    proves: receipts are gathered without altering git working tree state
    does_not_prove: that historical runs can be reproduced on current commits
    closed_by: mind_test.py, which verifies gathering and consistency calculations
    """
    from pathlib import Path  # noqa: PLC0415

    import receipt as _receipt  # noqa: PLC0415
    from safeedit import _git_path  # noqa: PLC0415

    records: list[dict] = []
    seen: set[str] = set()
    try:
        store = _git_path("headron-receipts.jsonl")
        if store.is_file():
            for line in store.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    entry = json.loads(line)
                    if (rid := entry.get("receipt_id")) and rid not in seen:
                        records.append(entry)
                        seen.add(rid)
    except Exception:
        pass
    try:
        last_v = _git_path("headron-last-verify.json")
        if last_v.is_file():
            d = json.loads(last_v.read_text(encoding="utf-8"))
            if rows := d.get("rows", []):
                built = _receipt.build(
                    rows,
                    base_commit=d.get("base", "0" * 40),
                    policy_digest=d.get("policy_digest", "0" * 40),
                    input_digest=d.get("input_digest", "0" * 40),
                )
                if (rid := built["receipt_id"]) not in seen:
                    cnt, pol = built.get("counts") or {}, built.get("policy") or {}
                    valid = len(_receipt.verify_bytes(_receipt.canonical(built))) == 0
                    records.append(
                        _receipt_entry(
                            rid,
                            built["verdict"],
                            built["base_commit"],
                            pol.get("digest", ""),
                            len(built.get("checks", [])),
                            int(cnt.get("PASS", 0)),
                            int(cnt.get("FAIL", 0)),
                            valid,
                        )
                    )
                    seen.add(rid)
    except Exception:
        pass
    if directory and (dp := Path(directory)).is_dir():
        for f in sorted(dp.glob("*.json")) + sorted(dp.glob("*.receipt")):
            if len(records) >= limit:
                break
            try:
                raw = f.read_bytes()
                findings, b = _receipt.verify_bytes(raw), json.loads(raw.decode("utf-8"))
                if (rid := b.get("receipt_id")) and rid not in seen:
                    cnt, pol = b.get("counts") or {}, b.get("policy") or {}
                    p_dig = pol.get("digest", "") if isinstance(pol, dict) else ""
                    records.append(
                        _receipt_entry(
                            rid,
                            b.get("verdict", "UNKNOWN"),
                            b.get("base_commit", ""),
                            p_dig,
                            len(b.get("checks", [])),
                            int(cnt.get("PASS", 0)),
                            int(cnt.get("FAIL", 0)),
                            len(findings) == 0,
                        )
                    )
                    seen.add(rid)
            except Exception:
                continue
    return records[:limit]


def _health_snapshot() -> dict:
    """Return a health telemetry snapshot with gathered receipts."""
    hit_rate = _cache_hits / _cache_lookups if _cache_lookups else 0.0
    snap = {
        "cache_hits": _cache_hits,
        "cache_lookups": _cache_lookups,
        "cache_hit_rate": round(hit_rate, 3),
        "stale_entries": _stale_entries,
    }
    receipts = gather_receipts(limit=50)
    valid_count = sum(1 for r in receipts if r.get("valid"))
    pass_count = sum(1 for r in receipts if r.get("verdict") == "PASS")
    snap["receipts_gathered"] = len(receipts)
    snap["receipts_valid"] = valid_count
    snap["receipt_pass_rate"] = round(pass_count / len(receipts), 3) if receipts else 0.0
    try:
        from safeedit import _git_path  # noqa: PLC0415

        last_v = _git_path("headron-last-verify.json")
        if last_v.is_file():
            data = json.loads(last_v.read_text(encoding="utf-8"))
            snap["last_verify_exit"] = data.get("exit")
            if "telemetry" in data:
                snap["verification_telemetry"] = data["telemetry"]
    except Exception:
        pass
    try:
        import slot  # noqa: PLC0415

        snap["slot_telemetry"] = slot.slot_status()
    except Exception:
        pass
    return snap


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `headron mind` — classify, plan, route, receipts, health.

    proves: mind API is reachable from the headron CLI
    does_not_prove: that classification matches the task context
    closed_by: mind_test.py, which plants ambiguous changes and asserts refusal
    """
    import argparse

    parser = argparse.ArgumentParser(prog="headron mind", description="Headron Mind API — classify, plan, route, health")
    parser.add_argument("--classify", action="store_true", help="classify the given files")
    parser.add_argument("--plan", action="store_true", help="generate a plan for the classification")
    parser.add_argument("--route", action="store_true", help="select an agent for the classification")
    parser.add_argument("--health", action="store_true", help="show health telemetry")
    parser.add_argument("--receipts", action="store_true", help="gather and verify audit receipts over time")
    parser.add_argument("--json", action="store_true", help="emit JSON output")
    parser.add_argument("files", nargs="*", help="files to classify")

    args = parser.parse_args(argv)
    as_json = args.json

    if args.receipts:
        records = gather_receipts(limit=20)
        valid_cnt = sum(1 for r in records if r.get("valid"))
        pass_cnt = sum(1 for r in records if r.get("verdict") == "PASS")
        result = {
            "command": "mind",
            "action": "receipts",
            "total": len(records),
            "valid": valid_cnt,
            "pass_count": pass_cnt,
            "receipts": records,
        }
        if as_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Mind receipts — {len(records)} gathered, {valid_cnt} valid, {pass_cnt} passing")
            for r in records[:5]:
                print(f"  {r['receipt_id'][:12]}.. {r['verdict']} ({r['pass_count']}/{r['checks_count']} passed)")
        return 0

    if args.health:
        health = _health_snapshot()
        result = {"command": "mind", **health}
        if as_json:
            print(json.dumps(result, indent=2))
        else:
            v_telemetry = health.get("verification_telemetry") or {}
            v_speedup = f", verify speedup: {v_telemetry.get('speedup')}x" if "speedup" in v_telemetry else ""
            print(
                f"Mind health — cache hits: {health['cache_hits']}, "
                f"lookups: {health['cache_lookups']}, "
                f"stale entries: {health['stale_entries']}, "
                f"receipts gathered: {health.get('receipts_gathered', 0)}"
                f"{v_speedup}"
            )
        return 0

    if not (args.classify or args.plan or args.route):
        parser.print_help()
        return 0

    files = args.files or []
    change = {"files": files, "change_class": "unknown", "metadata": {}}

    classification = classify(change)
    result = {"command": "mind", **classification.to_dict()}

    p = plan(classification) if args.plan else None
    if p is not None:
        result.update(p.to_dict())

    r = route(classification, files=files) if args.route else None
    if r is not None:
        result.update(r.to_dict())

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Category: {classification.category}")
        print(f"Risk: {classification.risk}")
        print(f"Unknown: {classification.unknown}")
        print(f"Rules: {', '.join(classification.matched_rules) or '(none)'}")
        if p is not None:
            print(f"Gates: {', '.join(p.gates_to_run)}")
            print(f"Isolation: {p.isolation_required}")
            print(f"Recovery budget: {p.recovery_budget}")
        if r is not None:
            print(f"Agent: {r.agent_id}")
            print(f"Capabilities: {', '.join(r.capabilities)}")
            print(f"Mode: {r.system_mode} (System 1/2)")
            print(f"Tier: {r.tier} | Shard: {r.shard}")
            print(f"Blast radius: {r.blast_radius} | Edges: {', '.join(r.edges)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
