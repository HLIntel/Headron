#!/usr/bin/env python3
"""Atlas primitives: the declared rosters, the file readers and the router.

WHY THIS IS SEPARATE (1.3.0). scripts/atlas.py crossed its own MAX_CODE_LINES cap while gaining
machine-readable output, and the answer to a file hitting its cap is to split it by concern, not
to raise the cap on the guard that caught it. The arrows point one way: this module reads
atlas.yaml and the tree and knows nothing about the contract; atlasgen.py generates documents
from it; atlas.py enforces the contract and owns the CLI.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import yaml

# ROOT, resolved for the three ways this code runs.
#
# Normally it is the repository above this file. Two other cases are real and both were found by
# trying: a FROZEN build (ClusterFuzzLite compiles the fuzz target with PyInstaller, where
# __file__ points into a temporary extraction directory and the data files travel in the bundle),
# and a VENDORED copy where the caller says where the tree is. Neither is a special case for a
# scanner's benefit — both are "do not assume you are standing in a git checkout", which is the
# same assumption that made the harness unusable outside one directory before check_contract.py.
ROOT = Path(
    os.environ.get("CODE_DEVELOPMENT_ROOT")
    or getattr(sys, "_MEIPASS", None)
    or Path(__file__).resolve().parents[1]
)
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
    ".ml", ".mli", ".scala", ".sc", ".swift", ".r", ".slq", ".fth", ".4th",
}
BLOB_SUFFIXES = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".onnx", ".pt", ".pth", ".safetensors",
    ".zip", ".tar", ".gz", ".7z", ".iso", ".db", ".sqlite", ".sqlite3",
}
# Every file that must carry the contract version verbatim. ONE declaration: `check` asserts it
# and the README's generated facts count it, so "five files" and "six files" cannot both be printed.
# Every file that must carry the contract version verbatim. The consumer pin joined after sitting
# fourteen minor versions stale — a worked example that teaches a stale pin is copied.
VERSION_SITES = ("MODEL.md", "README.md", "ABOUT.md", "SECURITY.md", "docs/VERSIONING.md",
                 "atlas.yaml", ".atlas.yaml")
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
    # Retrieval has failures no source-change gate can see: a chunk that ends mid-function, an
    # index invalidated by a modification time, an answer with no citation. All three pass a
    # formatter, a typechecker and a green unit suite.
    "retrieval_change",
)
# Precedence rules this ROUTER resolves. atlas.yaml declares six; four are resolved by the
# caller (an override, a project manifest, an issue label, the generic fallback) and naming
# them here keeps the difference legible instead of implied. check() asserts this is a subset
# of the declared list, so a typo cannot invent a precedence level.
PRECEDENCE_IMPLEMENTED = ("artifact_extension", "language_directory")
def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


# THE C SCANNER WHERE libyaml IS PRESENT, the pure-Python one where it is not. Only the scanner and
# parser change: the refusal below lives in construct_mapping, which is Python under both, so the
# duplicate-key guarantee is identical. MEASURED at 2.27.0 — YAML parsing was 73% of a check().
_SAFE_BASE = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class StrictLoader(_SAFE_BASE):  # type: ignore[misc, valid-type]
    """A YAML loader that REFUSES a duplicate key instead of keeping the last one.

    THE COLLISION THIS PREVENTS, MEASURED: adding `'.fs': forth` beneath `'.fs': fsharp` moved
    every F# file to the Forth pack. PyYAML keeps the LAST duplicate key, reports nothing, and the
    diff reads as an addition — so the router answered confidently with the wrong pack and no
    instrument could see it. The defect is not in the router; it is in a parser that PICKS A WINNER
    where the document is ambiguous. A parser that refuses cannot be fooled, and it protects every
    mapping in the file — routes, instruments, runners, labels, task profiles — not the one place a
    collision happened to be noticed.
    """

    def construct_mapping(self, node, deep=False):  # type: ignore[override]
        seen: set = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                mark = key_node.start_mark
                raise ValueError(f"{key!r} is declared more than once at line {mark.line + 1} — "
                                 "YAML would keep the last one silently, so the earlier value is "
                                 "gone with no error and no warning")
            seen.add(key)
        return super().construct_mapping(node, deep)


def read_jsonc(path: str) -> object:
    """JSONC from a file. The parsing lives in `parse_jsonc` so it can be FUZZED without a file."""
    return parse_jsonc((ROOT / path).read_text(encoding="utf-8"))


def parse_jsonc(text: str) -> object:
    """JSON with // and /* */ comments, parsed with STRING STATE respected.

    WHY IT IS NOT A REGEX, measured the moment it was needed: `re.sub(r"//.*$", "", line)` deletes
    the rest of any line containing `//` — including the one inside "https://example". A host task
    config with a URL in it then fails to parse, which is the FRIENDLY outcome; the unfriendly one
    is a config that still parses after a comment-strip silently truncated a value.

    Editor configuration is JSONC by convention, so everything in this tree that reads a host's
    config reads it through here rather than writing that regex again.
    """
    out: list[str] = []
    in_string = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            out.append(char)
            if char == "\\" and index + 1 < len(text):
                out.append(text[index + 1])   # an escaped char is consumed whole, quote included
                index += 2
                continue
            if char == '"':
                in_string = False
            index += 1
            continue
        if text[index:index + 2] == "//":
            index = text.find("\n", index)
            if index < 0:
                break
            continue
        if text[index:index + 2] == "/*":
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        if char == '"':
            in_string = True
        out.append(char)
        index += 1
    # A TRAILING COMMA IS LEGAL IN JSONC AND NOT IN JSON, and editors write them. It is removed
    # HERE, inside the scan, and not by a regex over the finished text — FOUND BY THE FUZZ TARGET
    # ON ITS FIRST RUN: `re.sub(r",(\s*[}\]])", ...)` over the whole output also rewrote
    # `"[1, 2,]"` INSIDE a string literal, silently changing a value. That is precisely the bug
    # this parser exists to avoid, one layer down: a regular expression applied without respecting
    # string state. The scanner already knows where the strings are, so the removal belongs in it.
    text_out = "".join(out)
    result: list[str] = []
    index = 0
    in_string = False
    while index < len(text_out):
        char = text_out[index]
        if in_string:
            result.append(char)
            if char == "\\" and index + 1 < len(text_out):
                result.append(text_out[index + 1])
                index += 2
                continue
            if char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue
        if char == ",":
            ahead = index + 1
            while ahead < len(text_out) and text_out[ahead] in " \t\r\n":
                ahead += 1
            if ahead < len(text_out) and text_out[ahead] in "}]":
                index += 1          # a trailing comma, outside any string: drop it
                continue
        result.append(char)
        index += 1
    return json.loads("".join(result))


_PARSED: dict[bytes, object] = {}
_PARSED_BYTES = [0]
_PARSED_CAP_BYTES = 32 * 1024 * 1024


def strict_yaml(text: str, where: str) -> object:
    """Parse YAML, refusing duplicate keys. Every YAML read in this repository goes through here.

    CACHED BY CONTENT, NEVER BY NAME. MEASURED at 2.27.0: one check() parsed ~37 files 671 times,
    and parsing was 73% of its wall clock. A name-keyed cache is the trap packmanifest.reset_caches
    records — a planted defect read against the cached bytes passes while changing nothing. A key
    derived from the TEXT cannot serve stale data: editing the file changes the key, so a mutation
    test sees its mutation and needs no reset discipline to stay honest.

    A deep copy is returned, so one caller editing its result cannot rewrite another's. The store
    is bounded in BYTES of source text, and cleared rather than rotated, because a cache only ever
    costs a re-parse when emptied.
    """
    key = hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()
    hit = _PARSED.get(key)
    if hit is None:
        try:
            hit = yaml.load(text, Loader=StrictLoader)
        except ValueError as exc:
            raise ValueError(f"{where}: {exc}") from None
        if _PARSED_BYTES[0] + len(text) > _PARSED_CAP_BYTES:
            _PARSED.clear()
            _PARSED_BYTES[0] = 0
        _PARSED[key] = hit
        _PARSED_BYTES[0] += len(text)
    return copy.deepcopy(hit)


@lru_cache(maxsize=1)
def atlas() -> dict:
    data = strict_yaml(read("atlas.yaml"), "atlas.yaml")
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


@lru_cache(maxsize=1)
def _git_index() -> Path | None:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--git-path", "index"], cwd=ROOT)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    found = Path(out.decode().strip())
    return found if found.is_absolute() else ROOT / found


_TRACKED: dict[tuple[int, int], list[Path]] = {}


def tracked() -> list[Path]:
    """Every tracked path. KEYED ON THE GIT INDEX'S mtime and size, the file that changes exactly
    when the tracked set can: `git ls-files` spawned 33 times per check() at 2.27.0. Editing a
    tracked file's CONTENT does not touch the index, and that is correct — the set is unchanged."""
    index = _git_index()
    try:
        stamp = index.stat() if index else None
    except OSError:
        stamp = None
    key = (stamp.st_mtime_ns, stamp.st_size) if stamp else None
    if key and key in _TRACKED:
        return list(_TRACKED[key])
    try:
        raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        found = [ROOT / p for p in raw.decode().split("\0") if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
    if key:
        _TRACKED.clear()
        _TRACKED[key] = found
    return list(found)


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
