#!/usr/bin/env python3
"""Atlas primitives: the declared rosters, the file readers and the router.

WHY THIS IS SEPARATE (1.3.0). scripts/atlas.py crossed its own MAX_CODE_LINES cap while gaining
machine-readable output, and the answer to a file hitting its cap is to split it by concern, not
to raise the cap on the guard that caught it. The arrows point one way: this module reads
atlas.yaml and the tree and knows nothing about the contract; atlasgen.py generates documents
from it; atlas.py enforces the contract and owns the CLI.
"""
from __future__ import annotations

import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)")
# THE README'S ENTIRE HEADER IS HTML — banner, badges and navigation — and none of it was
# link-checked. The banner file was renamed twice at v2.0.0 and the contract said nothing,
# which is the silent break this repository exists to prevent: a Markdown checker that only
# understands Markdown reports a clean pass over every anchor and image in the page a reader
# sees first.
HTML_LINK_RE = re.compile(r"(?:href|src)=\"([^\"]+)\"")
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
    ".ml", ".mli", ".scala", ".sc", ".swift", ".r", ".slq", ".fs", ".fth", ".4th",
    
}
BLOB_SUFFIXES = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".onnx", ".pt", ".pth", ".safetensors",
    ".zip", ".tar", ".gz", ".7z", ".iso", ".db", ".sqlite", ".sqlite3",
}
# Every file that must carry the contract version verbatim. ONE declaration: `check` asserts it
# and the README's generated facts count it, so "five files" and "six files" cannot both be printed.
VERSION_SITES = ("MODEL.md", "README.md", "ABOUT.md", "SECURITY.md", "docs/VERSIONING.md", "atlas.yaml")
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
    # A quantum result with no shot count, no noise model and no classical baseline is not a
    # measurement — and no source-change gate would notice. The domain gets its own class.
    "quantum_change",
)
# Precedence rules this ROUTER resolves. atlas.yaml declares six; four are resolved by the
# caller (an override, a project manifest, an issue label, the generic fallback) and naming
# them here keeps the difference legible instead of implied. check() asserts this is a subset
# of the declared list, so a typo cannot invent a precedence level.
PRECEDENCE_IMPLEMENTED = ("artifact_extension", "language_directory")
def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def atlas() -> dict:
    data = yaml.safe_load(read("atlas.yaml"))
    if not isinstance(data, dict):
        raise SystemExit("atlas.yaml did not parse to a mapping")
    return data


def duplicate_route_keys() -> list[str]:
    """Extensions declared more than once in atlas.yaml/artifact_routes.

    A PARSER THAT PICKS A WINNER IS WORSE THAN ONE THAT REFUSES. PyYAML keeps the LAST duplicate
    key and reports nothing, so adding `'.fs': forth` beneath `'.fs': fsharp` moved every F# file
    to the Forth pack with no error, no warning and no diff a reviewer would read as a change of
    behaviour. The raw text is the only place the duplicate is still visible.
    """
    seen: dict[str, int] = {}
    inside = False
    for line in read("atlas.yaml").splitlines():
        if line.startswith("artifact_routes:"):
            inside = True
            continue
        if inside:
            if line and not line.startswith((" ", "\t", "#")):
                break
            match = re.match(r"\s+'([^']+)':", line)
            if match:
                key = match.group(1).lower()
                seen[key] = seen.get(key, 0) + 1
    return sorted(key for key, count in seen.items() if count > 1)


def routes() -> dict[str, str]:
    table = atlas().get("artifact_routes")
    if not isinstance(table, dict) or not table:
        raise SystemExit("atlas.yaml/artifact_routes missing or empty")
    return {str(k).lower(): str(v) for k, v in table.items()}


def route_targets() -> list[str]:
    return sorted(set(routes().values()))


def route_with_evidence(path_value: str) -> tuple[str | None, str, str]:
    """(route, the precedence rule that decided it, the evidence for that decision).

    A router that answers only "python" makes an explicit match and a lucky guess look
    identical. The rule NAMES come from atlas.yaml/routing_policy/precedence, so a route
    cannot report a confidence this repository never declared.

    The directory rule applies only to paths INSIDE this repository: an unrelated
    /tmp/x/languages/go/y.txt used to route to go because a distant segment matched.
    """
    declared = [str(p) for p in (atlas().get("routing_policy") or {}).get("precedence") or []]

    def named(rule: str) -> str:
        return rule if rule in declared else f"{rule} (NOT declared in routing_policy.precedence)"

    path = Path(path_value)
    suffix = path.suffix.lower()
    language = routes().get(suffix)
    if language:
        return language, named("artifact_extension"), f"{suffix} in atlas.yaml/artifact_routes"
    try:
        parts = path.resolve().relative_to(ROOT.resolve()).parts
    except ValueError:
        return None, "none", "the path is outside this repository, so no segment of it routes"
    if "languages" in parts:
        i = parts.index("languages")
        for depth in (2, 1):
            candidate = "/".join(parts[i + 1:i + 1 + depth])
            if candidate and (ROOT / "languages" / candidate / "README.md").exists():
                return candidate, named("language_directory"), f"languages/{candidate}/README.md exists"
    return None, "none", f"no routed extension ({suffix or 'none'}) and no language pack in the path"


def route_for(path_value: str) -> str | None:
    return route_with_evidence(path_value)[0]


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
