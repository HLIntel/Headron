from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE_RE = re.compile(r"^  '([^']+)': ([a-z0-9_]+)$", re.MULTILINE)
LINK_RE = re.compile(r"!?\\[[^\\]]*\\]\\((?:<([^>]+)>|([^\\s)]+))(?:\\s+[^)]*)?\\)")
ORPHAN_ROOTS = ("docs", "integrations", "systems", "patterns", "models")
EXEMPT = {"README.md", "ABOUT.md", "MODEL.md", "VERSION", "atlas.yaml"}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def tracked() -> list[Path]:
    try:
        raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        return [ROOT / p for p in raw.decode().split("\\0") if p]
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
    version = read("VERSION").strip()

    for path in ("MODEL.md", "README.md", "ABOUT.md", "docs/VERSIONING.md", "atlas.yaml"):
        if version not in read(path):
            errors.append(f"version mismatch: {path} != {version}")

    required = [
        "MODEL.md", "README.md", "VERSION", "atlas.yaml", "docs/INDEX.md",
        "docs/LANGUAGE-SPEC.md", "languages/ATLAS.md", "models/README.md",
        "models/vscode/README.md", "integrations/VS-CODE.md",
        "systems/POLYGLOT-ENGINEERING.md", "systems/AGENT-HARNESS.md",
        "patterns/ANTI-DRIFT.md", "patterns/ANTI-ORPHANS.md",
        ".editorconfig", ".gitattributes", ".gitignore",
        ".github/workflows/atlas-ci.yml",
    ]
    for path in required:
        if not (ROOT / path).exists():
            errors.append(f"missing required path: {path}")

    if (ROOT / "AGENTS.md").exists():
        errors.append("stale root AGENTS.md exists; MODEL.md is canonical")

    aliases = [
        "docs/MODEL.md", "docs/PYTHON.md", "docs/RUST.md",
        "docs/GO.md", "docs/TYPESCRIPT.md", "models/agents/CANONICAL-MODEL.md",
    ]
    for alias in aliases:
        path = ROOT / alias
        if not path.is_symlink():
            errors.append(f"expected symlink: {alias}")
        elif not (path.parent / path.readlink()).exists():
            errors.append(f"broken symlink: {alias} -> {path.readlink()}")

    route_map = routes()
    for suffix in (".py", ".rs", ".go", ".ts", ".sql", ".cu", ".lean"):
        if suffix not in route_map:
            errors.append(f"artifact route missing: {suffix}")
    for language in set(route_map.values()):
        if not (ROOT / "languages" / language / "README.md").exists():
            errors.append(f"route target missing: {language}")

    model = read("MODEL.md")
    for adapter in re.findall(r"models/[A-Za-z0-9_-]+/README\\.md", model):
        if not (ROOT / adapter).exists():
            errors.append(f"model adapter missing: {adapter}")

    inbound: dict[str, list[str]] = {}
    for source in tracked():
        if source.suffix.lower() != ".md":
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
                errors.append(f"broken local link: {rel(source)} -> {raw}")

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

    workflows = ROOT / ".github" / "workflows"
    for workflow in workflows.glob("*.y*ml"):
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

    try:
        whitespace = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True)
        if whitespace.returncode:
            errors.append("git diff --check reports whitespace errors")
    except FileNotFoundError:
        pass

    if errors:
        print(f"Code-Development contract {version}: FAIL")
        print("\\n".join(f"- {e}" for e in sorted(set(errors))))
        return 1

    print(f"Code-Development contract {version}: OK")
    print("links: OK | routes: OK | adapters: OK | language guides: OK | orphans: none")
    return 0


def route(path_value: str) -> int:
    suffix = Path(path_value).suffix.lower()
    language = routes().get(suffix)
    if not language:
        print(f"no Atlas route for {path_value}")
        return 2
    print(f"language: {language}")
    print(f"guide: languages/{language}/README.md")
    print("runtime: models/vscode/README.md")
    print("verify: docs/VERIFY.md")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="atlas.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    route_parser = sub.add_parser("route")
    route_parser.add_argument("path")
    args = parser.parse_args(argv)
    return check() if args.command == "check" else route(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
