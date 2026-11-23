"""Headron Help model-free intent compiler and slot resolver (contract v1).

Maps user requests to exact capability IDs (100..500) and typed arguments.
Maintains multi-turn context and ranks page-aware questions without an LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from capability_catalog import (
    ANALYZE_SECURITY,
    COMPILE_OR_TYPECHECK,
    EXECUTE_FUZZ,
    EXECUTE_TESTS,
    EXPLAIN_RESULT,
    FORMAT_CODE,
    IDENTIFY_LANGUAGE,
    IDENTIFY_PROJECT_BOUNDARY,
    PRODUCE_EVIDENCE,
    RESOLVE_DEPS,
    TRACE_BOUNDARY,
    VALIDATE_PROOF,
)


@dataclass(frozen=True)
class ResolvedIntent:
    capability: int
    confidence: str  # confirmed, likely, unproven
    operation_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    disambiguation: list[str] = field(default_factory=list)


# Rule patterns mapping phrases to permanent capabilities
_INTENT_RULES: tuple[tuple[re.Pattern[str], int, str], ...] = (
    (
        re.compile(r"\b(test|tests|pytest|cargo test|go test|run tests)\b", re.IGNORECASE),
        EXECUTE_TESTS,
        "tests.execute",
    ),
    (
        re.compile(r"\b(compile|build|typecheck|type check|tsc|cargo check)\b", re.IGNORECASE),
        COMPILE_OR_TYPECHECK,
        "code.compile_or_typecheck",
    ),
    (re.compile(r"\b(format|fmt|style|lint|ruff|gofmt)\b", re.IGNORECASE), FORMAT_CODE, "code.format"),
    (
        re.compile(r"\b(security|vulnerability|audit|secret|cve|bandit)\b", re.IGNORECASE),
        ANALYZE_SECURITY,
        "security.analyze",
    ),
    (re.compile(r"\b(fuzz|fuzzing|afl|clusterfuzz)\b", re.IGNORECASE), EXECUTE_FUZZ, "fuzz.execute"),
    (
        re.compile(r"\b(dependency|dependencies|deps|lockfile|package\.json|cargo\.lock)\b", re.IGNORECASE),
        RESOLVE_DEPS,
        "deps.resolve",
    ),
    (
        re.compile(r"\b(boundary|boundaries|openapi|protobuf|grpc|contract|schema)\b", re.IGNORECASE),
        TRACE_BOUNDARY,
        "boundary.trace",
    ),
    (
        re.compile(r"\b(language|dialect|what language|detect language)\b", re.IGNORECASE),
        IDENTIFY_LANGUAGE,
        "language.identify",
    ),
    (
        re.compile(r"\b(project|root|workspace|where is root)\b", re.IGNORECASE),
        IDENTIFY_PROJECT_BOUNDARY,
        "project.boundary",
    ),
    (re.compile(r"\b(verify|gate|gates|evidence|run verify)\b", re.IGNORECASE), PRODUCE_EVIDENCE, "evidence.produce"),
    (re.compile(r"\b(receipt|proof|signature|verify receipt)\b", re.IGNORECASE), VALIDATE_PROOF, "proof.validate"),
    (re.compile(r"\b(explain|why|what failed|help|status)\b", re.IGNORECASE), EXPLAIN_RESULT, "result.explain"),
)

# Page-aware questions catalog
_PAGE_QUESTIONS: dict[str, list[str]] = {
    "overview": [
        "What checks does this project require?",
        "Which languages and boundaries were detected?",
        "Are all verification tools available on this machine?",
    ],
    "receipt": [
        "Why did this check fail?",
        "Is the receipt cryptographic signature valid?",
        "Which gate is blocking landing?",
    ],
    "boundary": [
        "What cross-language contracts were discovered?",
        "Are OpenAPI or Protobuf schemas synchronized?",
        "Which client bindings are affected by recent schema edits?",
    ],
    "gates": [
        "Which gates are marked NOT RUN?",
        "What toolchain is needed to run skipped checks?",
        "What is the required verification done-set?",
    ],
}


def compile_intent(query: str, slots: dict[str, Any] | None = None) -> ResolvedIntent:
    """Compile raw user query and slots into an exact capability ID."""
    active_slots = slots or {}
    text = query.strip()

    # Slot recall: "show previous", "run it again"
    if re.search(r"\b(previous|again|last one|re-run)\b", text, re.IGNORECASE):
        last_cap = active_slots.get("last_capability")
        if isinstance(last_cap, int):
            return ResolvedIntent(
                capability=last_cap,
                confidence="confirmed",
                operation_name=f"capability.{last_cap}",
                arguments={"source": "slot_recall", **active_slots},
            )

    matched: list[tuple[int, str]] = []
    for pattern, cap_id, name in _INTENT_RULES:
        if pattern.search(text):
            matched.append((cap_id, name))

    if len(matched) == 1:
        cap_id, name = matched[0]
        return ResolvedIntent(
            capability=cap_id, confidence="confirmed", operation_name=name, arguments={"query": text, **active_slots}
        )

    if len(matched) > 1:
        # Disambiguate when multiple matched
        first_cap, first_name = matched[0]
        return ResolvedIntent(
            capability=first_cap,
            confidence="likely",
            operation_name=first_name,
            arguments={"query": text, **active_slots},
            disambiguation=[m[1] for m in matched],
        )

    # Default fallback to result.explain
    return ResolvedIntent(
        capability=EXPLAIN_RESULT,
        confidence="unproven",
        operation_name="result.explain",
        arguments={"query": text, **active_slots},
    )


def rank_questions(page: str, slots: dict[str, Any] | None = None) -> list[str]:
    """Return top 3 prioritized context-aware questions for current page."""
    base = _PAGE_QUESTIONS.get(page.lower(), _PAGE_QUESTIONS["overview"])
    if slots and "selected_file" in slots:
        file_name = slots["selected_file"]
        return [f"What checks does {file_name} need?"] + base[:2]
    return base[:3]


def render_explanation(intent: ResolvedIntent, status: str, evidence: list[str]) -> str:
    """Generate concise, deterministic explanation from structured state."""
    header = f"Capability: {intent.operation_name} (ID {intent.capability}) | Status: {status}"
    if not evidence:
        return f"{header}\nNo direct evidence recorded for this operation."
    lines = [header, "Evidence:"]
    for item in evidence[:5]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher for model-free intent compilation and question ranking."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Headron Help model-free intent compiler")
    parser.add_argument("query", nargs="?", default="", help="User request to compile")
    parser.add_argument("--page", default="overview", help="Active page name for question ranking")
    parser.add_argument("--rank-questions", action="store_true", help="Rank questions for page")
    parser.add_argument("--json", action="store_true", help="Print output as JSON")
    args = parser.parse_args(argv)

    if args.rank_questions or not args.query:
        ranked = rank_questions(args.page)
        if args.json:
            print(json.dumps({"page": args.page, "questions": ranked}, indent=2))
        else:
            print(f"Questions for {args.page}:")
            for q in ranked:
                print(f"  - {q}")
        return 0

    resolved = compile_intent(args.query)
    if args.json:
        print(
            json.dumps(
                {
                    "capability": resolved.capability,
                    "confidence": resolved.confidence,
                    "operation_name": resolved.operation_name,
                    "arguments": resolved.arguments,
                    "disambiguation": resolved.disambiguation,
                },
                indent=2,
            )
        )
    else:
        print(f"Capability: {resolved.capability} ({resolved.operation_name}) [{resolved.confidence}]")
        if resolved.disambiguation:
            print(f"Disambiguation: {', '.join(resolved.disambiguation)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
