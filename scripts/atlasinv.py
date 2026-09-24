#!/usr/bin/env python3
"""The hard invariants: one function per promise, and the roster that refuses an unowned one.

WHY THIS IS SEPARATE (2.9.0). scripts/atlas.py crossed MAX_CODE_LINES — its own guard, on its own
file — the moment the agent controls were wired in. The answer to a file hitting its cap is to
split it by concern, not to raise the cap on the guard that caught it; atlascore.py exists for the
same reason and says so.

The concern is clean: atlas.yaml DECLARES the invariants, this module DECIDES each one, and
atlas.py runs the contract and owns the CLI. The arrows point one way — nothing here imports
atlas.py.

The split also repaired the instrument roster, which claimed `atlas.py invariants` was
scripts/atlasgen.py: true only in the sense that both were files nobody had re-read. The generator
now carries its own entry and this module carries the one named after what it does.
"""
from __future__ import annotations

import re

import yaml
from agentpolicy import agent_policy_errors, authority_class_errors, gate_tool_errors
from atlascore import (
    BLOB_SUFFIXES,
    CODE_SUFFIXES,
    MAX_BLOB_BYTES,
    MAX_CODE_LINES,
    MAX_DEFAULT_TOOLS,
    ORPHAN_ROOTS,
    ROOT,
    atlas,
    read,
    read_jsonc,
    rel,
    route_targets,
    tracked,
)
from atlasgen import BLOCKS, _begin
from contextcost import entry_cost_errors
from packmanifest import MANIFEST_SCHEMA


# EVERY HARD INVARIANT IS ENFORCED OR DECLARED — NEVER BOTH, NEVER NEITHER.
#
# atlas.yaml lists 25 hard_invariants and, until 1.0.2, not one of them was read
# by code: a list of promises that accrued authority from being written down.
# Each name below maps to either a CHECK (a function run by check(), which fails
# the contract) or a DECLARATION (a stated reason it cannot be checked HERE, which
# is a promise to come back, not an exemption). check() fails on any invariant in
# atlas.yaml that appears in neither, and prints the split every run.
def _inv_workflows_run_the_contract() -> str | None:
    """ci_enforces_contract — the CI file must actually invoke the harness."""
    ci = read(".github/workflows/atlas-ci.yml")
    missing = [c for c in ("atlas.py check", "atlas_test.py", "agent_test.py",
                           "agentrun.py", "bench.py", "atlasindex.py")
               if c not in ci]
    return f"atlas-ci.yml does not run: {', '.join(missing)}" if missing else None


def _inv_least_privilege() -> str | None:
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        text = wf.read_text(encoding="utf-8")
        if "permissions: write-all" in text or "permissions: {}" not in text and "contents: read" not in text:
            return f"{rel(wf)} does not start from a read-only permission floor"
    return None


def _inv_native_tools_authoritative() -> str | None:
    for language in route_targets():
        path = ROOT / "languages" / language / "tools.yaml"
        if not path.exists():
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not (data.get("authority") or {}).get("compiler_or_runtime"):
            return f"languages/{language}/tools.yaml names no compiler_or_runtime"
    return None


def _inv_warnings_are_classified() -> str | None:
    severity = (atlas().get("verification_policy") or {}).get("severity") or {}
    missing = [s for s in ("blocker", "error", "warning", "info", "baseline") if s not in severity]
    return f"verification_policy.severity is missing: {', '.join(missing)}" if missing else None


def _inv_no_hidden_baseline() -> str | None:
    if not (atlas().get("verification_policy") or {}).get("baseline_rule"):
        return "verification_policy.baseline_rule is not declared"
    stray = [rel(p) for p in tracked() if p.name in {"baseline.json", ".semgrep_baseline", "baseline.sarif"}]
    return f"a findings baseline file is tracked: {', '.join(stray)}" if stray else None


def _inv_model_choice_task_scoped() -> str | None:
    return None if (atlas().get("model_routes") or {}) else "atlas.yaml/model_routes is empty"


def _inv_context_progressive() -> str | None:
    """context_is_progressively_disclosed — MEASURED at the entry, not asserted by a non-empty list.

    This read `forbidden_default` and returned None if the list had anything in it, which made the
    invariant true of any repository that had typed three words into a YAML file. Progressive
    disclosure is a claim about BYTES HANDED OVER before a question is asked, and until 2.10.0
    nothing counted them — so the entry path could grow a page at a time with this check green.
    """
    policy = atlas().get("context_policy") or {}
    if not policy.get("forbidden_default"):
        return "context_policy.forbidden_default is empty — nothing is excluded by default"
    over = entry_cost_errors()
    return f"the entry path is not held to its declared cost: {over[0]}" if over else None


def _inv_task_verification_explicit() -> str | None:
    profiles = (atlas().get("verification_policy") or {}).get("profiles") or {}
    empty = [k for k, v in profiles.items() if not (v or {}).get("required")]
    return f"verification gates with no required list: {', '.join(empty)}" if empty else None


def _inv_polyglot_boundaries() -> str | None:
    doc = read("systems/POLYGLOT-ENGINEERING.md")
    return None if "boundary" in doc.lower() else "POLYGLOT-ENGINEERING.md does not define a boundary"


# --- the remaining sixteen, promoted from DECLARED to ENFORCED (1.1.0) --------
# Each asserts a property of THIS repository's own artifacts. None asserts a
# property of a consuming system — that would be a check that cannot fail, which
# is worse than a declaration because it reads as coverage.
def _inv_no_unbounded_growth() -> str | None:
    """Nothing tracked here may grow without a cap, and the caps must be real."""
    over = [f"{rel(p)} ({p.stat().st_size} B)" for p in tracked()
            if p.is_file() and p.suffix.lower() in BLOB_SUFFIXES and p.stat().st_size > MAX_BLOB_BYTES]
    if over:
        return "tracked blob over the declared cap: " + ", ".join(over)
    streams = [rel(p) for p in tracked() if p.suffix.lower() in {".log", ".jsonl", ".ndjson"}]
    return f"an append-only stream is tracked with no rotation: {', '.join(streams)}" if streams else None


def _inv_code_blobs_are_bounded() -> str | None:
    over = []
    for path in tracked():
        if path.suffix.lower() in CODE_SUFFIXES and path.is_file():
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                n = sum(1 for _ in fh)
            if n > MAX_CODE_LINES:
                over.append(f"{rel(path)} ({n} lines)")
    return "code file over MAX_CODE_LINES: " + ", ".join(over) if over else None


def _inv_tool_surfaces_are_bounded() -> str | None:
    """A manifest that defaults to everything is not a bounded surface."""
    for language in route_targets():
        path = ROOT / "languages" / language / "tools.yaml"
        if not path.exists():
            continue
        policy = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("policy") or {}
        default = policy.get("default_tools") or []
        if len(default) > MAX_DEFAULT_TOOLS:
            return f"languages/{language}/tools.yaml defaults to {len(default)} tools (cap {MAX_DEFAULT_TOOLS})"
        if not policy.get("avoid_by_default"):
            return f"languages/{language}/tools.yaml names nothing to avoid by default"
    return None


def _inv_one_source_of_truth() -> str | None:
    """A generated block may live only where the registry says it does."""
    for name, (files, _) in BLOCKS.items():
        for path in tracked():
            if path.suffix.lower() != ".md" or path.is_symlink():
                continue
            if _begin(name) in path.read_text(encoding="utf-8", errors="replace") and rel(path) not in files:
                return f"generated block '{name}' also appears in {rel(path)}, which the registry does not own"
    return None


def _inv_atlas_consistency() -> str | None:
    for language in route_targets():
        for artifact in ("README.md", "OPERATING.md", "tools.yaml"):
            if not (ROOT / "languages" / language / artifact).exists():
                return f"route {language} has no {artifact}"
    if str(atlas().get("version")) != read("VERSION").strip():
        return "atlas.yaml version and VERSION disagree"
    return None


def _inv_durable_artifacts_reachable() -> str | None:
    """Every durable document must be linked from somewhere (check() proves it)."""
    unreferenced = [d for d in ORPHAN_ROOTS if not (ROOT / d).is_dir()]
    return f"a declared documentation root is missing: {', '.join(unreferenced)}" if unreferenced else None


def _inv_auditable_changes() -> str | None:
    owners = [ln for ln in read(".github/CODEOWNERS").splitlines() if ln.strip() and not ln.startswith("#")]
    if not owners:
        return "CODEOWNERS declares no owner, so nothing has a reviewer"
    if not any(ln.split()[0] == "*" for ln in owners):
        return "CODEOWNERS has no default (*) rule, so new paths land unowned"
    template = read(".github/pull_request_template.md")
    missing = [s for s in ("## Verification", "## Breakage review") if s not in template]
    return f"pull_request_template.md is missing: {', '.join(missing)}" if missing else None


def _inv_schema_first() -> str | None:
    """Every machine-read file must parse before anything reads it."""
    import json as _json
    try:
        yaml.safe_load(read("atlas.yaml"))
        _json.loads(read("config/github-labels.json"))
        _json.loads(read("config/github-controls.json"))
        _json.loads(read(MANIFEST_SCHEMA))
        for language in route_targets():
            path = ROOT / "languages" / language / "tools.yaml"
            if path.exists():
                yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, ValueError) as exc:
        return f"a machine-read file does not parse: {exc.__class__.__name__}"
    return None


def _inv_immutable_first() -> str | None:
    """No mutable runtime state is tracked: this repository ships documents."""
    state = [rel(p) for p in tracked()
             if p.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".log"} or p.name.endswith(".state.json")]
    return f"mutable runtime state is tracked: {', '.join(state)}" if state else None


def _inv_explicit_deadlines() -> str | None:
    """Every CI job declares a timeout. A job with none hangs until GitHub kills it."""
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        data = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
        for job, spec in (data.get("jobs") or {}).items():
            if "timeout-minutes" not in (spec or {}):
                return f"{rel(wf)} job '{job}' declares no timeout-minutes"
    return None


def _inv_rollback_high_impact() -> str | None:
    """Every released version is named in the changelog, so any change is revertable to one."""
    version = read("VERSION").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        return f"VERSION {version!r} is not semver, so no release can be named"
    if not re.search(rf"^{re.escape(version)} ", read("docs/VERSIONING.md"), re.MULTILINE):
        return f"version {version} has no line in docs/VERSIONING.md"
    return None


def _inv_independent_verification() -> str | None:
    """The contract is checked by a second artifact, on a second machine."""
    if not (ROOT / "scripts" / "atlas_test.py").exists():
        return "scripts/atlas_test.py is absent: the harness verifies only itself"
    ci = read(".github/workflows/atlas-ci.yml")
    if "atlas_test.py" not in ci:
        return "CI does not run the harness test, so verification is local only"
    return None


def _inv_ide_is_not_enforcement() -> str | None:
    """No CI gate may depend on an editor file. This IS assertable, negatively."""
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        if ".vscode" in wf.read_text(encoding="utf-8"):
            return f"{rel(wf)} references .vscode — an IDE convenience became a gate"
    return None


def _inv_mcp_is_task_scoped() -> str | None:
    """Every server shipped in the example must be named by a published profile."""
    import json as _json
    example = _json.loads(read(".vscode/mcp.json.example"))
    servers = set((example.get("servers") or {}).keys())
    published = read("integrations/MCP-PROFILES.md") + read("integrations/MCP-LANGUAGE-MATRIX.md") + read("atlas.yaml")
    unscoped = sorted(s for s in servers if s.lower() not in published.lower())
    if unscoped:
        return f"mcp.json.example ships servers no profile names: {', '.join(unscoped)}"
    blob = _json.dumps(example)
    if re.search(r"(sk-|ghp_|github_pat_|xox[baprs]-|AKIA[0-9A-Z]{16})", blob):
        return "mcp.json.example contains a literal credential"
    return None


def _inv_production_boundaries() -> str | None:
    doc = read("patterns/BOUNDARY-BREAKAGE.md")
    missing = [k for k in ("schema", "version", "timeout") if k not in doc.lower()]
    return f"BOUNDARY-BREAKAGE.md does not name: {', '.join(missing)}" if missing else None


def _inv_goal_acceptance_is_explicit() -> str | None:
    template = read(".github/pull_request_template.md")
    return None if "## Verification" in template and "CI result" in template else \
        "pull_request_template.md does not ask what would prove the goal met"


def _inv_autonomous_profile_enforced() -> str | None:
    """autonomous_profile_is_enforced — the five controls are WIRED, not merely written down.

    The profile named them for eight minor versions and nothing in this tree enforced one. A
    control an agent can decline to read is a label; this invariant is what makes the difference
    between the two visible from outside, which is the only place it matters.
    """
    problems = agent_policy_errors() + authority_class_errors() + gate_tool_errors()
    return f"{len(problems)} agent-policy problem(s), first: {problems[0]}" if problems else None


def _inv_host_is_not_a_capability() -> str | None:
    """host_is_not_a_capability — a host task may not be the only place its behaviour exists.

    A task that lives only in an editor's configuration is a capability that vanishes for anyone
    not in that editor — for CI, for a terminal, for a reviewer on another machine — and its
    absence is SILENT, because the task still looks present to whoever configured it.

    THE FIRST VERSION OF THIS CHECK WAS WRONG AND FIRED ON CORRECT TASKS. It demanded every task
    wrap a file in this tree, and refused `git status` — which is as host-independent as anything
    can be. The real failure is not "wraps no file", it is LOGIC THAT EXISTS ONLY HERE: a shell
    pipeline, a chain of commands, an inline script with nowhere else to live. A guard that fires
    on correct code gets silenced, so the rule is the narrow one.
    """
    shell_logic = re.compile(r"&&|\|\||;|\s\|\s|\$\(")
    problems: list[str] = []
    for config in (".zed/tasks.json", ".vscode/tasks.json"):
        if not (ROOT / config).exists():
            continue
        try:
            entries = read_jsonc(config)
        except ValueError:
            # A FILE THAT DOES NOT PARSE IS ALREADY check()'s FINDING, reported first. Raising here
            # takes the whole contract down and hides every other result — the third time this
            # exact shape appeared, which is why it is now a declared rule rather than a habit.
            continue
        for task in (entries.get("tasks", entries) if isinstance(entries, dict) else entries):
            label = str((task or {}).get("label"))
            argv = [str(item) for item in (task or {}).get("args") or []]
            joined = " ".join(argv)
            # A task that only composes other tasks carries no behaviour of its own.
            if not argv and not (task or {}).get("command"):
                continue
            if shell_logic.search(joined):
                problems.append(f"{config}: '{label}' embeds shell logic in the host config, so "
                                "that behaviour exists nowhere a terminal or CI can reach it")
            for item in argv:
                if item.endswith((".py", ".sh", ".mjs")) and "$" not in item and not (ROOT / item).exists():
                    problems.append(f"{config}: '{label}' runs {item}, which is not in this tree")
    return "; ".join(problems[:2]) if problems else None


def _every_row_declares(section: str, fields: tuple[str, ...], absent: str) -> str | None:
    """Every entry of a declared table carries `fields`, or the table is advice wearing a rule.

    ONE FUNCTION, TWO CALLERS, and the shape gate is why. Written separately, the parser table and
    the staleness table produced byte-for-byte identical ASTs — `astshape.py` refused the second
    copy, which is what it is for. Two rosters checked by two identical functions agree only until
    somebody fixes one of them.
    """
    rows = atlas().get(section) or {}
    if not rows:
        return absent
    unowned = [name for name, spec in rows.items()
               if any(not str((spec or {}).get(field) or "").strip() for field in fields)]
    return f"{section} entries missing {' or '.join(fields)}: {unowned}" if unowned else None


def _inv_parsers_refuse_rather_than_guess() -> str | None:
    """parsers_refuse_rather_than_guess — every declared parser rule names what enforces it."""
    return _every_row_declares(
        "parser_discipline", ("enforced_by", "defect"),
        "atlas.yaml declares no parser_discipline, and every rule in it was earned by a break")


def _inv_readings_name_their_cache() -> str | None:
    """readings_name_their_cache — every external reading names its cache AND what defeats it.

    A stale number looks exactly like a failed change, and the cost is paid twice: once re-fixing
    what was already fixed, and once losing trust in the fix that worked.
    """
    return _every_row_declares(
        "staleness_discipline", ("authority", "cached_by"),
        "atlas.yaml declares no staleness_discipline, so a cached reading is diagnosed as a failed "
        "change and fixed a second time")


def _inv_failure_modes_name_their_refusal() -> str | None:
    """failure_modes_name_their_refusal — every recorded mistake names what refuses it now.

    A failure mode with no refusal is a warning, and a warning is a thing you read once. The
    sightings count is the load-bearing field: one is a bug, two is a missing rule and writing
    that rule is part of the fix, three means the evidence was there twice and nothing was done.
    """
    return _every_row_declares(
        "agent_failure_modes", ("shape", "looks_like", "prevented_by"),
        "atlas.yaml records no agent_failure_modes, so the same shape arrives wearing a different "
        "file every time and is rediscovered rather than recognised")


# name -> a callable returning None (satisfied) or a message (violated)
INVARIANT_CHECKS = {
    "no_unbounded_growth": _inv_no_unbounded_growth,
    "immutable_first": _inv_immutable_first,
    "schema_first": _inv_schema_first,
    "explicit_deadlines": _inv_explicit_deadlines,
    "auditable_changes": _inv_auditable_changes,
    "rollback_high_impact": _inv_rollback_high_impact,
    "one_source_of_truth": _inv_one_source_of_truth,
    "atlas_consistency": _inv_atlas_consistency,
    "ide_is_not_enforcement": _inv_ide_is_not_enforcement,
    "durable_artifacts_are_reachable_or_declared": _inv_durable_artifacts_reachable,
    "mcp_is_task_scoped": _inv_mcp_is_task_scoped,
    "independent_verification": _inv_independent_verification,
    "production_boundaries_are_contracts": _inv_production_boundaries,
    "code_blobs_are_bounded": _inv_code_blobs_are_bounded,
    "tool_surfaces_are_bounded": _inv_tool_surfaces_are_bounded,
    "goal_acceptance_is_explicit": _inv_goal_acceptance_is_explicit,
    "ci_enforces_contract": _inv_workflows_run_the_contract,
    "least_privilege": _inv_least_privilege,
    "native_language_tools_are_authoritative": _inv_native_tools_authoritative,
    "warnings_are_classified": _inv_warnings_are_classified,
    "new_violations_cannot_hide_in_baseline": _inv_no_hidden_baseline,
    "model_choice_is_task_scoped": _inv_model_choice_task_scoped,
    "context_is_progressively_disclosed": _inv_context_progressive,
    "task_verification_is_explicit": _inv_task_verification_explicit,
    "polyglot_boundaries_are_contracts": _inv_polyglot_boundaries,
    "autonomous_profile_is_enforced": _inv_autonomous_profile_enforced,
    "host_is_not_a_capability": _inv_host_is_not_a_capability,
    "parsers_refuse_rather_than_guess": _inv_parsers_refuse_rather_than_guess,
    "readings_name_their_cache": _inv_readings_name_their_cache,
    "failure_modes_name_their_refusal": _inv_failure_modes_name_their_refusal,
}

# name -> WHY it cannot be checked by this repository's harness. A declared blind
# spot is a promise to come back, so each says what WOULD check it and where.
# A declared blind spot is a promise to come back, not an exemption — so this table
# is EMPTY at 1.1.0: every one of the 25 was promoted to a real check against this
# repository's own artifacts. It stays because the next invariant added may not be
# checkable on the day it is written, and saying so beats a check that cannot fail.
INVARIANT_DECLARED: dict[str, str] = {}


def invariants() -> tuple[list[str], list[str], list[str]]:
    """(violations, enforced names, declared names) over atlas.yaml/hard_invariants."""
    declared_list = atlas().get("hard_invariants") or []
    violations, enforced, declared = [], [], []
    for name in declared_list:
        if name in INVARIANT_CHECKS:
            enforced.append(name)
            problem = INVARIANT_CHECKS[name]()
            if problem:
                violations.append(f"hard invariant '{name}' VIOLATED: {problem}")
        elif name in INVARIANT_DECLARED:
            declared.append(name)
        else:
            violations.append(f"hard invariant '{name}' is neither checked nor declared — a promise with no owner")
    for name in list(INVARIANT_CHECKS) + list(INVARIANT_DECLARED):
        if name not in declared_list:
            violations.append(f"'{name}' is registered in atlas.py but absent from atlas.yaml/hard_invariants")
    return violations, enforced, declared
