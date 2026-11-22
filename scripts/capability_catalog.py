"""Headron permanent numerical capability catalog (contract v1).

Maps stable numerical operations to capability semantics independent of tool release cycles.
IDs are permanent, unique, and never recycled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class CapabilityDefinition:
    capability: int
    name: str
    contract_version: int
    description: str
    requires: tuple[str, ...]
    result_schema: str


# Permanent numerical capability registry
IDENTIFY_LANGUAGE: Final[int] = 100
IDENTIFY_PROJECT_BOUNDARY: Final[int] = 110
IDENTIFY_DIALECT: Final[int] = 120
COMPILE_OR_TYPECHECK: Final[int] = 200
FORMAT_CODE: Final[int] = 210
EXECUTE_TESTS: Final[int] = 220
ANALYZE_SECURITY: Final[int] = 230
EXECUTE_FUZZ: Final[int] = 240
RESOLVE_DEPS: Final[int] = 300
TRACE_BOUNDARY: Final[int] = 310
PRODUCE_EVIDENCE: Final[int] = 400
VALIDATE_PROOF: Final[int] = 410
EXPLAIN_RESULT: Final[int] = 500

CAPABILITY_REGISTRY: Final[dict[int, CapabilityDefinition]] = {
    IDENTIFY_LANGUAGE: CapabilityDefinition(
        capability=IDENTIFY_LANGUAGE,
        name="language.identify",
        contract_version=1,
        description="Identify language and route from file content and directory structure.",
        requires=("file_path",),
        result_schema="headron.route-result/1",
    ),
    IDENTIFY_PROJECT_BOUNDARY: CapabilityDefinition(
        capability=IDENTIFY_PROJECT_BOUNDARY,
        name="project.boundary",
        contract_version=1,
        description="Identify project boundary and build root from manifests and lockfiles.",
        requires=("directory_path",),
        result_schema="headron.boundary-result/1",
    ),
    IDENTIFY_DIALECT: CapabilityDefinition(
        capability=IDENTIFY_DIALECT,
        name="dialect.identify",
        contract_version=1,
        description="Distinguish dialect and language variants (e.g. JSON vs JSONC, TS vs TSX).",
        requires=("file_path",),
        result_schema="headron.dialect-result/1",
    ),
    COMPILE_OR_TYPECHECK: CapabilityDefinition(
        capability=COMPILE_OR_TYPECHECK,
        name="code.compile_or_typecheck",
        contract_version=1,
        description="Compile, type-check, or statically analyze code using adopted native tools.",
        requires=("project_boundary", "native_tool"),
        result_schema="headron.operation-result/1",
    ),
    FORMAT_CODE: CapabilityDefinition(
        capability=FORMAT_CODE,
        name="code.format",
        contract_version=1,
        description="Check or apply code formatting according to adopted repository style.",
        requires=("project_boundary", "native_tool"),
        result_schema="headron.operation-result/1",
    ),
    EXECUTE_TESTS: CapabilityDefinition(
        capability=EXECUTE_TESTS,
        name="tests.execute",
        contract_version=1,
        description="Execute applicable test suites using discovered native test runners.",
        requires=("project_boundary", "native_test_runner", "execution_authorization"),
        result_schema="headron.operation-result/1",
    ),
    ANALYZE_SECURITY: CapabilityDefinition(
        capability=ANALYZE_SECURITY,
        name="security.analyze",
        contract_version=1,
        description="Run security analysis, vulnerability scans, and secret scanning.",
        requires=("project_boundary", "native_security_tool"),
        result_schema="headron.operation-result/1",
    ),
    EXECUTE_FUZZ: CapabilityDefinition(
        capability=EXECUTE_FUZZ,
        name="fuzz.execute",
        contract_version=1,
        description="Run fuzz targets against native fuzzing engines.",
        requires=("project_boundary", "fuzz_harness", "execution_authorization"),
        result_schema="headron.operation-result/1",
    ),
    RESOLVE_DEPS: CapabilityDefinition(
        capability=RESOLVE_DEPS,
        name="deps.resolve",
        contract_version=1,
        description="Resolve and validate package dependencies from lockfiles and manifests.",
        requires=("manifest_path",),
        result_schema="headron.deps-result/1",
    ),
    TRACE_BOUNDARY: CapabilityDefinition(
        capability=TRACE_BOUNDARY,
        name="boundary.trace",
        contract_version=1,
        description="Trace cross-language contracts across API schemas, databases, and bindings.",
        requires=("project_boundary",),
        result_schema="headron.cross-contract-result/1",
    ),
    PRODUCE_EVIDENCE: CapabilityDefinition(
        capability=PRODUCE_EVIDENCE,
        name="evidence.produce",
        contract_version=1,
        description="Produce structured verification evidence and gate status records.",
        requires=("verification_suite",),
        result_schema="headron.receipt/1",
    ),
    VALIDATE_PROOF: CapabilityDefinition(
        capability=VALIDATE_PROOF,
        name="proof.validate",
        contract_version=1,
        description="Validate cryptographic verification receipts and provenance signatures.",
        requires=("receipt_bytes",),
        result_schema="headron.proof-result/1",
    ),
    EXPLAIN_RESULT: CapabilityDefinition(
        capability=EXPLAIN_RESULT,
        name="result.explain",
        contract_version=1,
        description="Generate deterministic explanations of verification and capability states.",
        requires=("operation_result",),
        result_schema="headron.explanation-result/1",
    ),
}


def get_capability(cap_id: int) -> CapabilityDefinition | None:
    """Retrieve capability definition by permanent ID."""
    return CAPABILITY_REGISTRY.get(cap_id)


def is_valid_capability(cap_id: int) -> bool:
    """Check if capability ID is registered."""
    return cap_id in CAPABILITY_REGISTRY


def list_capabilities() -> list[CapabilityDefinition]:
    """Return all registered capabilities sorted by ID."""
    return [CAPABILITY_REGISTRY[k] for k in sorted(CAPABILITY_REGISTRY)]
