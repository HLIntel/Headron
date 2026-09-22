from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE_RE = re.compile(r"^  '([^']+)': ([a-z0-9_/-]+)$", re.MULTILINE)
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

TASK_REQUIREMENTS = {
    "source_change": ["formatter", "compiler_or_typechecker", "unit_tests"],
    "api_change": ["schema_validation", "contract_tests", "endpoint_tests", "compatibility_check"],
    "dependency_change": ["dependency_graph", "dependency_review", "vulnerability_scan", "tests"],
    "security_sensitive": ["codeql", "secret_scan", "static_analysis", "tests"],
    "concurrency_change": ["race_detection", "cancellation_tests", "timeout_tests", "stress_test"],
    "performance_change": ["benchmark", "profiler", "representative_workload", "regression_threshold"],
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def tracked() -> list[Path]:
    try:
        raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        return [ROOT / p for p in raw.decode().split("\0") if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def routes() -> dict[str, str]:
    return {ext: lang for ext, lang in ROUTE_RE.findall(read("atlas.yaml"))}


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


def check() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    version = read("VERSION").strip()

    if not LINK_RE.search("[self](self.md)"):
        errors.append("Markdown link parser self-test failed")

    for path in ("MODEL.md", "README.md", "ABOUT.md", "docs/VERSIONING.md", "atlas.yaml"):
        if version not in read(path):
            errors.append(f"version mismatch: {path} != {version}")

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

    route_map = routes()
    for suffix in (".py", ".rs", ".go", ".ts", ".ha", ".fut", ".carbon", ".roc", ".qs", ".sql", ".cu", ".lean"):
        if suffix not in route_map:
            errors.append(f"artifact route missing: {suffix}")
    for target in set(route_map.values()):
        guide = ROOT / "languages" / Path(target) / "README.md"
        manifest = ROOT / "languages" / Path(target) / "tools.yaml"
        if not guide.exists():
            errors.append(f"route target missing: {target}")
        if not manifest.exists():
            errors.append(f"tool manifest missing: languages/{target}/tools.yaml")
        elif f"language: {target.split('/')[-1]}" not in manifest.read_text(encoding="utf-8"):
            warnings.append(f"manifest identity requires review: languages/{target}/tools.yaml")

    model = read("MODEL.md")
    for adapter in re.findall(r"models/[A-Za-z0-9_-]+/README\.md", model):
        if not (ROOT / adapter).exists():
            errors.append(f"model adapter missing: {adapter}")

    atlas = read("atlas.yaml")
    for profile, requirements in TASK_REQUIREMENTS.items():
        for requirement in requirements:
            if requirement not in atlas:
                errors.append(f"verification requirement missing from atlas: {profile}/{requirement}")

    inbound: dict[str, list[str]] = {}
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
            key = rel(target)
            inbound.setdefault(key, []).append(rel(source))
            if not target.exists():
                errors.append(f"broken local link: {rel(source)} -> {raw} (resolved={target}; exists={target.exists()})")

    language_root = ROOT / "languages"
    for guide in language_root.rglob("README.md"):
        guide_rel = rel(guide)
        if guide_rel != "languages/README.md" and guide_rel not in inbound:
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
            except (OSError, UnicodeDecodeError):
                pass
        if suffix in BLOB_SUFFIXES and path.is_file():
            try:
                size = path.stat().st_size
                if size > MAX_BLOB_BYTES:
                    warnings.append(f"large binary/blob artifact: {rel(path)} ({size} bytes > {MAX_BLOB_BYTES})")
            except OSError:
                pass

    if errors:
        print(f"Code-Development contract {version}: FAIL")
        print("\n".join(f"- {e}" for e in sorted(set(errors))))
        return 1
    print(f"Code-Development contract {version}: OK")
    print("links: OK | routes: OK | manifests: OK | adapters: OK | language guides: OK | orphans: none")
    if warnings:
        print("warnings (non-blocking):")
        print("\n".join(f"- {w}" for w in sorted(set(warnings))))
    return 0


def route(path_value: str) -> int:
    suffix = Path(path_value).suffix.lower()
    language = routes().get(suffix)
    if not language:
        print(f"no Atlas route for {path_value}")
        return 2
    print(f"language/domain: {language}")
    print(f"guide: languages/{language}/README.md")
    print(f"tool manifest: languages/{language}/tools.yaml")
    print("native authority: language guide + native compiler/LSP/debugger/test/profiler")
    print("runtime: models/vscode/README.md")
    print("mcp: integrations/MCP-LANGUAGE-MATRIX.md -> use only the justified profile")
    print("operations: wiki/LANGUAGE-OPERATIONS.md")
    print(f"issue label: lang/{language}")
    print(f"branch lane: lang/{language}/<topic> (temporary; merge to main)")
    print(f"worktree: ../Code-Development-wt/{language}-<topic>")
    print("verify: docs/VERIFY.md")
    return 0


def plan(path_value: str, task: str) -> int:
    suffix = Path(path_value).suffix.lower()
    language = routes().get(suffix)
    if not language:
        print(f"no Atlas route for {path_value}")
        return 2
    profiles = {
        "default": ["native", "focused_context", "focused_verify"],
        "implementation": ["native", "semantic_context", "tests", "diff_review"],
        "debugging": ["native_debugger", "focused_repro", "regression_test", "diff_review"],
        "endpoint": ["native_http", "schema_contract", "integration_test", "browser_if_needed"],
        "database": ["native_db", "dbhub_read_only", "migration_test", "plan_review"],
        "security": ["native_security", "codeql", "semgrep", "secret_scan", "dependency_review"],
        "reliability": ["timeouts", "cancellation", "health_readiness", "telemetry", "smoke_test"],
        "mutation": ["existing_tests", "mutation_tool_if_mature", "bounded_mutants", "regression_gate"],
        "performance": ["profiler", "benchmark", "representative_workload", "regression_threshold"],
        "polyglot": ["schema_or_abi", "native_tools_both_sides", "boundary_test", "e2e_if_needed"],
        "research": ["primary_sources", "isolated_context", "prototype", "measurement"],
    }
    if task not in profiles:
        print(f"unknown task profile: {task}")
        print("available: " + ", ".join(profiles))
        return 2
    print(f"language/domain: {language}")
    print(f"guide: languages/{language}/README.md")
    print(f"tool manifest: languages/{language}/tools.yaml")
    print(f"task: {task}")
    print("tools:")
    for tool in profiles[task]:
        print(f"- {tool}")
    print("verification tiers: fast -> standard -> deep -> release")
    print("task-level required gates are defined in atlas.yaml/verification_policy/profiles")
    print("verification: docs/VERIFY.md + applicable native language checks")
    print("branch/worktree: wiki/BRANCH-WORKTREES.md")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="atlas.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    route_parser = sub.add_parser("route")
    route_parser.add_argument("path")
    plan_parser = sub.add_parser("plan")
    plan_parser.add_argument("path")
    plan_parser.add_argument("--task", choices=[
        "default", "implementation", "debugging", "endpoint", "database", "security",
        "reliability", "mutation", "performance", "polyglot", "research",
    ], default="default")
    args = parser.parse_args(argv)
    if args.command == "check":
        return check()
    if args.command == "route":
        return route(args.path)
    return plan(args.path, args.task)


if __name__ == "__main__":
    raise SystemExit(main())
