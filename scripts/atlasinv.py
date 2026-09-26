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
from pathlib import Path

import yaml
from agentpolicy import (
    agent_policy_errors,
    authority_class_errors,
    gate_resolution,
    gate_tool_errors,
)
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
    strict_yaml,
    tracked,
)
from atlasgen import BLOCKS, _begin
from contextcost import entry_cost_errors, footprint, measure
from declcheck import declaration_errors
from nativetools import native_agent_tool_errors
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
    """ci_enforces_contract — CI runs every gate `verify` runs, plus the instruments only CI runs.

    THE DONE SET IS THE ROSTER (3.10.0): this list was typed here, so a gate added to done_set could be
    run by `verify` locally and by nothing on a pull request. Every done_set command must appear in a
    workflow; the extras stay because CI also runs what no local done step does.
    """
    # THIS repository's CI, not any workflow: a reusable one for consumers names the same commands and
    # would satisfy the check while the pull-request workflow ran none of them.
    ci = read(".github/workflows/atlas-ci.yml")
    done = [" ".join(g["argv"]).replace("python ", "", 1) for g in
            ((atlas().get("verification_policy") or {}).get("done_set") or [])]
    missing = [c for c in done + ["agentrun.py", "bench.py", "atlasindex.py"] if c not in ci]
    return (f"atlas-ci.yml does not run: {', '.join(missing)} — verify runs it locally and nothing runs it on a pull request"
            if missing else None if done else "verification_policy/done_set is empty, so CI is held to nothing")


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
        data = strict_yaml(path.read_text(encoding="utf-8"), str(path)) or {}
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
        policy = (strict_yaml(path.read_text(encoding="utf-8"), str(path)) or {}).get("policy") or {}
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
        strict_yaml(read("atlas.yaml"), "atlas.yaml")
        _json.loads(read("config/github-labels.json"))
        _json.loads(read("config/github-controls.json"))
        _json.loads(read(MANIFEST_SCHEMA))
        for language in route_targets():
            path = ROOT / "languages" / language / "tools.yaml"
            if path.exists():
                strict_yaml(path.read_text(encoding="utf-8"), str(path))
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
        data = strict_yaml(wf.read_text(encoding="utf-8"), str(wf)) or {}
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
    problems = agent_policy_errors() + authority_class_errors() + gate_tool_errors() + role_coverage_errors()
    from langbar import linguist_name_errors
    problems += linguist_name_errors()
    problems += yaml_bypass_errors()
    problems += editorconfig_errors()
    problems += bare_sleep_errors()
    problems += duplicate_definition_errors()
    problems += decision_record_errors()
    problems += runtime_entry_errors()
    problems += chat_errors()
    problems += duplicate_prose_errors()
    problems += mechanism_doc_errors()
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
    """parsers_refuse_rather_than_guess — every declared parser rule names what enforces it, and it EXISTS.

    FOUND AT 3.9.0: a row named `atlascore.replace_once`, which lives in safeedit — a presence check
    passed a name nothing defines. Every `module.function` inside the prose is read off the module's
    AST (never imported: a test module's import has side effects) and must be defined at top level.
    """
    missing = _every_row_declares(
        "parser_discipline", ("enforced_by", "defect"),
        "atlas.yaml declares no parser_discipline, and every rule in it was earned by a break")
    dead = [f"{name}: {ref}" for name, spec in (atlas().get("parser_discipline") or {}).items()
            for ref in _script_refs(str((spec or {}).get("enforced_by") or "")) if not _defined(ref)]
    return missing or (f"parser_discipline names an enforcer nothing defines: {dead}" if dead else None)


def _script_refs(text: str) -> list[str]:
    """`module.name` pairs whose module is a script in this tree; a file name (atlas.yaml) is not a ref."""
    stems = {p.stem for p in (ROOT / "scripts").glob("*.py")}
    return [f"{m}.{n}" for m, n in re.findall(r"\b([a-z_]+)\.([A-Za-z_]\w*)\b", text)
            if m in stems and n not in {"py", "yaml", "json", "md", "toml", "txt", "sh"}]


def _defined(ref: str) -> bool:
    import ast  # noqa: PLC0415
    module, _, name = ref.partition(".")
    tree = ast.parse((ROOT / "scripts" / f"{module}.py").read_text(encoding="utf-8"))
    return any(getattr(node, "name", None) == name or name in {getattr(t, "id", None) for t in getattr(node, "targets", [])}
               for node in tree.body)


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
    missing = _every_row_declares(
        "agent_failure_modes", ("shape", "looks_like", "prevented_by"),
        "atlas.yaml records no agent_failure_modes, so the same shape arrives wearing a different "
        "file every time and is rediscovered rather than recognised")
    if missing:
        return missing
    # A LESSON WITH NO ENFORCER DECAYS TO A COMMENT. MEASURED at 2.28.0: `prevented_by` was prose,
    # and one already named `atlascore.replace_once` an hour after it moved to safeedit — nothing
    # noticed, because nothing resolved it. Each accident now lists the guards that refuse it,
    # resolved against the tree, or says `unenforceable` with the reason and what would close it.
    problems = failure_mode_enforcer_errors()
    return f"{len(problems)} failure mode(s) unenforced, first: {problems[0]}" if problems else None


def _minor_distance(then: str, now: str) -> int:
    (a, b), (c, d) = ([int(x) for x in v.split(".")[:2]] for v in (then, now))
    return (c - a) * 100 + (d - b)


def failure_mode_enforcer_errors() -> list[str]:
    from agentpolicy import _resolves  # noqa: PLC0415
    errors: list[str] = []
    for name, spec in (atlas().get("agent_failure_modes") or {}).items():
        spec = spec or {}
        refs = spec.get("enforced_by") or []
        if not refs:
            if not (str(spec.get("unenforceable") or "").strip() and str(spec.get("closed_by") or "").strip()):
                errors.append(f"agent_failure_modes/{name} names no enforcer, and no reason with a closer")
            # INTAKE MUST GRADUATE (3.0.0, /thea): a shape recorded before it could be guarded carries the
            # version it arrived at. Two minor versions later it is guarded, or `intake` is removed and the
            # reason above stands as a standing verdict — a promise to come back is not an exemption.
            seen, now = str(spec.get("intake") or ""), str(atlas().get("version"))
            if seen and _minor_distance(seen, now) >= 2:
                errors.append(f"agent_failure_modes/{name} has sat in intake since {seen} (now {now}): "
                              "guard it, or drop `intake` and keep the reason as a standing verdict")
            continue
        for ref in refs:
            ref = str(ref)
            ok = (ROOT / ref).exists() if ("/" in ref or ref.startswith(".")) else _resolves(ref)
            if not ok:
                errors.append(f"agent_failure_modes/{name} is enforced_by {ref}, which is not in this tree")
    return errors


def _inv_every_bound_declares_its_tier() -> str | None:
    """every_bound_declares_its_tier — hard, bounded or dynamic, declared rather than felt.

    Hard bounds alone have one predictable failure: the wall that cannot move gets worked AROUND.
    A system that never says which of its rules may move, and on what terms, leaves every reader
    to classify their own change — and they classify generously.
    """
    from knowledge import governance_errors  # noqa: PLC0415 — knowledge imports nothing from here
    problems = governance_errors()
    return f"{len(problems)} governance problem(s), first: {problems[0]}" if problems else None


def _inv_dependency_count_is_the_closure() -> str | None:
    """A dependency count is the CLOSURE an install pulls in, never the lines someone typed.

    ADDED AT 2.28.0 on the owner's ask: "1 runtime dependency" was counted from requirements.txt,
    so a dependency that grew forty of its own would still print 1 — a false minimum. Two readings
    must agree: the hash lock (what CI installs; pip refuses anything unpinned) and the metadata of
    what is installed, walked transitively. The walk catches a new upstream requirement BEFORE the
    locked install refuses it, and the lock catches a count typed to look small.
    """
    import importlib.metadata as md  # noqa: PLC0415 — only this check reads installed metadata

    def norm(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name).lower()
    pinned = {norm(p) for p in re.findall(r"^([A-Za-z0-9_.-]+)==", read("scripts/requirements.lock.txt"), re.M)}
    declared = ((atlas().get("context_policy") or {}).get("install_footprint") or {}).get("resolved_closure")
    if declared is None or len(pinned) != int(declared):
        return (f"install_footprint/resolved_closure says {declared} but the hash lock pins {len(pinned)} "
                f"({', '.join(sorted(pinned))}) — the count an install pays is the closure")
    seen: set[str] = set()
    queue = sorted(pinned)
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        try:
            requires = md.requires(name) or []
        except md.PackageNotFoundError:
            if name in pinned:
                return f"{name} is locked but not installed, so its closure cannot be read — install the lock first"
            continue  # required upstream and absent here: still outside the lock, reported below
        queue += [norm(re.split(r"[\s;<>=!~\[(]", r, maxsplit=1)[0]) for r in requires if "extra ==" not in r]
    unpinned = sorted(seen - pinned)
    return f"the installed closure pulls in {len(unpinned)} package(s) the lock does not pin: {', '.join(unpinned)}" if unpinned else None


def _inv_gates_resolve_distinctly() -> str | None:
    """Two gates may resolve to one command in one pack only when gate_alias_groups declares them one tool.

    FOUND AT 2.30.0: race_detection, timeout_tests, authorization_tests and 18 more resolved to the plain
    test runner, so "race_detection passed" was satisfied by running the unit tests — 21 names, one check.
    """
    from agentpolicy import gate_resolution  # noqa: PLC0415
    groups = [set(g) for g in atlas().get("gate_alias_groups") or []]
    clashes = []
    for pack in sorted(route_targets()):
        by: dict[tuple, list[str]] = {}
        for gate in atlas().get("gate_tools") or {}:
            r = gate_resolution(pack, gate)
            if r["state"] == "runnable":
                by.setdefault(tuple(r["argv"]), []).append(gate)
        clashes += [f"{pack}: {', '.join(gs)} all run `{' '.join(argv)}`" for argv, gs in by.items()
                    if len(gs) > 1 and not any(set(gs) <= g for g in groups)]
    return f"{len(clashes)} gate collision(s), first: {clashes[0]}" if clashes else None





def _from_errors(errors, label: str):
    """An invariant that is a list of problems: None when empty, else the count and the first."""
    def check() -> str | None:
        problems = errors()
        return f"{len(problems)} {label} problem(s), first: {problems[0]}" if problems else None
    return check


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
    "every_bound_declares_its_tier": _inv_every_bound_declares_its_tier,
    "dependency_count_is_the_closure": _inv_dependency_count_is_the_closure,
    "gates_resolve_distinctly": _inv_gates_resolve_distinctly,
    "native_agent_tools_are_kept": _from_errors(native_agent_tool_errors, "native-tool"),
    "declarations_are_read": _from_errors(declaration_errors, "unread-declaration"),
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


# --- readme case count: the defect total in prose is checked against both suites -----------
def declared_case_total() -> int:
    """The UNCONDITIONAL case count: the first integer each suite declares as `expected`.

    Read from the assignment's AST rather than by matching text — a regex over source is a
    rendering, and a comment mentioning `expected = 9` would have satisfied it. The optional
    cross-check that runs only where jsonschema is installed is deliberately NOT counted: a figure
    that depends on the reader's machine does not belong in prose.
    """
    import ast as _ast
    total = 0
    for suite in ("atlas_test.py", "agent_test.py"):
        tree = _ast.parse((ROOT / "scripts" / suite).read_text(encoding="utf-8"))
        for node in _ast.walk(tree):
            if (isinstance(node, _ast.Assign) and any(isinstance(t, _ast.Name) and t.id == "expected"
                                                      for t in node.targets)):
                value = node.value.left if isinstance(node.value, _ast.BinOp) else node.value
                if isinstance(value, _ast.Constant) and isinstance(value.value, int):
                    total += value.value
                    break
    return total


# --- one definition per name: a later def silently replaces the earlier ---------------------------
def duplicate_definition_errors() -> list[str]:
    """No module defines the same top-level function or class twice.

    MEASURED at 2.27.0: an edit rebuilt a module from slices with the end before the start and
    duplicated 150 lines; Python keeps the LAST definition, so every test passed over two copies. The
    byte ratchet caught it by luck. ruff's F811 does not, because the first copy was referenced.
    """
    import ast as _ast
    errors: list[str] = []
    for source in sorted([*(ROOT / "scripts").glob("*.py"), *(ROOT / "fuzz").glob("*.py")]):
        try:
            tree = _ast.parse(source.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        seen: dict[str, int] = {}
        for node in tree.body:
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                if node.name in seen:
                    errors.append(f"{source.relative_to(ROOT)}:{node.lineno} defines {node.name} again "
                                  f"(first at line {seen[node.name]}) — the later one silently wins")
                seen.setdefault(node.name, node.lineno)
    return errors


# --- waiting: on a condition through resilience.wait_until, never a bare fixed sleep ----------
def bare_sleep_errors() -> list[str]:
    """No module outside resilience.py calls time.sleep directly.

    Prophylactic at 2.27.0 — zero sightings — and cheap for that reason: a fixed sleep standing in
    for a condition is too long on a fast day, too short on a slow one, and hides which. resilience
    owns every wait, so a bare sleep elsewhere is refused before its first flaky run.
    """
    import ast as _ast
    errors: list[str] = []
    for source in sorted([*(ROOT / "scripts").glob("*.py"), *(ROOT / "fuzz").glob("*.py")]):
        if source.name == "resilience.py":
            continue
        try:
            tree = _ast.parse(source.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in _ast.walk(tree):
            if (isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute)
                    and node.func.attr == "sleep" and isinstance(node.func.value, _ast.Name)
                    and node.func.value.id == "time"):
                errors.append(f"{source.relative_to(ROOT)}:{node.lineno} calls time.sleep — wait on "
                              "a condition with resilience.wait_until instead")
    return errors


# --- editorconfig: the [*] section is ENFORCED, not merely present --------------------------
def editorconfig_errors() -> list[str]:
    """Every tracked text file obeys what .editorconfig's [*] section declares.

    MEASURED at 2.27.0: the contract checked that .editorconfig EXISTED and nothing checked that
    any file obeyed it — 34 tracked files lacked the final newline it requires, and one had
    trailing whitespace from an edit made the same session. A declared control no instrument reads
    is a comment with a file extension. The rules are READ from the file, so editing .editorconfig
    changes what is enforced with no second copy here to update.
    """
    import configparser as _cp
    parser = _cp.ConfigParser(interpolation=None)
    try:
        parser.read_string(read(".editorconfig").replace("root = true", "", 1))
    except _cp.Error as exc:
        return [f".editorconfig does not parse: {exc}"]
    rules = dict(parser["*"]) if parser.has_section("*") else {}
    binary = {".webp", ".png", ".jpg", ".ico", ".gz", ".zip"}
    errors: list[str] = []
    for path in tracked():
        name = path.relative_to(ROOT).as_posix()
        if (not path.is_file() or path.is_symlink() or path.suffix.lower() in binary
                or name.endswith((".bat", ".cmd", ".ps1"))):
            continue  # binary, or a Windows script whose own section declares crlf
        raw = path.read_bytes()
        if not raw:
            continue
        if rules.get("insert_final_newline") == "true" and not raw.endswith(b"\n"):
            errors.append(f"{name} has no final newline, which .editorconfig [*] requires")
        if rules.get("end_of_line") == "lf" and b"\r\n" in raw:
            errors.append(f"{name} has CRLF line endings, which .editorconfig [*] forbids")
        # Markdown is exempt from the whitespace rule BY FORMAT: two trailing spaces are a hard
        # line break there, so stripping them would change the rendered document.
        if (rules.get("trim_trailing_whitespace") == "true" and not name.endswith(".md")
                and any(line != line.rstrip(" \t") for line in raw.decode("utf-8", "replace").split("\n"))):
            errors.append(f"{name} has trailing whitespace, which .editorconfig [*] forbids")
    return errors


# --- yaml bypass: every YAML read goes through atlascore.strict_yaml -----------------------
_YAML_READERS = {"load", "safe_load", "full_load", "unsafe_load", "load_all", "safe_load_all"}


def yaml_bypass_errors() -> list[str]:
    """No module outside atlascore may call a PyYAML loader directly.

    MEASURED at 2.27.0: StrictLoader's docblock said every YAML read went through it, and 11 did
    not — manifest reads in atlas.py, atlasgen.py and packprobe.py among them, so a duplicate key
    in a pack manifest was silently resolved to its LAST value on those paths, which is the exact
    collision the strict loader was written to refuse. They were also uncached, and parsing was
    73% of a check(). One bypass was a correctness hole and a speed regression at once.

    Test harnesses are exempt BY SUFFIX, with the reason: they call the raw loader on purpose to
    BUILD a document the strict one would refuse, and a guard that fired on that would be silenced.
    """
    import ast as _ast
    errors: list[str] = []
    for source in sorted([*(ROOT / "scripts").glob("*.py"), *(ROOT / "fuzz").glob("*.py")]):
        if source.name == "atlascore.py" or source.name.endswith("_test.py"):
            continue
        try:
            tree = _ast.parse(source.read_text(encoding="utf-8"))
        except SyntaxError:
            continue  # a file that does not parse is the compile check's finding, not this one's
        for node in _ast.walk(tree):
            if (isinstance(node, _ast.Call) and isinstance(node.func, _ast.Attribute)
                    and node.func.attr in _YAML_READERS
                    and isinstance(node.func.value, _ast.Name)
                    and node.func.value.id in {"yaml", "_yaml"}):
                errors.append(f"{source.relative_to(ROOT)}:{node.lineno} calls yaml.{node.func.attr} "
                              "directly — it bypasses the duplicate-key refusal AND the parse cache; "
                              "use atlascore.strict_yaml")
    return errors


# --- mechanism docs: moved dev-only at 2.28.0 — it checks THIS repository's own documents ---
def mechanism_doc_errors() -> list[str]:
    """A document that describes a MECHANISM must name what enforces it.

    Measured at 2.25.0: every pattern and systems document named ZERO of the instruments built to
    implement them. They described mechanisms that had since become real and pointed at none of
    them — advice that outlived its own implementation, which reads as guidance and is actually a
    map of where the enforcement used to be missing.

    The roster is derived from atlas.yaml/instruments rather than typed, so an instrument added
    beside these documents widens what counts automatically. `patterns/` and the mechanism pages
    under `systems/` are in scope; an index page is not, because a page whose job is to link
    elsewhere has no mechanism of its own.
    """
    names = set()
    for label, spec in (atlas().get("instruments") or {}).items():
        names.add(str(label).split()[0].rstrip(":"))
        names.add(Path(str((spec or {}).get("script") or "")).stem)
    names |= {"agent_policy", "governance_tiers", "agent_failure_modes", "staleness_discipline",
              "parser_discipline", "retrieval_policy", "data_classes", "knowledge_layers",
              "language_selection", "gate_tools", "tool_claims", "install_footprint",
              "entry_paths", "example_coverage"}
    names.discard("")
    errors: list[str] = []
    # wiki/ joined after its pages turned out to name nothing either — the same shape in a
    # third directory, which is what makes it a rule rather than two incidents.
    for page in (sorted((ROOT / "patterns").glob("*.md"))
                 + sorted((ROOT / "systems").glob("*.md"))
                 + sorted((ROOT / "wiki").glob("*.md"))):
        if page.name == "README.md":
            continue
        body = page.read_text(encoding="utf-8")
        if not any(name in body for name in names):
            errors.append(f"{page.relative_to(ROOT)} describes a mechanism and names no instrument "
                          "or declaration that enforces it — advice that outlived its own "
                          "implementation reads as guidance and is a map of a gap that closed")
    return errors


# --- redundancy: a sentence paid for twice on one entry path ------------------------------------
def duplicate_prose_errors() -> list[str]:
    """No sentence of ten or more words appears twice across the files one entry path makes a reader
    load together, nor twice within one agent entry.

    MEASURED at 2.28.0: the verification-gates table was generated into README.md AND MODEL.md, both
    on the human entry path, so every reader paid for it twice; and MODEL.md carried a hand-written
    runtime roster beside the generated one. The file list is DERIVED from context_policy/entry_paths,
    so a new entry file is covered the moment it is declared.
    """
    import re as _re
    paths = (atlas().get("context_policy") or {}).get("entry_paths") or {}

    def sentences(text: str) -> list[str]:
        text = _re.sub(r"[`*_>#|\[\]()]", " ", _re.sub(r"<!--.*?-->", " ", text, flags=_re.S))
        found = [" ".join(_re.findall(r"[a-z0-9']+", part.lower()))
                 for part in _re.split(r"(?<=[.!?])\s+|\n\s*\n", text)]
        return [f for f in found if len(f.split()) >= 10]
    groups = [list((paths.get("human") or {}).get("files") or [])]
    groups += [[f] for f in (paths.get("agent") or {}).get("alternatives") or []]
    errors: list[str] = []
    for group in groups:
        seen: dict[str, str] = {}
        for name in group:
            if not (ROOT / name).is_file():
                continue
            for sentence in sentences(read(name)):
                if sentence in seen:
                    errors.append(f"{name} repeats a sentence already in {seen[sentence]} on the same entry path "
                                  f"— paid for twice: {sentence[:70]}")
                seen.setdefault(sentence, name)
    return errors


# --- chat: a process with no stop never ends, and the install text is paid in every session ---
def chat_errors() -> list[str]:
    chat = atlas().get("chat") or {}
    errors = [f"chat process {name} has no {field}" for name, spec in (chat.get("processes") or {}).items()
              for field in ("when", "steps", "returns", "stop_when") if not (spec or {}).get(field)]
    size, cap = len(str(chat.get("install", "")).encode()), int(chat.get("install_max_bytes") or 0)
    if not cap or size > cap:
        errors.append(f"chat install text is {size} B against a cap of {cap} B — it is pasted into every "
                      "session, so cut it rather than raise the cap")
    return errors


# --- runtime entry: each adapter's "How it loads" names what the declaration says it loads ---
def runtime_entry_errors() -> list[str]:
    """The table is generated from the declaration; this keeps the adapters' prose agreeing with it."""
    import re as _re
    errors: list[str] = []
    for entry in atlas().get("runtime_entry") or []:
        loads, adapter = str(entry.get("loads")), ROOT / str(entry.get("adapter"))
        if not (ROOT / loads).is_file():
            errors.append(f"runtime_entry {entry.get('runtime')} loads {loads}, which is not in the tree")
        section = _re.search(r"## How it loads\n(.*?)(?=\n## |\Z)", adapter.read_text(encoding="utf-8"), _re.S) \
            if adapter.is_file() else None
        if not section or loads not in section.group(1):
            errors.append(f"{entry.get('adapter')} does not say, under How it loads, that {entry.get('runtime')} "
                          f"loads {loads} — the adapter and the declaration disagree")
    return errors


# --- system-design decision records: structured, sourced, and proven where a proof exists ----
DECISION_FIELDS = ("decides", "options", "axes", "choose_when", "failure_mode", "verified_by", "source")


def decision_record_errors() -> list[str]:
    """Every record in systems/decisions.yaml is complete, internally consistent, and honest.

    Structured so an instrument can check what prose never could: a choose_when naming an option the
    record does not offer, a source that is not a URL, a proof that is not in the tree. An unverified
    source is ALLOWED and must say why — hiding that it was not confirmed is the refused case.
    """
    from knowledge import decision_records  # noqa: PLC0415
    records = decision_records()
    if not records:
        return ["systems/decisions.yaml holds no decision records"]
    errors: list[str] = []
    for name, spec in records.items():
        spec = spec or {}
        errors += [f"decision {name} declares no {f}" for f in DECISION_FIELDS if not spec.get(f)]
        options = set(spec.get("options") or [])
        errors += [f"decision {name} chooses '{o}', which is not one of its options"
                   for o in (spec.get("choose_when") or {}) if o not in options]
        if not str(spec.get("source") or "").startswith("https://"):
            errors.append(f"decision {name} source is not an https URL")
        if spec.get("source_verified") is False and not str(spec.get("uncertain") or "").strip():
            errors.append(f"decision {name} marks its source unverified and does not say why")
        proof = spec.get("proven_by")
        if proof and not (ROOT / str(proof)).is_file():
            errors.append(f"decision {name} is proven_by {proof}, which is not in the tree")
    return errors


# --- ratchet tightening: rewrites THIS repository's declared bounds ---------------------------
# Moved from shipped contextcost at 2.27.0 to pay for `atlas gate`: only a checkout ever
# tightens its own ratchets, and `check --fix` already reached it through _selfcheck().
def tighten_ratchets(write: bool) -> list[str]:
    """Lower every ratchet to what the tree now costs. It can only make a gate STRICTER.

    WHY THIS DIRECTION IS SAFE AND THE OTHER IS NOT. Lowering a budget to the measured value
    cannot let anything through that was passing before — the worst case of getting it wrong is a
    bound that is too tight, which fails loudly on the next change. RAISING one is the opposite:
    it lets through exactly what the gate existed to refuse, and it always needs a person naming
    what earned it. So this never raises, and `--fix` cannot silence a gate.

    It exists because tightening was the single most repeated manual edit in the session that
    built these ratchets: measure, subtract, retype the number, re-run. That is toil, and toil
    next to a gate is what gets the gate removed.
    """
    declared = (atlas().get("context_policy") or {})
    rows: list[tuple[str, int, int, int]] = []
    for name, row in measure().items():
        rows.append((f"entry path '{name}'", row["bytes"], row["budget"], row["slack"]))
    weight = footprint()
    rows.append(("install footprint", weight["bytes"],
                 int((declared.get("install_footprint") or {}).get("module_bytes") or 0),
                 int((declared.get("install_footprint") or {}).get("slack_bytes") or 0)))
    text = read("atlas.yaml")
    changed: list[str] = []
    for label, current, ceiling, slack in rows:
        if not ceiling or ceiling - current <= slack:
            continue
        target = current + slack // 2
        needle = f"budget_bytes: {ceiling}" if "entry path" in label else f"module_bytes: {ceiling}"
        if needle not in text:
            changed.append(f"{label}: cannot locate '{needle}' in atlas.yaml — tighten it by hand")
            continue
        text = text.replace(needle, needle.split(":")[0] + f": {target}", 1)
        changed.append(f"{label}: {ceiling} -> {target} (measured {current})")
    if write and changed:
        (ROOT / "atlas.yaml").write_text(text, encoding="utf-8")
    return changed


# --- role coverage: this repository measured against its own manifests -------------------
# Development-only. A consumer imports `gate_resolution` for ONE pair; the tally below is
# the number this tree reports about itself, and shipping it would put a self-measurement
# in every install.
def role_coverage() -> dict:
    """The triple over every (pack, role) pair — the number this repository reports about itself."""
    gate_for = {str((s or {}).get("role")): g
                for g, s in reversed(list((atlas().get("gate_tools") or {}).items()))}
    gate_for.pop("none", None)
    tally, by_role, gap = dict.fromkeys(("runnable", "absent", "undeclared"), 0), {}, []
    for role, gate in sorted(gate_for.items()):
        counts = dict.fromkeys(tally, 0)
        for route in sorted(route_targets()):
            verdict = gate_resolution(route, gate)
            counts[verdict["state"]] += 1
            if verdict["state"] == "undeclared":
                gap.append(f"{route}.{role}: {verdict['why']}")
        by_role[role] = counts
        tally = {k: tally[k] + counts[k] for k in tally}
    return {"total": sum(tally.values()), "by_role": by_role, "gaps": gap, **tally}


def role_coverage_errors() -> list[str]:
    """A pack that NAMES a tool must say what runs it. `none` is allowed; silence is not.

    THE SHAPE, and it is the one this whole repository is about: an unrunnable gate and a passing
    gate print the same nothing. A pack naming `lib:criterion` with no driver looks covered in the
    manifest and resolves to nothing at the gate, so the benchmark is skipped and the change merges
    with a gate that never ran. Declaring `none` is the honest alternative and always available.
    """
    return [f"{gap} — name the command that drives it in the pack's `runner`, or declare the "
            "role `none`; an unrunnable gate and a passing gate print the same nothing"
            for gap in role_coverage()["gaps"]]
