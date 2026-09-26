#!/usr/bin/env python3
"""declarations_are_read: a block in atlas.yaml that no program reads is a promise, so each is read here.

WHY (3.11.0). An audit grepped every top-level block for a reader and found several with none: issue_routes,
model_routes membership, front_end, drift_review's settings, the paths and verbs inside topologies and
first_sweep, and branch_policy/landed_states. A block nobody reads drifts silently — front_end/reads had
already been split on its commas into six items, half of them fragments, and nothing noticed.
Each check below refuses the one shape that block can rot into; atlasinv registers them as one invariant.
"""
from __future__ import annotations

import json
import re

from atlascore import ROOT, atlas, route_targets

FRONT_END_STATES = {"planned", "built"}


def _cli_verbs() -> set[str]:
    from commands import build_parser  # noqa: PLC0415
    parser, _ = build_parser()
    sub = next(a for a in parser._actions if a.__class__.__name__ == "_SubParsersAction")  # noqa: SLF001
    return set(sub.choices)


def _mcp_servers() -> set[str]:
    path = ROOT / ".vscode/mcp.json.example"
    return set((json.loads(path.read_text(encoding="utf-8")).get("servers") or {})) if path.exists() else set()


def issue_route_errors() -> list[str]:
    a = atlas()
    known = (set(route_targets()) | set(a.get("gate_tools") or {}) | set(a.get("tool_profiles") or {})
             | {str(e.get("id")) for e in a.get("runtime_entry") or []} | set(a.get("runtime_roles") or {})
             | _mcp_servers() | set(a.get("issue_route_terms") or []))
    return [f"issue_routes/{issue} names '{term}': not a route, gate, profile, runtime, MCP server or issue_route_terms word"
            for issue, terms in (a.get("issue_routes") or {}).items() for term in terms or [] if term not in known]


def model_route_errors() -> list[str]:
    a = atlas()
    roles = a.get("runtime_roles") or {}
    members = {str(e.get("id")) for e in a.get("runtime_entry") or []} | set(roles)
    hosts = {r for r, role in roles.items() if role == "multi_agent_host"}
    errors = [f"model_routes/{work} names '{m}', which is neither a runtime_entry id nor a runtime_roles key"
              for work, ms in (a.get("model_routes") or {}).items() for m in ms or [] if m not in members]
    errors += [f"model_routes/{work} names {m}, a multi_agent_host: a host is not a model"
               for work, ms in (a.get("model_routes") or {}).items() for m in ms or [] if m in hosts]
    return errors


def front_end_errors() -> list[str]:
    spec = atlas().get("front_end") or {}
    errors = [] if spec.get("status") in FRONT_END_STATES else [f"front_end/status '{spec.get('status')}' is not one of {sorted(FRONT_END_STATES)}"]
    for item in spec.get("reads") or []:
        path = str(item).split(" ", 1)[0]
        if "(" in str(item) and ")" not in str(item) or ")" in str(item) and "(" not in str(item):
            errors.append(f"front_end/reads holds a fragment, '{item}' — a flow value split on a comma")
        elif "/" in path and path.endswith(".json") and not (ROOT / path).is_file():
            errors.append(f"front_end/reads names {path}, which is not in the tree")
    return errors


def drift_review_errors() -> list[str]:
    spec = atlas().get("drift_review") or {}
    tiers = spec.get("tiers") or {}
    errors = [] if float(spec.get("horizon_hours") or 0) > 0 else ["drift_review/horizon_hours is not positive"]
    errors += [f"drift_review/structural names {p}, which is not in the tree"
               for p in spec.get("structural") or [] if not (ROOT / str(p)).exists()]
    hot, cold = float(tiers.get("hot", 0)), float(tiers.get("cold", 0))
    if not (0 <= hot <= 1 and 0 <= cold <= 1 and hot + cold <= 1):
        errors.append(f"drift_review/tiers hot {hot} + cold {cold} is not a split of one tree")
    return errors


def prose_reference_errors() -> list[str]:
    """Backticked paths and `atlas.py <verb>` inside topologies and first_sweep must still exist."""
    a, verbs = atlas(), _cli_verbs()
    texts = [(f"topologies/{k}", json.dumps(v)) for k, v in (a.get("topologies") or {}).items()]
    texts += [("first_sweep", json.dumps(a.get("first_sweep") or {}))]
    errors: list[str] = []
    for where, text in texts:
        for token in re.findall(r"`([^`]+)`", text):
            words = token.split()
            for w in words:
                if re.fullmatch(r"[\w./-]+\.(py|md|json|yml|yaml)", w) and "<" not in w and not (ROOT / w).exists() \
                        and not (ROOT / "scripts" / w).exists():
                    errors.append(f"{where} names `{w}`, which is not in the tree")
            at = next((i for i, w in enumerate(words) if w.endswith("atlas.py")), None)
            if at is not None and at + 1 < len(words):
                verb = words[at + 1]
                if not verb.startswith("-") and verb not in verbs:
                    errors.append(f"{where} runs `atlas.py {verb}`, which the CLI does not have")
            for flag in (w for w in words if w.startswith("--")):
                script = next((w for w in words if w.endswith(".py")), None)
                source = ROOT / "scripts" / str(script).split("/")[-1] if script else None
                if source and source.is_file() and flag not in source.read_text(encoding="utf-8"):
                    errors.append(f"{where} passes `{flag}` to {script}, which never reads it")
    return errors


def landed_state_errors() -> list[str]:
    """Each declared landing state is one branchstate reports; renaming either side must fail."""
    source = (ROOT / "scripts/branchstate.py").read_text(encoding="utf-8")
    states = (atlas().get("branch_policy") or {}).get("landed_states") or {}
    return [f"branch_policy/landed_states declares '{s}', which branchstate.py never reports"
            for s in states if s not in source] or ([] if states else ["branch_policy/landed_states is empty"])


def declaration_errors() -> list[str]:
    return (issue_route_errors() + model_route_errors() + front_end_errors() + drift_review_errors()
            + prose_reference_errors() + landed_state_errors())
