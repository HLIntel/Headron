"""Headron polyglot capability negotiation and verification planning engine (contract v1).

Resolves project-native toolchains for capabilities (200, 210, 220, 230), negotiates execution
readiness, constructs fallback chains, and plans cross-language contract verification.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from capability_catalog import ANALYZE_SECURITY, COMPILE_OR_TYPECHECK, EXECUTE_TESTS, FORMAT_CODE, TRACE_BOUNDARY
from polyglot import inspect
from polyglot_boundary import detect_cross_language_contracts

# Tool candidate matrix by route and capability
# Structure: (route, capability_id): tuple[tuple[tool_binary, command_template], ...]
_CANDIDATE_MATRIX: dict[tuple[str, int], tuple[tuple[str, str], ...]] = {
    ("python", COMPILE_OR_TYPECHECK): (
        ("basedpyright", "basedpyright ."),
        ("pyright", "pyright ."),
        ("mypy", "mypy ."),
        ("python3", "python3 -m py_compile"),
    ),
    ("python", FORMAT_CODE): (("ruff", "ruff format --check ."), ("black", "black --check .")),
    ("python", EXECUTE_TESTS): (("pytest", "pytest"), ("python3", "python3 -m unittest discover")),
    ("python", ANALYZE_SECURITY): (("bandit", "bandit -r ."), ("ruff", "ruff check --select S .")),
    ("typescript", COMPILE_OR_TYPECHECK): (("tsc", "tsc --noEmit"), ("npm", "npm run build")),
    ("typescript", FORMAT_CODE): (("biome", "biome check ."), ("prettier", "prettier --check .")),
    ("typescript", EXECUTE_TESTS): (("vitest", "vitest run"), ("jest", "jest"), ("npm", "npm test")),
    ("typescript", ANALYZE_SECURITY): (("npm", "npm audit"), ("pnpm", "pnpm audit")),
    ("rust", COMPILE_OR_TYPECHECK): (("cargo", "cargo check"), ("rustc", "rustc")),
    ("rust", FORMAT_CODE): (("cargo", "cargo fmt --check"), ("rustfmt", "rustfmt --check")),
    ("rust", EXECUTE_TESTS): (("cargo", "cargo test"),),
    ("rust", ANALYZE_SECURITY): (("cargo-audit", "cargo audit"),),
    ("go", COMPILE_OR_TYPECHECK): (("go", "go vet ./..."),),
    ("go", FORMAT_CODE): (("gofmt", "gofmt -l ."), ("goimports", "goimports -l .")),
    ("go", EXECUTE_TESTS): (("go", "go test ./..."),),
    ("go", ANALYZE_SECURITY): (("govulncheck", "govulncheck ./..."),),
}


def negotiate_capability(capability_id: int, project_root: Path, route: str | None = None) -> dict[str, Any]:
    """Negotiate toolchain execution readiness and fallback chain for a capability."""
    root = project_root.resolve()
    target_route = route
    if not target_route:
        fp = inspect(root)
        target_route = fp["languages"][0] if fp["languages"] else "python"

    candidates = _CANDIDATE_MATRIX.get((target_route, capability_id), ())
    if not candidates:
        return {
            "capability": capability_id,
            "route": target_route,
            "status": "unsupported",
            "selected_tool": None,
            "command": None,
            "fallback_chain": [],
            "reason": f"No native tool candidates defined for route '{target_route}' and capability {capability_id}.",
        }

    # Evaluate candidate availability
    available_tools: list[dict[str, str]] = []
    fallback_chain: list[str] = []
    for tool_bin, cmd in candidates:
        if shutil.which(tool_bin):
            available_tools.append({"tool": tool_bin, "command": cmd})
        else:
            fallback_chain.append(f"Install native runner '{tool_bin}' or configure script.")

    if available_tools:
        selected = available_tools[0]
        return {
            "capability": capability_id,
            "route": target_route,
            "status": "ready",
            "selected_tool": selected["tool"],
            "command": selected["command"],
            "fallback_chain": fallback_chain,
            "reason": f"Tool '{selected['tool']}' is installed and ready for execution.",
        }

    return {
        "capability": capability_id,
        "route": target_route,
        "status": "unavailable",
        "selected_tool": None,
        "command": candidates[0][1],
        "fallback_chain": fallback_chain,
        "reason": f"Required native toolchain for route '{target_route}' is not installed on this machine.",
    }


def plan_cross_language_verification(target_file: Path, project_root: Path) -> dict[str, Any]:
    """Plan verification sequence when a file intersects cross-language contract boundaries."""
    root = project_root.resolve()
    target = target_file.resolve()
    try:
        rel_target = target.relative_to(root).as_posix()
    except ValueError:
        rel_target = target.as_posix()

    contracts = detect_cross_language_contracts(root)
    affected_contracts: list[dict[str, Any]] = []

    # Check which contracts encompass or match the target file
    for c in contracts:
        cdict = c.to_dict()
        evidence_path = cdict.get("evidence_path", "")
        if (
            rel_target.startswith(evidence_path)
            or evidence_path.startswith(rel_target)
            or target.suffix in (".proto", ".graphql", ".sql")
        ):
            affected_contracts.append(cdict)

    verification_steps: list[dict[str, Any]] = []
    if affected_contracts:
        verification_steps.append(
            {
                "step": 1,
                "capability": TRACE_BOUNDARY,
                "action": "validate_contract_schemas",
                "targets": [c["evidence_path"] for c in affected_contracts],
                "description": "Verify contract schema integrity across participating language routes.",
            }
        )
        routes = sorted(
            {c["source_route"] for c in affected_contracts} | {c["target_route"] for c in affected_contracts}
        )
        verification_steps.append(
            {
                "step": 2,
                "capability": COMPILE_OR_TYPECHECK,
                "action": "typecheck_producers_and_consumers",
                "targets": routes,
                "description": "Compile both producer stubs and consumer applications across language boundaries.",
            }
        )
        verification_steps.append(
            {
                "step": 3,
                "capability": EXECUTE_TESTS,
                "action": "run_integration_and_boundary_tests",
                "targets": [c["evidence_path"] for c in affected_contracts],
                "description": "Execute cross-language contract and compatibility tests.",
            }
        )
    else:
        # Standard single-route verification
        verification_steps.append(
            {
                "step": 1,
                "capability": COMPILE_OR_TYPECHECK,
                "action": "compile_or_typecheck",
                "targets": [rel_target],
                "description": "Typecheck target file within its home project boundary.",
            }
        )
        verification_steps.append(
            {
                "step": 2,
                "capability": EXECUTE_TESTS,
                "action": "execute_tests",
                "targets": [rel_target],
                "description": "Run unit and behavioral tests for target file.",
            }
        )

    return {
        "target": rel_target,
        "is_cross_language": bool(affected_contracts),
        "affected_contracts": affected_contracts,
        "plan_steps": verification_steps,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher for capability negotiation and verification planning."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Headron polyglot capability negotiation engine")
    parser.add_argument("target", help="Capability ID (int) or target file path")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--route", help="Language route override (python, rust, go, typescript)")
    parser.add_argument("--json", action="store_true", help="Print structured JSON result")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()

    if args.target.isdigit():
        cap_id = int(args.target)
        res = negotiate_capability(cap_id, root, route=args.route)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Capability {cap_id} [{res['route']}]: {res['status'].upper()} ({res['reason']})")
            if res.get("command"):
                print(f"Command: {res['command']}")
        return 0 if res["status"] in ("ready", "unsupported") else 1

    plan = plan_cross_language_verification(Path(args.target), root)
    if args.json:
        print(json.dumps(plan, indent=2))
    else:
        boundary_label = "CROSS-LANGUAGE" if plan["is_cross_language"] else "LOCAL"
        print(f"Target: {plan['target']} [{boundary_label}] | Steps: {len(plan['plan_steps'])}")
        for step in plan["plan_steps"]:
            print(f"  Step {step['step']}: {step['action']} (cap: {step['capability']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
