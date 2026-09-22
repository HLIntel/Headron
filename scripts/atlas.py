"""Atlas router + repository contract.

Design (0.9.7): atlas.yaml is the single source of truth. Every roster below is
read from it, every document section that restates it is generated from it, and
every count the contract resolves is printed, so a clean pass is always legible.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)")
ORPHAN_ROOTS = ("docs", "integrations", "systems", "patterns", "models", "wiki")
EXEMPT = {"README.md", "ABOUT.md", "MODEL.md", "VERSION", "atlas.yaml"}
REQUIRED_WIKI = (
    "wiki/README.md", "wiki/CODE-ROUTING.md", "wiki/BRANCH-WORKTREES.md",
    "wiki/LABELS-TAGS.md", "wiki/LANGUAGE-LANES.md", "wiki/TOOL-ORCHESTRATION.md",
    "wiki/LANGUAGE-OPERATIONS.md",
)
CODE_SUFFIXES = {
    ".py", ".pyi", ".rs", ".go", ".ts", ".tsx", ".c", ".h", ".cpp", ".cc", ".hpp",
    ".zig", ".mojo", ".jl", ".ex", ".exs", ".gleam", ".nim", ".v", ".odin", ".ha",
    ".fut", ".hs", ".lhs", ".fs", ".fsx", ".chpl", ".bqn", ".ua", ".lean", ".carbon",
    ".roc", ".qs", ".cu", ".cuh", ".sql", ".sh", ".bash", ".wat", ".wasm",
}
BLOB_SUFFIXES = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".onnx", ".pt", ".pth", ".safetensors",
    ".zip", ".tar", ".gz", ".7z", ".iso", ".db", ".sqlite", ".sqlite3",
}
MAX_CODE_LINES = 1000
MAX_BLOB_BYTES = 2_000_000
# A manifest that defaults to everything is not a bounded tool surface. The cap is
# set above the largest hand-authored manifest (python/rust default to 4) with room
# for a language that genuinely needs more, and below "all of them".
MAX_DEFAULT_TOOLS = 8
# The six change classes CI must always be able to gate on. Their REQUIRED lists
# live in atlas.yaml/verification_policy/profiles — this is only the roster of
# names that must exist there, so a deleted profile fails loudly.
CHANGE_CLASSES = (
    "source_change", "api_change", "dependency_change",
    "security_sensitive", "concurrency_change", "performance_change",
)
MANIFEST_TOP = ("schema", "language", "authority", "profiles", "policy")
MANIFEST_POLICY = ("default_tools", "optional_tools", "avoid_by_default", "warnings", "blockers")
# Generated blocks: every place a document restates atlas.yaml is written FROM
# atlas.yaml between these markers, and check() fails on drift.
def _begin(name: str) -> str:
    return f"<!-- BEGIN generated: {name} (python scripts/atlas.py index --write) -->"


def _end(name: str) -> str:
    return f"<!-- END generated: {name} -->"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def atlas() -> dict:
    data = yaml.safe_load(read("atlas.yaml"))
    if not isinstance(data, dict):
        raise SystemExit("atlas.yaml did not parse to a mapping")
    return data


def routes() -> dict[str, str]:
    table = atlas().get("artifact_routes")
    if not isinstance(table, dict) or not table:
        raise SystemExit("atlas.yaml/artifact_routes missing or empty")
    return {str(k).lower(): str(v) for k, v in table.items()}


def route_targets() -> list[str]:
    return sorted(set(routes().values()))


def route_for(path_value: str) -> str | None:
    """Precedence per atlas.yaml/routing_policy: extension, then language directory.

    The directory rule applies only to paths INSIDE this repository: an unrelated
    /tmp/x/languages/go/y.txt used to route to go because a distant segment matched.
    """
    path = Path(path_value)
    language = routes().get(path.suffix.lower())
    if language:
        return language
    try:
        parts = path.resolve().relative_to(ROOT.resolve()).parts
    except ValueError:
        return None
    if "languages" in parts:
        i = parts.index("languages")
        for depth in (2, 1):
            candidate = "/".join(parts[i + 1:i + 1 + depth])
            if candidate and (ROOT / "languages" / candidate / "README.md").exists():
                return candidate
    return None


def label_for(language: str) -> str:
    return "lang/" + language.split("/")[-1]


def known_labels() -> set[str]:
    """A malformed catalog must be REPORTED, not raised: the contract's job is to
    name what is wrong, and a traceback names only where it gave up."""
    try:
        data = json.loads(read("config/github-labels.json"))
    except ValueError:
        return set()
    found: set[str] = set()

    def walk(node) -> None:
        if isinstance(node, str):
            found.add(node)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data.get("namespaces", data))
    return found


def tracked() -> list[Path]:
    try:
        raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        return [ROOT / p for p in raw.decode().split("\0") if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def link_target(source: Path, raw: str) -> Path | None:
    raw = raw.strip().strip("<>")
    if not raw or raw.startswith("#") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", raw):
        return None
    raw = raw.split("#", 1)[0].split("?", 1)[0]
    if not raw:
        return None
    target = (source.parent / raw).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        raise ValueError(f"link escapes repository: {rel(source)} -> {raw}")
    return target


def manifest_errors(language: str) -> list[str]:
    path = ROOT / "languages" / language / "tools.yaml"
    name = f"languages/{language}/tools.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"manifest not YAML: {name} ({exc.__class__.__name__})"]
    if not isinstance(data, dict):
        return [f"manifest not a mapping: {name}"]
    out = [f"manifest missing key '{k}': {name}" for k in MANIFEST_TOP if k not in data]
    if str(data.get("language")) != language.split("/")[-1]:
        out.append(f"manifest identity mismatch: {name} language={data.get('language')!r}")
    policy = data.get("policy")
    if isinstance(policy, dict):
        out += [f"manifest policy missing '{k}': {name}" for k in MANIFEST_POLICY if k not in policy]
    for key in ("authority", "profiles"):
        if key in data and not (isinstance(data[key], dict) and data[key]):
            out.append(f"manifest '{key}' must be a non-empty mapping: {name}")
    return out


def language_index_block() -> str:
    rows = ["| route | guide | operating card | tool manifest |", "|---|---|---|---|"]
    # An umbrella pack (quantum/) has no extension of its own but owns routed children;
    # it is indexed beside them so the guide-reachability check sees it.
    umbrellas = sorted({t.rsplit("/", 1)[0] for t in route_targets() if "/" in t})
    for language in umbrellas + route_targets():
        base = ROOT / "languages" / language
        card = f"[card]({language}/OPERATING.md)" if (base / "OPERATING.md").exists() else "missing"
        manifest = f"[tools.yaml]({language}/tools.yaml)" if (base / "tools.yaml").exists() else "none"
        rows.append(f"| `{language}` | [guide]({language}/README.md) | {card} | {manifest} |")
    present = sum((ROOT / "languages" / lang / "tools.yaml").exists() for lang in route_targets())
    return (f"Derived from `atlas.yaml/artifact_routes` — {len(route_targets())} routes, "
            f"{present} tool manifests.\n\n" + "\n".join(rows))


def precedence_block() -> str:
    items = (atlas().get("routing_policy") or {}).get("precedence") or []
    return "```text\n" + "\n    -> ".join(str(i) for i in items) + "\n```"


def gates_block() -> str:
    profiles = (atlas().get("verification_policy") or {}).get("profiles") or {}
    width = max((len(k) for k in profiles), default=10)
    lines = [f"{k.ljust(width)} -> " + " + ".join(str(g) for g in (v or {}).get("required", []))
             for k, v in profiles.items()]
    return "```text\n" + "\n".join(lines) + "\n```"


def lanes_block() -> str:
    pattern = str((atlas().get("branch_policy") or {}).get("language_lane_pattern", "lang/<language>/<topic>"))
    rows = ["| Route | Label | Branch namespace |", "|---|---|---|"]
    for language in route_targets():
        lane = pattern.replace("<language>", language).replace("<topic>", "*")
        rows.append(f"| `{language}` | `{label_for(language)}` | `{lane}` |")
    return "Derived from `atlas.yaml/artifact_routes` + `branch_policy.language_lane_pattern`.\n\n" + "\n".join(rows)


# name -> (files that carry the block, generator). check() asserts every one.
BLOCKS: dict[str, tuple[tuple[str, ...], object]] = {
    "language-index": (("languages/README.md",), language_index_block),
    "routing-precedence": (("wiki/CODE-ROUTING.md",), precedence_block),
    "verification-gates": (("README.md", "MODEL.md"), gates_block),
    "language-lanes": (("wiki/LANGUAGE-LANES.md",), lanes_block),
}


def rendered(name: str) -> str:
    return f"{_begin(name)}\n{BLOCKS[name][1]()}\n{_end(name)}"


def index(write: bool) -> int:
    """Regenerate every registered block. Markers must already exist in the file."""
    missing = 0
    for name, (files, _) in BLOCKS.items():
        block = rendered(name)
        for rel_path in files:
            path = ROOT / rel_path
            text = path.read_text(encoding="utf-8")
            if _begin(name) not in text or _end(name) not in text:
                print(f"markers missing for {name} in {rel_path}")
                missing += 1
                continue
            pre, rest = text.split(_begin(name), 1)
            _, post = rest.split(_end(name), 1)
            new = pre + block + post
            if write and new != text:
                path.write_text(new, encoding="utf-8")
                print(f"wrote {name} -> {rel_path}")
            elif not write:
                print(f"--- {name} -> {rel_path}\n{block}")
    print(f"generated blocks: {len(BLOCKS)} ({sum(len(f) for f, _ in BLOCKS.values())} sites), {missing} missing markers")
    return 1 if missing else 0


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
    missing = [c for c in ("atlas.py check", "atlas_test.py") if c not in ci]
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
    policy = atlas().get("context_policy") or {}
    if not policy.get("forbidden_default"):
        return "context_policy.forbidden_default is empty — nothing is excluded by default"
    return None


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


def check() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    version = read("VERSION").strip()

    if not LINK_RE.search("[self](self.md)"):
        errors.append("Markdown link parser self-test failed")

    for path in ("MODEL.md", "README.md", "ABOUT.md", "docs/VERSIONING.md"):
        if version not in read(path):
            errors.append(f"version mismatch: {path} != {version}")
    if str(atlas().get("version")) != version:
        errors.append(f"version mismatch: atlas.yaml {atlas().get('version')} != {version}")

    required = [
        "MODEL.md", "README.md", "VERSION", "atlas.yaml", "docs/INDEX.md", "docs/LANGUAGE-SPEC.md",
        "docs/GITHUB-FINALIZATION.md", "languages/ATLAS.md", "models/README.md", "models/vscode/README.md",
        "integrations/VS-CODE.md", "integrations/MCP-LANGUAGE-MATRIX.md", "integrations/MCP-PROFILES.md",
        "systems/POLYGLOT-ENGINEERING.md", "systems/AGENT-HARNESS.md", "patterns/ANTI-DRIFT.md",
        "patterns/ANTI-ORPHANS.md", "patterns/ANTI-MUTATION.md", "patterns/BOUNDARY-BREAKAGE.md",
        "patterns/ANTI-BLOBS.md", ".github/copilot-instructions.md", ".github/dependabot.yml",
        ".github/workflows/dependency-review.yml", ".github/workflows/scorecard.yml",
        ".github/pull_request_template.md", ".github/CODEOWNERS", "SECURITY.md", "config/github-labels.json",
        ".editorconfig", ".gitattributes", ".gitignore", ".github/workflows/atlas-ci.yml", "tools/README.md",
        "scripts/requirements.txt", "scripts/atlas_test.py", ".devcontainer/devcontainer.json", ".devcontainer/README.md",
        *REQUIRED_WIKI,
    ]
    for path in required:
        if not (ROOT / path).exists():
            errors.append(f"missing required path: {path}")

    if (ROOT / "AGENTS.md").exists():
        errors.append("stale root AGENTS.md exists; MODEL.md is canonical")

    aliases = [
        "docs/MODEL.md", "docs/PYTHON.md", "docs/RUST.md", "docs/GO.md", "docs/TYPESCRIPT.md",
        "models/agents/CANONICAL-MODEL.md",
    ]
    for alias in aliases:
        path = ROOT / alias
        if not path.is_symlink():
            errors.append(f"expected symlink: {alias}")
        elif not (path.parent / path.readlink()).exists():
            errors.append(f"broken symlink: {alias} -> {path.readlink()}")

    try:
        json.loads(read("config/github-labels.json"))
    except ValueError as exc:
        errors.append(f"config/github-labels.json does not parse: {exc}")

    route_map = routes()
    for suffix in (".py", ".rs", ".go", ".ts", ".ha", ".fut", ".carbon", ".roc", ".qs", ".sql", ".cu", ".lean"):
        if suffix not in route_map:
            errors.append(f"artifact route missing: {suffix}")
    targets = route_targets()
    labels = known_labels()
    manifests_present = cards_present = labelled = 0
    for target in targets:
        base = ROOT / "languages" / target
        if not (base / "README.md").exists():
            errors.append(f"route target missing: {target}")
        if (base / "OPERATING.md").exists():
            cards_present += 1
        else:
            errors.append(f"operating card missing: languages/{target}/OPERATING.md")
        if (base / "tools.yaml").exists():
            manifests_present += 1
            errors += manifest_errors(target)
        else:
            warnings.append(f"tool manifest missing (generic policy applies): languages/{target}/tools.yaml")
        if label_for(target) in labels:
            labelled += 1
        else:
            errors.append(f"route label not in config/github-labels.json: {label_for(target)}")

    model = read("MODEL.md")
    for adapter in re.findall(r"models/[A-Za-z0-9_-]+/README\.md", model):
        if not (ROOT / adapter).exists():
            errors.append(f"model adapter missing: {adapter}")

    profiles = (atlas().get("verification_policy") or {}).get("profiles") or {}
    for cls in CHANGE_CLASSES:
        req = (profiles.get(cls) or {}).get("required") if isinstance(profiles.get(cls), dict) else None
        if not isinstance(req, list) or not req:
            errors.append(f"verification_policy.profiles.{cls}.required missing or empty in atlas.yaml")
    task_profiles = atlas().get("task_profiles") or {}
    if not isinstance(task_profiles, dict) or "default" not in task_profiles:
        errors.append("atlas.yaml/task_profiles missing or has no 'default'")

    inbound: dict[str, list[str]] = {}
    links_checked = 0
    for source in tracked():
        if source.suffix.lower() != ".md" or source.is_symlink():
            continue
        try:
            content = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"non-UTF-8 markdown: {rel(source)}")
            continue
        for match in LINK_RE.finditer(content):
            raw = match.group(1) or match.group(2) or ""
            try:
                target = link_target(source, raw)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if target is None:
                continue
            links_checked += 1
            key = rel(target)
            inbound.setdefault(key, []).append(rel(source))
            if target.is_dir():  # a link to a directory reaches its README
                inbound.setdefault(key + "/README.md", []).append(rel(source))
            if not target.exists():
                errors.append(f"broken local link: {rel(source)} -> {raw}")

    blocks_ok = 0
    for name, (files, _) in BLOCKS.items():
        block = rendered(name)
        for rel_path in files:
            if block in read(rel_path):
                blocks_ok += 1
            else:
                errors.append(f"generated block '{name}' drifted or missing in {rel_path}: run `python scripts/atlas.py index --write`")

    guides_total = guides_indexed = 0
    for guide in (ROOT / "languages").rglob("README.md"):
        guide_rel = rel(guide)
        if guide_rel == "languages/README.md":
            continue
        guides_total += 1
        if guide_rel in inbound:
            guides_indexed += 1
        else:
            errors.append(f"unindexed language guide: {guide_rel}")

    for root_name in ORPHAN_ROOTS:
        for path in (ROOT / root_name).rglob("*.md"):
            path_rel = rel(path)
            if path.is_symlink() or path.name == "README.md" or path_rel in EXEMPT:
                continue
            if path_rel not in inbound:
                errors.append(f"orphaned durable document: {path_rel}")

    for workflow in (ROOT / ".github" / "workflows").glob("*.y*ml"):
        content = workflow.read_text(encoding="utf-8")
        if "permissions:" not in content:
            errors.append(f"workflow missing permissions: {rel(workflow)}")
        if "concurrency:" not in content:
            errors.append(f"workflow missing concurrency: {rel(workflow)}")
        if "pull_request_target:" in content:
            errors.append(f"privileged trigger requires review: {rel(workflow)}")

    for path in tracked():
        if path.name.startswith(".env") and path.name != ".env.example":
            errors.append(f"tracked environment/secret file: {rel(path)}")
        suffix = path.suffix.lower()
        if suffix in CODE_SUFFIXES and path.is_file():
            try:
                with path.open("r", encoding="utf-8") as handle:
                    line_count = sum(1 for _ in handle)
                if line_count > MAX_CODE_LINES:
                    warnings.append(f"large code file: {rel(path)} ({line_count} lines > {MAX_CODE_LINES})")
            except (OSError, UnicodeDecodeError) as exc:
                warnings.append(f"unreadable code file: {rel(path)} ({exc.__class__.__name__})")
        if suffix in BLOB_SUFFIXES and path.is_file():
            size = path.stat().st_size
            if size > MAX_BLOB_BYTES:
                warnings.append(f"large binary/blob artifact: {rel(path)} ({size} bytes > {MAX_BLOB_BYTES})")

    inv_violations, inv_enforced, inv_declared = invariants()
    errors += inv_violations

    counts = (f"links {links_checked} | routes {len(targets)} | guides {guides_indexed}/{guides_total} | "
              f"cards {cards_present}/{len(targets)} | manifests {manifests_present}/{len(targets)} | "
              f"labels {labelled}/{len(targets)} | generated blocks {blocks_ok}/{sum(len(f) for f, _ in BLOCKS.values())} | "
              f"invariants {len(inv_enforced)} enforced + {len(inv_declared)} declared"
              f"/{len(atlas().get('hard_invariants') or [])} | warnings {len(set(warnings))}")
    if errors:
        print(f"Code-Development contract {version}: FAIL ({len(set(errors))} errors)")
        print("\n".join(f"- {e}" for e in sorted(set(errors))))
        print(counts)
        return 1
    print(f"Code-Development contract {version}: OK")
    print(counts)
    if warnings:
        print("warnings (non-blocking):")
        print("\n".join(f"- {w}" for w in sorted(set(warnings))))
    return 0


def route(path_value: str) -> int:
    language = route_for(path_value)
    if not language:
        print(f"no Atlas route for {path_value} (not a routed extension and not under languages/)")
        return 2
    base = ROOT / "languages" / language
    manifest = f"languages/{language}/tools.yaml"
    if not (base / "tools.yaml").exists():
        manifest += " (MISSING — generic tool policy applies; see tools/README.md)"
    print(f"language/domain: {language}")
    print(f"guide: languages/{language}/README.md")
    print(f"operating card: languages/{language}/OPERATING.md")
    print(f"tool manifest: {manifest}")
    print("native authority: language guide + native compiler/LSP/debugger/test/profiler")
    print("runtime: models/vscode/README.md")
    print("mcp: integrations/MCP-LANGUAGE-MATRIX.md -> use only the justified profile")
    print("operations: wiki/LANGUAGE-OPERATIONS.md")
    print(f"issue label: {label_for(language)}")
    print(f"branch lane: lang/{language}/<topic> (temporary; merge to main)")
    print(f"worktree: ../Code-Development-wt/{language.replace('/', '-')}-<topic>")
    print("verify: docs/VERIFY.md")
    return 0


def plan(path_value: str, task: str, change: str | None) -> int:
    language = route_for(path_value)
    if not language:
        print(f"no Atlas route for {path_value}")
        return 2
    profiles = atlas().get("task_profiles") or {}
    if task not in profiles:
        print(f"unknown task profile: {task}")
        print("available: " + ", ".join(profiles))
        return 2
    print(f"language/domain: {language}")
    print(f"guide: languages/{language}/README.md")
    print(f"operating card: languages/{language}/OPERATING.md")
    print(f"tool manifest: languages/{language}/tools.yaml")
    print(f"task: {task}")
    print("tools:")
    for tool in profiles[task]:
        print(f"- {tool}")
    gates = ((atlas().get("verification_policy") or {}).get("profiles") or {})
    if change:
        req = (gates.get(change) or {}).get("required") or []
        print(f"required gates ({change}):")
        for gate in req:
            print(f"- {gate}")
    else:
        print("required gates: pass --change <" + "|".join(gates) + ">")
    tiers = ((atlas().get("verification_policy") or {}).get("tiers") or {})
    print("verification tiers: " + " -> ".join(tiers) if tiers else "verification tiers: none declared in atlas.yaml")
    print("verification: docs/VERIFY.md + applicable native language checks")
    print("branch/worktree: wiki/BRANCH-WORKTREES.md")
    return 0


def learn(language: str) -> int:
    """Turn an operating card into the seven-pass mastery loop (research/LANGUAGE-MASTERY.md)."""
    target = language if (ROOT / "languages" / language / "OPERATING.md").exists() else route_for(language)
    if not target or not (ROOT / "languages" / target / "OPERATING.md").exists():
        print(f"no operating card for {language}")
        return 2
    card = read(f"languages/{target}/OPERATING.md")
    def field(name: str) -> str:
        m = re.search(rf"\*\*{name}:\*\*\s*(.+)", card)
        return m.group(1).strip() if m else "(not on the card)"
    manifest_path = ROOT / "languages" / target / "tools.yaml"
    tools = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    auth = tools.get("authority", {})
    verify = (tools.get("provenance") or {}).get("verify") or []
    print(f"language: {target}")
    print(f"card: languages/{target}/OPERATING.md")
    print(f"fast path: {field('Fast path')}")
    print(f"native authority: {field('Native authority')}")
    print(f"research: {field('Research')}")
    print("mastery loop (one pass each, record the lesson at the end):")
    steps = [
        ("read reference", f"docs {auth.get('docs', '(none)')}"),
        ("trace real code", f"research {auth.get('research', '(none)')}"),
        ("reproduce a tiny example", f"run with {auth.get('compiler_or_runtime', '(none)')}"),
        ("modify it", f"format with {auth.get('formatter', 'none')}; language server {auth.get('lsp', 'none')}"),
        ("break it on purpose", f"tests {auth.get('test', 'none')}; fuzz {auth.get('fuzz', 'none')}"),
        ("verify", f"security {auth.get('security', 'none')}; debugger {auth.get('debugger', 'none')}"),
        ("benchmark", f"profiler {auth.get('profiler', 'none')}"),
        ("record the lesson", "one fact per note; a measured number beats a summary"),
    ]
    for i, (step, how) in enumerate(steps, 1):
        print(f"  {i}. {step}: {how}")
    if verify:
        print("confirm before relying on: " + ", ".join(verify))
    print(f"avoid: {field('Avoid')}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="atlas.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("invariants")
    index_parser = sub.add_parser("index")
    index_parser.add_argument("--write", action="store_true")
    learn_parser = sub.add_parser("learn")
    learn_parser.add_argument("language", help="a route (python, quantum/qsharp) or a file to route")
    route_parser = sub.add_parser("route")
    route_parser.add_argument("path")
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("path")
    plan_parser.add_argument("--task", default="default", help="a key of atlas.yaml/task_profiles")
    plan_parser.add_argument("--change", default=None, help="a key of atlas.yaml/verification_policy/profiles")
    args = parser.parse_args(argv)
    if args.command == "check":
        return check()
    if args.command == "invariants":
        violations, enforced, declared = invariants()
        for name in enforced:
            problem = INVARIANT_CHECKS[name]()
            print(f"ENFORCED  {name}" + (f"  -> VIOLATED: {problem}" if problem else ""))
        for name in declared:
            print(f"DECLARED  {name}: {INVARIANT_DECLARED[name]}")
        print(f"{len(enforced)} enforced, {len(declared)} declared, {len(violations)} unowned or violated")
        return 1 if violations else 0
    if args.command == "index":
        return index(args.write)
    if args.command == "learn":
        return learn(args.language)
    if args.command == "route":
        return route(args.path)
    return plan(args.path, args.task, args.change)


if __name__ == "__main__":
    raise SystemExit(main())
