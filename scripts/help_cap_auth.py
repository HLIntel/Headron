"""Headron capability authorization matrix and idempotency engine (contract v1).

Evaluates whether operations are authorized for given plans and runtimes.
Computes deterministic idempotency keys and selects permitted execution locations.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from capability_catalog import (
    ANALYZE_SECURITY,
    COMPILE_OR_TYPECHECK,
    EXECUTE_FUZZ,
    EXECUTE_TESTS,
    EXPLAIN_RESULT,
    FORMAT_CODE,
    IDENTIFY_DIALECT,
    IDENTIFY_LANGUAGE,
    IDENTIFY_PROJECT_BOUNDARY,
    PRODUCE_EVIDENCE,
    RESOLVE_DEPS,
    TRACE_BOUNDARY,
    VALIDATE_PROOF,
)

# Plan allowed capabilities:
# Trust: Read-only inspection, boundary tracing, evidence verification, explanations
_TRUST_PERMITTED: frozenset[int] = frozenset(
    {
        IDENTIFY_LANGUAGE,
        IDENTIFY_PROJECT_BOUNDARY,
        IDENTIFY_DIALECT,
        RESOLVE_DEPS,
        TRACE_BOUNDARY,
        PRODUCE_EVIDENCE,
        VALIDATE_PROOF,
        EXPLAIN_RESULT,
    }
)

# Pro & Team: Full local verification and build capabilities with authorized driver
_PRO_PERMITTED: frozenset[int] = frozenset(
    {
        IDENTIFY_LANGUAGE,
        IDENTIFY_PROJECT_BOUNDARY,
        IDENTIFY_DIALECT,
        COMPILE_OR_TYPECHECK,
        FORMAT_CODE,
        EXECUTE_TESTS,
        ANALYZE_SECURITY,
        EXECUTE_FUZZ,
        RESOLVE_DEPS,
        TRACE_BOUNDARY,
        PRODUCE_EVIDENCE,
        VALIDATE_PROOF,
        EXPLAIN_RESULT,
    }
)


def authorize_capability(capability_id: int, plan: str, runtime: str) -> dict[str, Any]:
    """Evaluate whether an operation is authorized for the given plan and runtime."""
    plan_clean = plan.strip().lower()
    runtime_clean = runtime.strip().lower()

    allowed = _PRO_PERMITTED if plan_clean in ("pro", "team") else _TRUST_PERMITTED

    if capability_id not in allowed:
        return {
            "authorized": False,
            "capability": capability_id,
            "plan": plan_clean,
            "runtime": runtime_clean,
            "reason": f"Capability {capability_id} requires Pro or Team plan with an authorized execution driver.",
        }

    # Browser runtime cannot run local compilation or test subprocesses directly
    local_exec_caps = {COMPILE_OR_TYPECHECK, FORMAT_CODE, EXECUTE_TESTS, EXECUTE_FUZZ}
    if capability_id in local_exec_caps and runtime_clean == "browser":
        return {
            "authorized": False,
            "capability": capability_id,
            "plan": plan_clean,
            "runtime": runtime_clean,
            "reason": "Execution requires an authorized local or hosted driver, not browser runtime.",
        }

    return {
        "authorized": True,
        "capability": capability_id,
        "plan": plan_clean,
        "runtime": runtime_clean,
        "reason": "Operation authorized under current grants.",
    }


def compute_idempotency_token(capability_id: int, arguments: dict[str, Any], context_digest: str) -> str:
    """Compute a deterministic idempotency token for operation mutation deduplication."""
    canonical = json.dumps(
        {"capability": capability_id, "arguments": arguments, "context": context_digest},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def select_execution_location(capability_id: int, available_runtimes: list[str]) -> str:
    """Select appropriate execution runtime for a given capability."""
    runtimes = set(available_runtimes)
    # Inspection capabilities can run offline or in browser
    if capability_id in (IDENTIFY_LANGUAGE, IDENTIFY_PROJECT_BOUNDARY, IDENTIFY_DIALECT, EXPLAIN_RESULT):
        if "browser" in runtimes:
            return "browser"
        if "offline" in runtimes:
            return "offline"

    # Execution capabilities prefer local driver or hosted worker
    if "local_driver" in runtimes:
        return "local_driver"
    if "hosted_worker" in runtimes:
        return "hosted_worker"

    return "offline"


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher for capability authorization and execution routing."""
    import argparse

    parser = argparse.ArgumentParser(description="Headron Help capability authorization engine")
    parser.add_argument("capability", type=int, help="Capability ID (e.g. 100, 200, 220)")
    parser.add_argument("--plan", default="trust", help="Plan level (trust, standard, team, enterprise)")
    parser.add_argument(
        "--runtime", default="offline", help="Runtime mode (offline, browser, local_driver, hosted_worker)"
    )
    parser.add_argument("--select-location", action="store_true", help="Select optimal execution location")
    parser.add_argument("--idempotency-token", action="store_true", help="Compute idempotency token")
    parser.add_argument("--context-digest", default="empty", help="Context digest for idempotency")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output")
    args = parser.parse_args(argv)

    if args.select_location:
        available = [args.runtime] if args.runtime else ["offline"]
        loc = select_execution_location(args.capability, available)
        if args.json:
            print(json.dumps({"capability": args.capability, "selected_location": loc}))
        else:
            print(loc)
        return 0

    if args.idempotency_token:
        token = compute_idempotency_token(args.capability, {"plan": args.plan}, args.context_digest)
        if args.json:
            print(json.dumps({"capability": args.capability, "idempotency_token": token}))
        else:
            print(token)
        return 0

    res = authorize_capability(args.capability, plan=args.plan, runtime=args.runtime)
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        status = "AUTHORIZED" if res.get("authorized") else "DENIED"
        print(f"Capability {args.capability}: {status} ({res.get('reason')})")
    return 0 if res.get("authorized") else 1


if __name__ == "__main__":
    raise SystemExit(main())
