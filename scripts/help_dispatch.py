"""Headron Help unified query dispatcher (contract v1).

Coordinates model-free intent compilation, sensitive data redaction, capability authorization,
idempotency tracking, polyglot inspection, and provenance tracking into a single deterministic pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from capability_catalog import (
    ANALYZE_SECURITY,
    COMPILE_OR_TYPECHECK,
    EXECUTE_TESTS,
    FORMAT_CODE,
    IDENTIFY_DIALECT,
    IDENTIFY_LANGUAGE,
    IDENTIFY_PROJECT_BOUNDARY,
    TRACE_BOUNDARY,
)
from help_cap_auth import authorize_capability, compute_idempotency_token, select_execution_location
from help_intent import compile_intent, rank_questions, render_explanation
from help_provenance import build_provenance
from help_redact import redact_text
from polyglot import inspect
from polyglot_boundary import detect_cross_language_contracts
from polyglot_plan import negotiate_capability


def dispatch_help(
    query: str, project_root: Path | None = None, plan: str = "trust", runtime: str = "offline", page: str = "overview"
) -> dict[str, Any]:
    """Execute complete deterministic Headron Help query resolution."""
    root = (project_root or Path.cwd()).resolve()

    # Empty or suggest queries return page questions
    clean_query = query.strip()
    if not clean_query or clean_query.lower() in ("suggest", "questions", "help"):
        questions = rank_questions(page)
        return {
            "status": "suggested_questions",
            "page": page,
            "questions": questions,
            "explanation": f"Suggested inquiries for context '{page}':\n" + "\n".join(f"- {q}" for q in questions),
        }

    # 1. Scrub credentials and sensitive tokens
    scrubbed_query = redact_text(clean_query)
    redacts_count = 1 if scrubbed_query != clean_query else 0

    # 2. Compile model-free intent
    intent = compile_intent(scrubbed_query)

    # 3. Evaluate capability authorization
    auth = authorize_capability(intent.capability, plan=plan, runtime=runtime)

    # 4. Context digest and idempotency token
    prov = build_provenance(root / "atlas.yaml" if (root / "atlas.yaml").exists() else root)
    token = compute_idempotency_token(intent.capability, intent.arguments, prov["digest"])
    location = select_execution_location(intent.capability, [runtime, "offline"])

    result_payload: dict[str, Any] = {
        "query": scrubbed_query,
        "redactions_applied": redacts_count,
        "capability": intent.capability,
        "operation_name": intent.operation_name,
        "confidence": intent.confidence,
        "authorized": auth.get("authorized", False),
        "auth_reason": auth.get("reason", ""),
        "execution_location": location,
        "idempotency_token": token,
        "provenance": prov,
    }

    if not auth.get("authorized", False):
        result_payload["status"] = "denied"
        result_payload["explanation"] = render_explanation(
            intent,
            status="DENIED",
            evidence=[
                auth.get("reason", "Operation denied"),
                f"Plan: {plan}",
                f"Runtime: {runtime}",
                f"Token: {token[:8]}",
            ],
        )
        return result_payload

    # 5. Route to deterministic capability engine
    cid = intent.capability
    evidence: list[str] = [f"Plan: {plan}", f"Location: {location}"]

    if cid in (IDENTIFY_LANGUAGE, IDENTIFY_PROJECT_BOUNDARY, IDENTIFY_DIALECT):
        fp = inspect(root)
        result_payload["polyglot_fingerprint"] = fp
        evidence.extend(
            [
                f"Languages: {', '.join(fp['languages'])}",
                f"Build: {fp['primary_build_system']}",
                f"Boundaries: {len(fp['boundaries'])}",
            ]
        )

    elif cid == TRACE_BOUNDARY:
        contracts = [c.to_dict() for c in detect_cross_language_contracts(root)]
        result_payload["cross_language_contracts"] = contracts
        evidence.append(f"Discovered {len(contracts)} cross-language boundary contract(s)")

    elif cid in (COMPILE_OR_TYPECHECK, FORMAT_CODE, EXECUTE_TESTS, ANALYZE_SECURITY):
        plan_res = negotiate_capability(cid, root)
        result_payload["negotiation"] = plan_res
        evidence.extend(
            [
                f"Route: {plan_res['route']}",
                f"Tool: {plan_res.get('selected_tool') or 'none'}",
                f"Status: {plan_res['status']}",
            ]
        )

    result_payload["status"] = "resolved"
    result_payload["explanation"] = render_explanation(intent, status="RESOLVED", evidence=evidence)
    return result_payload


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher for unified Headron Help queries."""
    import argparse

    parser = argparse.ArgumentParser(description="Headron Help deterministic query dispatcher")
    parser.add_argument("query", nargs="?", default="", help="Help inquiry or task query")
    parser.add_argument("--root", default=".", help="Project root path")
    parser.add_argument("--plan", default="trust", help="Plan tier (trust, standard, team, enterprise)")
    parser.add_argument("--runtime", default="offline", help="Runtime mode (offline, browser, local_driver)")
    parser.add_argument("--page", default="overview", help="UI page context for question ranking")
    parser.add_argument("--json", action="store_true", help="Print structured JSON result")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    result = dispatch_help(query=args.query, project_root=root, plan=args.plan, runtime=args.runtime, page=args.page)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result.get("explanation", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
