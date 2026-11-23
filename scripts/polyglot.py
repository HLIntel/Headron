"""Headron polyglot capability resolver facade (contract v1).

Provides language-aware project inspection, capability resolution, and deterministic explanations
without requiring LLMs or updates on tool release cycles.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
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
    get_capability,
    list_capabilities,
)
from polyglot_boundary import detect_cross_language_contracts, discover_boundaries
from polyglot_plan import negotiate_capability

# Manifest to route and build system mapping
MANIFEST_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("pyproject.toml", "python", "uv"),
    ("Cargo.toml", "rust", "cargo"),
    ("go.mod", "go", "go"),
    ("package.json", "typescript", "npm/pnpm"),
    ("pom.xml", "java", "maven"),
    ("build.gradle", "java", "gradle"),
    ("Package.swift", "swift", "swiftpm"),
    ("CMakeLists.txt", "cpp", "cmake"),
)


def _detect_boundaries(root: Path) -> list[dict[str, str]]:
    """Detect project and module boundaries by manifest presence."""
    boundaries: list[dict[str, str]] = []
    for manifest_name, route, _ in MANIFEST_ROUTES:
        for manifest_path in root.glob(f"**/{manifest_name}"):
            if any(
                part.startswith(".") or part in ("build", "dist", "node_modules", "vendor")
                for part in manifest_path.parts
            ):
                continue
            rel_root = manifest_path.parent.relative_to(root).as_posix()
            boundaries.append(
                {
                    "root": rel_root if rel_root else ".",
                    "route": route,
                    "manifest": manifest_path.relative_to(root).as_posix(),
                }
            )
    return sorted(boundaries, key=lambda b: (b["root"], b["route"]))


def inspect(project_root: Path) -> dict[str, Any]:
    """Compute project language fingerprint and boundaries (schema: headron.polyglot/1)."""
    boundaries = _detect_boundaries(project_root)
    languages = sorted({b["route"] for b in boundaries})
    primary_build = "unknown"
    for manifest_name, _, build_sys in MANIFEST_ROUTES:
        if (project_root / manifest_name).exists():
            primary_build = build_sys
            break

    # Resolve available operations
    available: list[int] = [
        IDENTIFY_LANGUAGE,
        IDENTIFY_PROJECT_BOUNDARY,
        IDENTIFY_DIALECT,
        RESOLVE_DEPS,
        TRACE_BOUNDARY,
        PRODUCE_EVIDENCE,
        VALIDATE_PROOF,
        EXPLAIN_RESULT,
    ]
    unavailable: list[int] = []

    # Probing execution-capable operations based on discovered routes & native tools
    has_runner = bool(shutil.which("pytest") or shutil.which("cargo") or shutil.which("go") or shutil.which("npm"))
    if has_runner and boundaries:
        available.extend([COMPILE_OR_TYPECHECK, FORMAT_CODE, EXECUTE_TESTS, ANALYZE_SECURITY])
    else:
        unavailable.extend([COMPILE_OR_TYPECHECK, FORMAT_CODE, EXECUTE_TESTS, ANALYZE_SECURITY])

    # Fuzzing requires dedicated harness
    if (project_root / "fuzz").exists() or (project_root / "tests/fuzz").exists():
        available.append(EXECUTE_FUZZ)
    else:
        unavailable.append(EXECUTE_FUZZ)

    contracts = [c.to_dict() for c in detect_cross_language_contracts(project_root)]

    return {
        "command": "polyglot",
        "schema": 1,
        "kind": "headron.polyglot",
        "project_id": project_root.name or "project",
        "revision": "HEAD",
        "languages": languages if languages else ["polyglot"],
        "primary_build_system": primary_build,
        "boundaries": boundaries,
        "capabilities_available": sorted(available),
        "capabilities_unavailable": sorted(unavailable),
        "cross_language_contracts": contracts,
        "status": "resolved" if boundaries else "partial",
    }


def capabilities(project_root: Path) -> dict[int, dict[str, Any]]:
    """Determine availability of every permanent capability for this project."""
    fp = inspect(project_root)
    avail_set = set(fp["capabilities_available"])
    result: dict[int, dict[str, Any]] = {}

    for cap in list_capabilities():
        cid = cap.capability
        is_avail = cid in avail_set
        result[cid] = {
            "capability": cid,
            "name": cap.name,
            "status": "available" if is_avail else "unavailable",
            "requires": list(cap.requires),
            "schema": cap.result_schema,
        }
    return result


def explain(fingerprint: dict[str, Any], capability_id: int) -> dict[str, Any]:
    """Generate deterministic structured explanation of a capability state."""
    cap = get_capability(capability_id)
    if not cap:
        return {
            "capability": capability_id,
            "status": "unregistered",
            "explanation": f"Capability ID {capability_id} is not registered in Headron.",
            "next_action": "Consult capability catalog schema",
        }

    is_avail = capability_id in fingerprint.get("capabilities_available", [])
    if is_avail:
        return {
            "capability": capability_id,
            "name": cap.name,
            "status": "available",
            "explanation": f"Operation {cap.name} ({capability_id}) is available for this project.",
            "next_action": f"Execute capability {cap.name} via authorized verifier",
        }

    return {
        "capability": capability_id,
        "name": cap.name,
        "status": "unavailable",
        "explanation": f"Operation {cap.name} ({capability_id}) lacks required runtime or manifest prerequisites.",
        "prerequisites_needed": list(cap.requires),
        "next_action": "Install required toolchain or configure project manifest",
    }


def _emit_explain(fp: dict[str, Any], cid: int, as_json: bool) -> int:
    res = explain(fp, cid)
    res["command"] = "polyglot"
    print(json.dumps(res, indent=2) if as_json else f"[{res['status'].upper()}] {res['explanation']}")
    return 0


def _emit_boundaries(root: Path, as_json: bool) -> int:
    bounds = discover_boundaries(root)
    if as_json:
        print(json.dumps({"command": "polyglot", "boundaries": [b.to_dict() for b in bounds]}, indent=2))
        return 0
    print(f"Discovered {len(bounds)} cross-language boundary contract(s):")
    for b in bounds:
        print(f"  [{b.contract_type}] {b.source_route} -> {b.target_route} ({b.evidence_path})")
    return 0


def _emit_plan(root: Path, plan_id: int, as_json: bool) -> int:
    res = negotiate_capability(plan_id, root)
    res["command"] = "polyglot"
    if as_json:
        print(json.dumps(res, indent=2))
        return 0
    print(f"Negotiation for capability {plan_id}: {res['status']}")
    print(f"  Route: {res['route']} | Selected tool: {res.get('selected_tool') or 'none'}")
    print(f"  Command: {res.get('command') or 'none'}")
    for fb in res.get("fallback_chain", []):
        print(f"    - {fb}")
    return 0


def _emit_capabilities(root: Path, as_json: bool) -> int:
    c_map = capabilities(root)
    if as_json:
        print(json.dumps({"command": "polyglot", "capabilities": c_map}, indent=2))
        return 0
    for cid, data in sorted(c_map.items()):
        print(f"[{data['status'].upper():11}] {cid} {data['name']}")
    return 0


def _emit_fingerprint(fp: dict[str, Any], as_json: bool) -> int:
    if as_json:
        print(json.dumps(fp, indent=2))
        return 0
    print(f"Project: {fp['project_id']} (build: {fp['primary_build_system']})")
    print(f"Languages: {', '.join(fp['languages'])} | Boundaries: {len(fp['boundaries'])}")
    print(
        f"Capabilities available: {len(fp['capabilities_available'])} | Contracts: {len(fp['cross_language_contracts'])}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher for polyglot inspection and capability querying."""
    parser = argparse.ArgumentParser(description="Headron polyglot capability resolver")
    parser.add_argument("path", nargs="?", default=".", help="Project path to inspect")
    parser.add_argument("--json", action="store_true", help="Print fingerprint as JSON")
    parser.add_argument("--capabilities", action="store_true", help="Print all capabilities status")
    parser.add_argument("--boundaries", action="store_true", help="Print discovered cross-language boundaries")
    parser.add_argument("--plan", type=int, help="Plan cross-language verification for capability ID")
    parser.add_argument("--explain", type=int, help="Explain specific capability ID")
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    fp = inspect(root)

    if args.explain:
        return _emit_explain(fp, args.explain, args.json)
    if args.boundaries:
        return _emit_boundaries(root, args.json)
    if args.plan is not None:
        return _emit_plan(root, args.plan, args.json)
    if args.capabilities:
        return _emit_capabilities(root, args.json)
    return _emit_fingerprint(fp, args.json)


if __name__ == "__main__":
    raise SystemExit(main())
