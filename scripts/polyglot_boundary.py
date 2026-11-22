"""Headron cross-language boundary detector (contract v1).

Discovers structural contracts (OpenAPI, Protobuf, GraphQL, SQL migrations)
spanning language boundaries from concrete repository evidence.
Never infers contractual dependencies from file naming coincidences alone.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class CrossLanguageContract:
    source_route: str
    target_route: str
    contract_type: str  # api_schema, database_migration, protobuf, graphql, binding
    evidence_path: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def detect_cross_language_contracts(root: Path) -> list[CrossLanguageContract]:
    """Scan project root for concrete cross-language boundary evidence."""
    contracts: list[CrossLanguageContract] = []
    if not root.is_dir():
        return contracts

    # 1. Protobuf / gRPC definitions
    for proto in root.glob("**/*.proto"):
        if any(part.startswith(".") or part in ("build", "dist", "node_modules", "vendor") for part in proto.parts):
            continue
        rel = proto.relative_to(root).as_posix()
        contracts.append(
            CrossLanguageContract(
                source_route="protobuf", target_route="polyglot", contract_type="protobuf", evidence_path=rel
            )
        )

    # 2. OpenAPI / Swagger schemas
    for schema_pattern in (
        "**/openapi.json",
        "**/openapi.yaml",
        "**/openapi.yml",
        "**/swagger.json",
        "**/swagger.yaml",
    ):
        for schema_file in root.glob(schema_pattern):
            if any(
                part.startswith(".") or part in ("build", "dist", "node_modules", "vendor")
                for part in schema_file.parts
            ):
                continue
            rel = schema_file.relative_to(root).as_posix()
            contracts.append(
                CrossLanguageContract(
                    source_route="api", target_route="polyglot", contract_type="api_schema", evidence_path=rel
                )
            )

    # 3. GraphQL schemas
    for gql in root.glob("**/*.graphql"):
        if any(part.startswith(".") or part in ("build", "dist", "node_modules", "vendor") for part in gql.parts):
            continue
        rel = gql.relative_to(root).as_posix()
        contracts.append(
            CrossLanguageContract(
                source_route="graphql", target_route="polyglot", contract_type="graphql", evidence_path=rel
            )
        )

    # 4. Database migrations (SQL cross-language boundary)
    for mig_dir in root.glob("**/migrations"):
        if any(part.startswith(".") or part in ("build", "dist", "node_modules", "vendor") for part in mig_dir.parts):
            continue
        if mig_dir.is_dir():
            sql_files = list(mig_dir.glob("*.sql"))
            if sql_files:
                rel = mig_dir.relative_to(root).as_posix()
                contracts.append(
                    CrossLanguageContract(
                        source_route="sql",
                        target_route="polyglot",
                        contract_type="database_migration",
                        evidence_path=rel,
                    )
                )

    # Deduplicate and sort by evidence_path
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[CrossLanguageContract] = []
    for c in sorted(contracts, key=lambda x: x.evidence_path):
        key = (c.source_route, c.target_route, c.contract_type, c.evidence_path)
        if key not in seen:
            seen.add(key)
            deduped.append(c)

    return deduped
