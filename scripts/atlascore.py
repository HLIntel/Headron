#!/usr/bin/env python3
"""Atlas primitives: the declared rosters, the file readers and the router.

WHY THIS IS SEPARATE (1.3.0). scripts/atlas.py crossed its own MAX_CODE_LINES cap while gaining
machine-readable output, and the answer to a file hitting its cap is to split it by concern, not
to raise the cap on the guard that caught it. The arrows point one way: this module reads
atlas.yaml and the tree and knows nothing about the contract; atlasgen.py generates documents
from it; atlas.py enforces the contract and owns the CLI.
"""

from __future__ import annotations

import ast
import copy
import functools
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
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
    os.environ.get("THEA_ROOT")
    or os.environ.get("CODE_DEVELOPMENT_ROOT")  # the old name: deprecated, still read
    or getattr(sys, "_MEIPASS", None)
    or Path(__file__).resolve().parents[1]
)


def worktree() -> Path:
    """The git repository a command ACTS ON — not always the atlas it READS its policy from.

    ROOT answers "where are the rules"; this answers "whose tree is changing". Here they are one path.
    From another repository an agent routes through this atlas and lands in ITS OWN tree: every git
    command in a landing runs here, never at ROOT. Refuses outside a git repository rather than falling
    back to ROOT, because a fallback would retarget a push at the atlas — `none` is a real answer.
    """
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    ).stdout.strip()
    if not out:
        raise ValueError(
            f"REFUSED: {Path.cwd()} is not inside a git repository, so there is no tree to "
            "land. Run this from the repository you mean to change; the atlas it reads its "
            "policy from is a separate question, answered by THEA_ROOT."
        )
    return Path(out).resolve()


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
    "wiki/README.md",
    "wiki/CODE-ROUTING.md",
    "wiki/BRANCH-WORKTREES.md",
    "wiki/LABELS-TAGS.md",
    "wiki/LANGUAGE-LANES.md",
    "wiki/TOOL-ORCHESTRATION.md",
    "wiki/LANGUAGE-OPERATIONS.md",
)
CODE_SUFFIXES = {
    ".py",
    ".pyi",
    ".rs",
    ".go",
    ".ts",
    ".tsx",
    ".c",
    ".h",
    ".cpp",
    ".cc",
    ".hpp",
    ".zig",
    ".mojo",
    ".jl",
    ".ex",
    ".exs",
    ".gleam",
    ".nim",
    ".v",
    ".odin",
    ".ha",
    ".fut",
    ".hs",
    ".lhs",
    ".fs",
    ".fsx",
    ".chpl",
    ".bqn",
    ".ua",
    ".lean",
    ".carbon",
    ".roc",
    ".qs",
    ".cu",
    ".cuh",
    ".sql",
    ".sh",
    ".bash",
    ".wat",
    ".wasm",
    ".ml",
    ".mli",
    ".scala",
    ".sc",
    ".swift",
    ".r",
    ".slq",
    ".fth",
    ".4th",
}
BLOB_SUFFIXES = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".onnx",
    ".pt",
    ".pth",
    ".safetensors",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".iso",
    ".db",
    ".sqlite",
    ".sqlite3",
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
    "source_change",
    "api_change",
    "dependency_change",
    "security_sensitive",
    "concurrency_change",
    "performance_change",
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
PRECEDENCE_IMPLEMENTED = ("artifact_extension", "project_manifest", "language_directory")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


# THE C SCANNER WHERE libyaml IS PRESENT, the pure-Python one where it is not. Only the scanner and
# parser change: the refusal below lives in construct_mapping, which is Python under both, so the
# duplicate-key guarantee is identical. MEASURED at 2.27.0 — YAML parsing was 73% of a check().
_SAFE_BASE = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class _RefusesDuplicates:
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
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            # A FLOW VALUE SPLIT ON A COMMA (3.3.0): in `{k: a, b}` the comma ends the value and `b`
            # becomes a key with nothing after it. Six declarations lost half their text that way.
            if node.flow_style and value_node.tag.endswith(":null") and value_node.value == "":
                raise ValueError(
                    f"{key!r} has no value at line {key_node.start_mark.line + 1} — a flow "
                    "value split on a comma; quote the value that holds it"
                )
            if key in seen:
                mark = key_node.start_mark
                raise ValueError(
                    f"{key!r} is declared more than once at line {mark.line + 1} — "
                    "YAML would keep the last one silently, so the earlier value is "
                    "gone with no error and no warning"
                )
            seen.add(key)
        return super().construct_mapping(node, deep)  # type: ignore[misc]


class StrictLoader(_RefusesDuplicates, _SAFE_BASE):  # type: ignore[misc, valid-type]
    """The strict loader on libyaml when installed: what every read in this repository uses."""


class PortableLoader(_RefusesDuplicates, yaml.SafeLoader):
    """The same refusals on the PURE-Python parser, which a machine without libyaml falls back to."""


def portable_yaml(text: str, where: str) -> object:
    """Parse `text` the way a machine WITHOUT libyaml would (3.50.0): the two parsers disagree on some plain
    scalars, so a value a writer emits must read back under both. Uncached: only short values come here."""
    try:
        return yaml.load(text, Loader=PortableLoader)  # noqa: S506 — a SafeLoader subclass
    except ValueError as exc:
        raise ValueError(f"{where}: {exc}") from None


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
    # A TRAILING COMMA IS LEGAL IN JSONC AND NOT IN JSON, and editors write them. It is dropped IN THIS
    # SCAN, never by a regex over the finished text — FOUND BY THE FUZZ TARGET ON ITS FIRST RUN: a
    # `re.sub(r",(\s*[}\]])", ...)` also rewrote `"[1, 2,]"` INSIDE a string literal. At a closing
    # bracket outside any string, comments are already gone and strings were emitted whole, so a comma
    # that is the last non-blank character emitted is a real trailing comma (#27: one scanner, not two).
    out: list[str] = []
    in_string = False
    index = 0
    while index < len(text):
        char = text[index]
        if in_string:
            out.append(char)
            if char == "\\" and index + 1 < len(text):
                out.append(text[index + 1])  # an escaped char is consumed whole, quote included
                index += 2
                continue
            if char == '"':
                in_string = False
            index += 1
            continue
        if text[index : index + 2] == "//":
            index = text.find("\n", index)
            if index < 0:
                break
            continue
        if text[index : index + 2] == "/*":
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        if char in "}]":
            back = len(out) - 1
            while back >= 0 and out[back] in " \t\r\n":
                back -= 1
            if back >= 0 and out[back] == ",":
                del out[back]
        in_string = char == '"'
        out.append(char)
        index += 1
    return json.loads("".join(out), object_pairs_hook=_unique_keys)


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """A DUPLICATE KEY IS REFUSED, never resolved: `json` keeps the last one silently, so the
    earlier value is a setting somebody wrote and nothing reads (rule 4: refuse, never pick)."""
    seen: dict[str, object] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen[key] = value
    return seen


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


_TREES: dict[bytes, object] = {}
_TREE_BYTES = [0]


def parsed_python(text: str, where: str):
    """The syntax tree for `text`, or None when it does not parse. CACHED BY CONTENT, NEVER BY NAME.

    MEASURED at 3.34.0. Six instruments walk the same Python sources in one contract run — three
    forbidden_calls rows, the instrument reachability closure, the orphan sweep and the shape cap — and
    each parsed every file again. The profile put callshape alone at 0.89s of a 4.37s run, almost all of
    it re-parsing what the previous row had just parsed.

    Same contract as strict_yaml, for the same reason: a key derived from the TEXT cannot serve stale
    data to a mutation test, whereas a name-keyed cache silently would. Unlike strict_yaml this returns
    the SHARED tree rather than a copy — an ast.Module is large, deep-copying it would give back the cost
    the cache exists to remove, and every caller here only ever walks it. A caller that intends to MUTATE
    a tree must parse its own; nothing in this tree does.

    None on a SyntaxError, never a raise: a file that does not parse is the parse check's finding, which
    runs first and reports it once. An instrument that crashed on it would hide that finding behind its
    own traceback, which is `a_guard_that_crashes_on_another_guards_input` — four sightings here.
    """
    key = hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()
    if key in _TREES:
        return _TREES[key]
    try:
        tree = ast.parse(text, where)
    except (SyntaxError, ValueError):
        tree = None
    if _TREE_BYTES[0] + len(text) > _PARSED_CAP_BYTES:
        _TREES.clear()
        _WALKS.clear()
        _TREE_BYTES[0] = 0
    _TREES[key] = tree
    _TREE_BYTES[0] += len(text)
    return tree


_WALKS: dict[int, tuple] = {}


def walked(node) -> tuple:
    """Every node under `node`, walked ONCE per shared tree (3.50.0).

    MEASURED: one contract run called ast.walk over a million times — seven instruments re-walking the
    trees parsed_python already shares, about a quarter of the run. Keyed by identity, which is safe only
    because the key's node is held in the value (an id is never reused while it lives) and the trees are
    the shared, content-keyed, never-mutated ones; cleared with them."""
    hit = _WALKS.get(id(node))
    if hit is None or hit[0] is not node:
        hit = _WALKS[id(node)] = (node, tuple(ast.walk(node)))
    return hit[1]


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


def project_manifests() -> dict[str, str]:
    """Filenames that name their pack; their extensions are shared by every other tool's config."""
    return {str(k): str(v) for k, v in (atlas().get("project_manifests") or {}).items()}


def route_targets() -> list[str]:
    return sorted(set(routes().values()) | set(project_manifests().values()))


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
    manifest = project_manifests().get(path.name)
    if manifest:
        return manifest, named("project_manifest"), f"{path.name} in atlas.yaml/project_manifests"
    try:
        parts = path.resolve().relative_to(ROOT.resolve()).parts
    except ValueError:
        return None, "none", "the path is outside this repository, so no segment of it routes"
    if "languages" in parts:
        i = parts.index("languages")
        for depth in (2, 1):
            candidate = "/".join(parts[i + 1 : i + 1 + depth])
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
        out = subprocess.check_output(["git", "rev-parse", "--git-path", "index"], cwd=ROOT, timeout=600)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    found = Path(out.decode().strip())
    return found if found.is_absolute() else ROOT / found


_TRACKED: dict[tuple[int, int], list[Path]] = {}


def changed_paths(tree: Path) -> list[str]:
    """Every path the working tree changed, from `git status -z`: ONE parser for every caller (agentrun's
    scope gate and verify's fast loop each sliced `ln[3:]`, mangling a rename's origin and a quoted name).
    A git that cannot answer REFUSES — an empty list passes every scope. A rename yields its new path only."""
    done = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        cwd=tree,
        capture_output=True,  # noqa: S607
        text=True,
        check=False,
        timeout=60,
    )
    if done.returncode:
        raise SystemExit(f"git status failed in {tree}: {done.stderr.strip()}")
    fields, out = iter(done.stdout.split("\0")), set()
    for field in fields:
        if len(field) > 3:
            out.add(field[3:])
            if field[0] in "RC":
                next(fields, None)  # the origin arrives as its own field, with no status prefix
    return sorted(out)


def diff_names(tree: Path, *revs: str) -> list[str]:
    """Every path `git diff revs` names, NUL-split: ONE parser for every caller (one split on whitespace, so a
    path with a space became two). A git that cannot answer RAISES ValueError with its own words — an empty
    list passes every scope, so each caller decides out loud whether to refuse or fall back."""
    done = subprocess.run(
        ["git", "diff", "--name-only", "-z", *revs], cwd=tree, capture_output=True, text=True, check=False, timeout=600
    )
    if done.returncode:
        raise ValueError(done.stderr.strip()[:300])
    return sorted(f for f in done.stdout.split("\0") if f)


def ls_files(tree: Path, *pathspec: str, flags: tuple[str, ...] = ()) -> list[str]:
    """Every path `tree` tracks, NUL-split: ONE reader for every caller. A git that cannot answer REFUSES —
    the inline copies this replaced split it differently, and two returned [] outside a repository."""
    done = subprocess.run(
        ["git", "ls-files", "-z", *flags, "--", *pathspec],
        cwd=tree,
        capture_output=True,  # noqa: S607
        text=True,
        errors="surrogateescape",
        check=False,
        timeout=600,
    )
    if done.returncode:
        raise SystemExit(f"git ls-files failed in {tree}: {done.stderr.strip()}")
    return [p for p in done.stdout.split("\0") if p]


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
        found = [ROOT / p for p in ls_files(ROOT)]
    except (SystemExit, FileNotFoundError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
    if key:
        _TRACKED.clear()
        _TRACKED[key] = found
    return list(found)


@functools.lru_cache(maxsize=8)
def _resolved(root: Path) -> Path:
    return root.resolve()


@functools.lru_cache(
    maxsize=8192
)  # resolve() is a syscall per part; check() asks for the same paths thousands of times
def rel(path: Path) -> str:
    return path.resolve().relative_to(_resolved(ROOT)).as_posix()


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


def md_anchors(text: str) -> set[str]:
    """The fragment ids a Markdown page renders, by GitHub's rule: headings outside code fences, lower-cased,
    punctuation dropped, spaces to hyphens, repeats suffixed -1, -2; plus explicit `id=`/`name=` anchors."""
    counts: dict[str, int] = {}
    slugs: set[str] = set()
    fenced = False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        heading = None if fenced else re.match(r"#{1,6}\s+(.*?)\s*#*\s*$", line)
        if heading:
            words = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading[1])
            slug = re.sub(r"[^\w\- ]", "", words.lower()).replace(" ", "-")
            slugs.add(f"{slug}-{counts[slug]}" if slug in counts else slug)
            counts[slug] = counts.get(slug, 0) + 1
    return slugs | set(re.findall(r"""<a\s[^>]*?(?:id|name)=["']([^"']+)["']""", text))


def anchor_error(source: Path, raw: str) -> str | None:
    """A `#fragment` link into a Markdown page names a heading that page renders (3.50.0): the path
    check passed a renamed heading, and the reader lands at the top of the page with no error."""
    raw = raw.strip().strip("<>")
    if "#" not in raw or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw):
        return None
    path, fragment = raw.split("#", 1)
    target = (source.parent / path.split("?", 1)[0]).resolve() if path else source
    if target.suffix.lower() != ".md" or not target.is_file() or not fragment:
        return None
    from urllib.parse import unquote  # noqa: PLC0415

    if unquote(fragment).lower() in md_anchors(target.read_text(encoding="utf-8", errors="replace")):
        return None
    return f"broken anchor: {rel(source)} -> {raw} (no such heading in {rel(target)})"


def editorconfig_errors() -> list[str]:
    """Every tracked text file obeys what the .editorconfig sections matching it declare.

    MEASURED at 2.27.0: the contract checked that .editorconfig EXISTED and nothing checked that
    any file obeyed it — 34 tracked files lacked the final newline it requires, and one had
    trailing whitespace from an edit made the same session. A declared control no instrument reads
    is a comment with a file extension. The rules are READ from the file, so editing .editorconfig
    changes what is enforced with no second copy here to update.
    """
    import configparser as _cp  # noqa: PLC0415 — only this check reads INI
    import fnmatch  # noqa: PLC0415

    parser = _cp.ConfigParser(interpolation=None)
    try:
        parser.read_string(read(".editorconfig").replace("root = true", "", 1))
    except _cp.Error as exc:
        return [f".editorconfig does not parse: {exc}"]
    # EVERY SECTION, resolved per file in file order, later wins (3.50.0): only [*] was read, so
    # `indent_style = space` and `charset` were declared for every route and enforced for none.
    sections = []
    for pattern in parser.sections():
        brace = re.fullmatch(r"(.*)\{(.*)\}(.*)", pattern)
        globs = [brace[1] + alt + brace[3] for alt in brace[2].split(",")] if brace else [pattern]
        sections.append((globs, dict(parser[pattern])))
    binary = {".webp", ".png", ".jpg", ".ico", ".gz", ".zip"}
    errors: list[str] = []
    for path in tracked():
        name = path.relative_to(ROOT).as_posix()
        if (
            not path.is_file()
            or path.is_symlink()
            or path.suffix.lower() in binary
            or name.endswith((".bat", ".cmd", ".ps1"))
        ):
            continue  # binary, or a Windows script whose own section declares crlf
        raw = path.read_bytes()
        if not raw:
            continue
        rules: dict[str, str] = {}
        for globs, values in sections:
            if any(fnmatch.fnmatch(path.name, glob) for glob in globs):
                rules.update(values)
        if rules.get("insert_final_newline") == "true" and not raw.endswith(b"\n"):
            errors.append(f"{name} has no final newline, which .editorconfig requires")
        if rules.get("end_of_line") == "lf" and b"\r\n" in raw:
            errors.append(f"{name} has CRLF line endings, which .editorconfig forbids")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            text = raw.decode("utf-8", "replace")
            if rules.get("charset") == "utf-8":
                errors.append(f"{name} is not UTF-8 (byte {exc.start}), which .editorconfig requires")
        lines = text.split("\n")
        # Markdown is exempt from the whitespace rule BY FORMAT: two trailing spaces are a hard
        # line break there, so stripping them would change the rendered document.
        if (
            rules.get("trim_trailing_whitespace") == "true"
            and not name.endswith(".md")
            and any(line != line.rstrip(" \t") for line in lines)
        ):
            errors.append(f"{name} has trailing whitespace, which .editorconfig forbids")
        if rules.get("indent_style") == "space" and (
            tab := next((n for n, ln in enumerate(lines, 1) if ln.startswith("\t")), 0)
        ):
            errors.append(f"{name}:{tab} is tab-indented, and .editorconfig declares indent_style = space")
    return errors


def blame_ignore_errors() -> list[str]:
    """`.git-blame-ignore-revs` names commits ON THIS HISTORY. Found at 3.50.0: a rebase-merge
    rewrote the formatting commit, the file kept the pre-rebase hash, and blame skipped nothing
    while the file looked correct. A shallow clone cannot answer, so it is refused, never passed."""
    path = ROOT / ".git-blame-ignore-revs"
    if not path.is_file():
        return [".git-blame-ignore-revs is missing, so a mechanical reformat is blamed on its author"]
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()]
    shas = [ln for ln in lines if ln and not ln.startswith("#")]
    errors = [
        f".git-blame-ignore-revs: {sha!r} is not a full 40-hex commit"
        for sha in shas
        if not re.fullmatch(r"[0-9a-f]{40}", sha)
    ]
    git = ["git", "-C", str(ROOT)]
    shallow = subprocess.run(
        [*git, "rev-parse", "--is-shallow-repository"], capture_output=True, text=True, check=False, timeout=20
    )
    if shallow.stdout.strip() != "false":
        return [
            *errors,
            ".git-blame-ignore-revs: shallow or no history, so its commits were NOT checked (fetch-depth: 0)",
        ]
    for sha in (s for s in shas if re.fullmatch(r"[0-9a-f]{40}", s)):
        if subprocess.run(
            [*git, "merge-base", "--is-ancestor", sha, "HEAD"], capture_output=True, check=False, timeout=20
        ).returncode:
            errors.append(
                f".git-blame-ignore-revs: {sha} is not an ancestor of HEAD — a rebase rewrote it; name the landed hash"
            )
    return errors


_VERDICTS: dict[bytes, list[str]] = {}


def judged_once(kind: str, raw: bytes, judge) -> list[str]:
    """`judge()` once per (kind, exact bytes). MEASURED 3.51.0: parse_errors is the preflight of every
    staged case and re-judged every unchanged file each time — 40% of the planted suite. The key is the
    content, never the name, so a planted file is always judged afresh (see parsed_python)."""
    key = hashlib.blake2b(kind.encode() + b"\0" + raw, digest_size=16).digest()
    if key not in _VERDICTS:
        _VERDICTS[key] = judge()
    return _VERDICTS[key]


def _refusal(path: Path, what: str, reader, exc_types) -> list[str]:
    try:
        reader()
    except exc_types as exc:
        return [f"{rel(path)} is not valid {what}: {str(exc).splitlines()[0] if what == 'YAML' else exc}"]
    return []


def _shell_errors(path: Path, raw: bytes) -> list[str]:
    shebang = raw[:64].split(b"\n", 1)[0].decode("utf-8", "replace")
    words = shebang[2:].split()[:2]  # `#!/bin/sh` or `#!/usr/bin/env bash`: the interpreter's own name
    shell = (
        "bash"
        if path.suffix == ".sh"
        else Path(words[-1] if words[:1] and words[0].endswith("/env") else (words or [""])[0]).name
    )
    if not (shebang.startswith("#!") or path.suffix == ".sh") or shell not in {"sh", "bash", "dash", "zsh", "ksh"}:
        return []
    try:  # a missing interpreter is NOT RUN, said aloud: never a silent pass
        done = subprocess.run([shell, "-n", str(path)], capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"{rel(path)}: `{shell} -n` did not finish ({type(exc).__name__}), so its syntax was NOT checked"]
    if done.returncode:
        return [f"{rel(path)} is not valid {shell}: {(done.stderr.strip().splitlines() or ['?'])[0]}"]
    return []


def parse_errors() -> list[str]:
    """Every tracked artifact PARSES — source and configuration alike, and this runs first.

    Nothing below this check means anything otherwise. A source file that does not compile makes
    every document count a report about a tree that cannot run; a configuration file that does not
    load is a capability that silently does nothing while looking present to whoever wrote it.

    Both halves were earned. A mechanical re-indent wrote invalid Python twice and the contract
    printed all of its counts. Two host configurations carried an invalid JSON escape, so neither
    loaded at all and the tasks they declared had never run.
    """
    errors: list[str] = []
    # EVERY TRACKED SOURCE FILE MUST PARSE, AND THIS IS FIRST BECAUSE NOTHING BELOW IT IS
    # MEANINGFUL OTHERWISE. Measured cause: a mechanical re-indent of one function wrote a file
    # that no longer compiled, twice in a row, and the contract said nothing — it read documents
    # and rosters and never asked whether its own harness was still valid Python. A transformation
    # is not finished when the bytes are written; it is finished when the artifact parses.
    for path in tracked():
        if path.suffix != ".py" or path.is_symlink() or not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if parsed_python(text, str(path)) is not None:  # the shared content-keyed tree every instrument walks
            continue
        try:  # only a file that fails pays a second parse, to name the error and its line
            ast.parse(text, filename=str(path))
        except (SyntaxError, ValueError) as exc:
            errors.append(
                f"{rel(path)} is not valid Python: {exc.__class__.__name__} at line {getattr(exc, 'lineno', '?')}"
            )
    # EVERY TRACKED JSON PARSES, and this sits beside the Python parse check for the same reason:
    # a configuration file that does not parse is a capability that silently does nothing. Found by
    # trying — .vscode/tasks.json carried `"\${file}"`, an invalid JSON escape, so the whole file
    # failed to load and the task it declared had never worked. Editor configuration is JSONC by
    # convention, so it is read through the reader that understands comments and trailing commas.
    for path in tracked():
        if path.suffix.lower() not in {".json", ".jsonc", ".example"} or path.is_symlink() or not path.exists():
            continue
        if path.suffix.lower() == ".example" and ".json" not in path.name:
            continue
        errors += judged_once(
            f"json:{rel(path)}",
            path.read_bytes(),
            lambda: _refusal(path, "JSON", lambda: read_jsonc(rel(path)), ValueError),
        )
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, check=False, timeout=20)
    blame = ROOT / ".git-blame-ignore-revs"
    errors += judged_once(
        "blame", head.stdout + (blame.read_bytes() if blame.is_file() else b"\0missing"), blame_ignore_errors
    )
    for path in (p for p in tracked() if p.suffix == ".toml" and p.is_file()):  # 3.19.0: a duplicate key hid here
        raw = path.read_bytes()
        errors += judged_once(
            f"toml:{rel(path)}",
            raw,
            lambda: _refusal(path, "TOML", lambda: tomllib.loads(raw.decode()), tomllib.TOMLDecodeError),
        )
    # YAML AND SHELL PARSE TOO (3.49.0). A CI workflow that does not load never runs, and only the forge
    # says so, after the push; a hook script with a syntax error refuses nothing, and its caller reads
    # the failure as a pass. Shell is read by its OWN interpreter: bash judging zsh refuses correct code.
    for path in (p for p in tracked() if p.suffix in {".yaml", ".yml"} and p.is_file() and not p.is_symlink()):
        raw = path.read_bytes()
        errors += judged_once(
            f"yaml:{rel(path)}",
            raw,
            lambda: _refusal(
                path, "YAML", lambda: strict_yaml(raw.decode("utf-8"), rel(path)), (ValueError, yaml.YAMLError)
            ),
        )
    for path in (p for p in tracked() if p.is_file() and not p.is_symlink() and (p.suffix == ".sh" or not p.suffix)):
        raw = path.read_bytes()
        errors += judged_once(f"shell:{rel(path)}", raw, lambda: _shell_errors(path, raw))

    # AN UNCLOSED CODE FENCE SWALLOWS THE REST OF THE DOCUMENT. Everything after it renders as
    # code: the headings, the links, the tables. The file still parses, still passes a link check
    # if the swallowed links were already valid, and looks like a formatting preference rather
    # than a page that stopped working halfway down.
    for path in tracked():
        if path.suffix.lower() != ".md" or path.is_symlink() or not path.exists():
            continue
        fences = sum(
            1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("```")
        )
        if fences % 2:
            errors.append(
                f"{rel(path)} has {fences} code fences — an odd count means one never "
                "closes, and everything after it renders as code"
            )

    # AND THE SURFACE NOTATION, HERE RATHER THAN IN A ROSTER OF ITS OWN. This check enumerates
    # artifacts BY SUFFIX, which is the shape that silently stops looking the moment a new kind of
    # tracked file appears (code-quality §8) — `.thea` was exactly that file. It is reported from
    # ONE call site and deliberately NOT given a 43rd hard invariant: an invariant whose check is a
    # second call to this function would print every finding twice and make one rule two
    # declarations. `thealang.surface_errors` is where the rule lives.
    from thealang import surface_errors  # noqa: PLC0415 — thealang reads this module; lazy one way

    errors += surface_errors()
    return errors
