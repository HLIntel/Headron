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


SLOW_GUIDES = ("integrations/", "patterns/", "systems/", "wiki/", "languages/")


def guide_reference_errors() -> list[str]:
    """Hand-written guides must not name a harness script or an `atlas.py` verb that no longer exists.

    MEASURED (3.14.0, 60 days of history): generated files change hourly and cannot drift; these guides
    change about daily, are written by hand, and name scripts that change hourly — the one place a
    reference goes stale unseen. The check is that stale edge: every `scripts/x.py` and verb they cite.
    """
    from atlascore import tracked  # noqa: PLC0415
    verbs, errors = _cli_verbs(), []
    for path in tracked():
        rel = str(path.relative_to(ROOT))
        if not rel.startswith(SLOW_GUIDES) or path.suffix != ".md":
            continue
        for token in re.findall(r"`([^`\n]+)`", path.read_text(encoding="utf-8")):
            words = token.split()
            errors += [f"{rel} names `{w}`, which is not in the tree" for w in words
                       if re.fullmatch(r"scripts/[\w.-]+\.py", w) and not (ROOT / w).exists()]
            at = next((i for i, w in enumerate(words) if w.endswith("atlas.py")), None)
            if at is not None and at + 1 < len(words) and words[at + 1][0] not in "-<" and words[at + 1] not in verbs:
                errors.append(f"{rel} runs `atlas.py {words[at + 1]}`, which the CLI does not have")
    return errors


def role_errors() -> list[str]:
    """Every role runs under a declared task profile and process, and says what it hands back and when it ends."""
    a = atlas()
    errors = []
    for name, spec in (a.get("agent_roles") or {}).items():
        spec = spec or {}
        errors += [f"agent_roles/{name} names no {f}" for f in ("task_profile", "may", "may_not", "hands_back", "ends_when")
                   if not str(spec.get(f) or "").strip()]
        if spec.get("task_profile") not in (a.get("task_profiles") or {}):
            errors.append(f"agent_roles/{name} runs under task profile '{spec.get('task_profile')}', which is not declared")
        if spec.get("process") and spec["process"] not in (a.get("processes") or {}):
            errors.append(f"agent_roles/{name} follows process '{spec['process']}', which is not declared")
    return errors or ([] if a.get("agent_roles") else ["atlas.yaml declares no agent_roles"])


COUNTED = (r"language|route|pack|gate|test|case|instrument|invariant|file|document|module|script|tool|manifest|"
           r"model|runtime|token|command|check|shape|extension|question|task|entr(?:y|ies)|dependenc(?:y|ies)|line|KiB|MiB|MB")
NUMBER = re.compile(r"(?<![\w.v/-])(\d[\d,]*\d|\d{2,})\s+(?:" + COUNTED + r")s?\b", re.I)
# A PERCENTAGE IS A CLAIM TOO (3.22.0). The first guard read only a digit beside a counted noun, so every
# "90% fewer tokens" walked past it — the most quotable shape in the repository, and the one a reader trusts most.
PERCENT = re.compile(r"(?<![\w.-])\d{1,3}(?:\.\d+)?\s?%")
STAMP = re.compile(r"measured at v?\d+\.\d+|\bv?\d+\.\d+\.\d+\b|\b20\d\d-\d\d-\d\d\b")
# THE RULE'S OWN ESCAPES, not an exemption list: "generate it, or NAME THE INSTRUMENT that prints it" —
# so a line naming a scripts/*.py, carrying a source URL, or attributing a quoted law to its author
# (Cargill, Brooks) is already answering the question the guard asks.
SOURCED = re.compile(r"scripts/[\w.-]+\.py|https?://|\([A-Z][a-z]+(?:[ &-][A-Z][a-z]+)*\)")


def number_drift_errors() -> list[str]:
    """No number typed beside a counted thing in ANY tracked document, unless it is stamped as a record (3.21.0).

    THE OWNER'S HARDEST RULE. A live count is generated or named by the instrument that prints it; a past
    measurement is a record and carries the version it was measured at. Its first sweep found 18: one stale
    ("29 language routes" against 36), three caps restated beside the constants that enforce them (one of
    which, an advisory 80-line function limit, contradicted the enforced cap), and fourteen unstamped
    records. Generated files and blocks are exempt: the build computed those numbers.
    """
    from atlascore import tracked  # noqa: PLC0415
    generated = set(atlas().get("generated_files") or [])
    errors = []
    for path in tracked():
        rel = str(path.relative_to(ROOT))
        if path.suffix not in (".md", ".txt") or rel in generated or not path.is_file():
            continue
        text = re.sub(r"<!-- BEGIN generated.*?<!-- END generated[^>]*-->", "", path.read_text(encoding="utf-8"), flags=re.S)
        if text.lstrip().startswith(("# CLAUDE.md", "# AGENTS.md", "<!-- GENERATED")) or "GENERATED by" in text[:400]:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            # A COMMAND LINE IS NOT A SOURCE: `python scripts/atlas.py gate ... # 90% fewer tokens` names the
            # command being documented, not the instrument that measured the claim beside it (3.22.0).
            if STAMP.search(line) or (SOURCED.search(line) and not re.match(r"\s*(\$|python|thea|git|gh)\b", line)):
                continue
            errors += [f"{rel}:{n} types '{m.group(0)}' — generate it, name its instrument, or stamp it (measured at vX)"
                       for m in list(NUMBER.finditer(line)) + list(PERCENT.finditer(line))]
    return errors


def decision_evidence_errors() -> list[str]:
    """Every decision carries data (a number with a source), a trend and the human side — or waits on the backlog."""
    from knowledge import decision_records  # noqa: PLC0415
    records, backlog = decision_records(), set(atlas().get("decision_evidence_backlog") or [])
    errors = []
    for name, spec in records.items():
        ev = (spec or {}).get("evidence") or {}
        if name in backlog:
            if ev:
                errors.append(f"decision {name} now has evidence — remove it from decision_evidence_backlog")
            continue
        missing = [f for f in ("data", "trend", "human") if not str(ev.get(f) or "").strip()]
        if missing:
            errors.append(f"decision {name} carries no evidence {'/'.join(missing)}: data with its source, the trend, who pays")
        elif not re.search(r"\d|UNMEASURED", str(ev["data"])) or not re.search(r"https?://|\.py\b|UNMEASURED", str(ev["data"])):
            errors.append(f"decision {name} evidence/data holds no number with a source (or an explicit UNMEASURED)")
    errors += [f"decision_evidence_backlog names {b}, which is not a decision" for b in backlog - set(records)]
    return errors


def hook_parity_errors() -> list[str]:
    """What the commit hook enforces, verify and CI must enforce too — a hook-only gate is a local habit."""
    hook = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8") if (ROOT / ".githooks" / "pre-commit").is_file() else ""
    done = [" ".join(g["argv"]).replace("python ", "", 1) for g in (atlas().get("verification_policy") or {}).get("done_set") or []]
    ran = re.findall(r"scripts/[\w]+\.py(?: check)?|ruff check \.", hook)
    return [f".githooks/pre-commit runs `{r}`, which verification_policy/done_set does not — the hook and verify disagree"
            for r in ran if not any(r in d or d in r for d in done)]


def cadence_errors() -> list[str]:
    """The time box adds up, reserves its verification, and refuses to lower the bar when the clock runs out."""
    spec = atlas().get("cadence") or {}
    if not spec:
        return ["atlas.yaml declares no cadence: a timed session with no declared phases is prose in a prompt file"]
    phases = spec.get("phases") or []
    errors = [f"cadence/{p.get('id')} declares no {f}" for p in phases for f in ("does", "exits") if not str(p.get(f) or "").strip()]
    weights, box = sum(float(p.get("weight") or 0) for p in phases), float(spec.get("box_minutes") or 0)
    if weights != box:
        errors.append(f"cadence phase weights sum to {weights:g} against a box of {box:g} minutes — the clock does not add up")
    reserves = [p["id"] for p in phases if p.get("reserve")]
    if len(reserves) != 1:
        errors.append(f"cadence declares {len(reserves)} reserve phases, not one — a verification budget taken from "
                      "what is left at the end is the budget that gets dropped")
    if not any("verify" in str(d) for d in spec.get("definition_of_done") or []):
        errors.append("cadence/definition_of_done does not name verify — a done that the agent judges for itself")
    if int(spec.get("wip") or 0) != 1:
        errors.append(f"cadence/wip is {spec.get('wip')}: a solo agent's only lever on cycle time is one change in flight")
    marks = [float(c) for c in spec.get("checkpoints") or []]
    if not marks or marks != sorted(marks) or not all(0 < c < 1 for c in marks):
        errors.append("cadence/checkpoints must be an ascending list strictly inside the box")
    errors += [] if spec.get("never_under_pressure") else ["cadence declares nothing that is never done under time pressure"]
    return errors


def process_return_errors() -> list[str]:
    """Every process says what it hands back and to whom — an agent must know where its work returns."""
    return [f"processes/{p} names no returns: an agent finishing it would not know what to hand back"
            for p, spec in (atlas().get("processes") or {}).items() if not str((spec or {}).get("returns") or "").strip()]


def declaration_errors() -> list[str]:
    return cadence_errors() + role_errors() + process_return_errors() + guide_reference_errors() + number_drift_errors() + \
        decision_evidence_errors() + hook_parity_errors() + (issue_route_errors() + model_route_errors() + front_end_errors() + drift_review_errors()
            + prose_reference_errors() + landed_state_errors())
