"""Where one gate runs for one file, and whether running it there proves anything.

ONE RESOLVER for `gate`, `verify` in a consumer, the landing and the commit hook. It answers {"argv", "home"}
when the gate runs, or {"why"} when no run of it here proves anything: no project above a per-project verb,
a crate member handed to bare `rustc`, a formatter the repository never adopted, or a tool that cannot
read this file's dialect. MEASURED AT 3.62.0 on 8 public repositories (docs/BENCHMARK-POLYGLOT.md).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from atlascore import ROOT, atlas, headron_home, parse_jsonc, text_of


def project_home(path: Path, marker: str) -> Path | None:
    """The nearest directory above `path`, up to its repository's top, holding `marker`.

    GLOBBED, not compared: `*.?sproj` can never be an exact filename, and a literal name globs to itself.
    BOUNDED BY THE REPOSITORY: a stray Cargo.toml in a parent of the clone is not this file's project."""
    for folder in path.resolve().parents:
        if next(folder.glob(marker), None):
            return folder
        if (folder / ".git").exists():
            return None
    return None


def _repository_folders(path: Path) -> list[Path] | None:
    """The folders from `path`'s own up to its repository's top, or None outside any repository."""
    folders: list[Path] = []
    for folder in path.resolve().parents:
        folders.append(folder)
        if (folder / ".git").exists():
            return folders
    return None


def _names(file: Path, spelling: str) -> bool:
    """Whether a build, hook or CI file spells the tool. text_of holds the read against the file's stat, so a
    file a case writes after an earlier lookup is read fresh, and each file is read once per check."""
    try:
        return re.search(spelling, text_of(file, errors="replace")) is not None
    except OSError:
        return False


def unadopted(path: Path, tool: str, spec: dict) -> str | None:
    """None when the repository holding `path` adopts `tool`, else why its formatter gate proves nothing.

    A STYLE IS THE REPOSITORY'S CHOICE (3.63.0). Measured on 8 public repositories: 31 of 58 FAIL rows were
    prettier, shfmt, taplo or ruff checking files in repositories that configure none of them, so a FAIL
    reported the default style, not a defect. ADOPTED means the tool's config file sits between the file
    and its repository's top, or a build, hook or CI file there names it. An `.editorconfig` adopts only the
    tool it names or whose own key it sets (shfmt's switch_case_indent): indent_style alone is read by every
    formatter and chooses none. A toolchain's own formatter (rustfmt,
    gleam format) has no entry here and always runs: its style is the language's, not the repository's."""
    configs = (spec.get("adopted_by") or {}).get(tool)
    if configs is None:
        return None
    folders = _repository_folders(path)
    if folders is None:
        return f"{tool} checks a repository's chosen style and this file is in no repository"
    spelling = (spec.get("named_as") or {}).get(tool)
    for folder in folders:
        if any(next(folder.glob(c), None) for c in configs):
            return None
        if spelling and any(_names(f, spelling) for g in spec.get("named_in") or [] for f in folder.glob(g)):
            return None
    said = " or ".join(configs) if configs else "config file it reads"
    return f"the repository does not adopt {tool}: no {said} above this file, and no build, hook or CI file names it"


def _json_with_comments(text: str) -> bool:
    """Strict JSON refuses it and the JSONC reader takes it: a comment, not a defect, is all jq would fail on.
    A file broken in BOTH readers is not this dialect, so jq still runs and its FAIL stands."""
    try:
        json.loads(text)
        return False
    except ValueError:
        pass
    try:
        parse_jsonc(text)
        return True
    except ValueError:
        return False


# A BuildKit heredoc on an instruction: `RUN <<EOF`, `COPY <<-"END" /x`; a `<<<` here-string is not one.
_HEREDOC = re.compile(r"(?mi)^\s*(?:RUN|COPY|ADD)\b[^\n]*(?<!<)<<(?!<)-?\s*[\"']?[A-Za-z_]\w*")

DIALECTS = {"json_with_comments": _json_with_comments, "dockerfile_heredoc": lambda t: bool(_HEREDOC.search(t))}


def misread(path: Path, tool: str, spec: dict) -> str | None:
    """Why `tool` cannot read this file's dialect, or None when it can (or the file cannot be read at all)."""
    entry = (spec.get("cannot_read") or {}).get(tool)
    if not entry:
        return None
    try:
        text = text_of(path, errors="replace")
    except OSError:
        return None
    return f"{tool} cannot read {entry['why']}" if DIALECTS[entry["dialect"]](text) else None


def _anchored(path_value: str) -> Path:
    """The file a relative path names: from the working directory, else from the atlas, as shebang_dialect reads it.

    MEASURED: `headron check` run from outside the tree (the install case) resolved `scripts/doctor.py`
    against the working directory, found no repository and called ruff unadopted, so the README's live
    `gate` example drifted only off-tree."""
    path = Path(path_value)
    try:  # exists() raises on a name too long to stat
        return ROOT / path if not path.is_absolute() and not path.exists() else path
    except (OSError, ValueError):
        return path


def placement(path_value: str, gate: str, argv: list[str] | None) -> dict:
    """Where one gate runs for one file: {"argv", "home"}, or {"why"} when no run of it here proves anything.

    MEASURED AT 3.62.0: `verify` ran per-project verbs from the tree root with no project there, so `tsc`
    printed its help, `go vet ./...` found no module and bare `bats` read no test, each reported FAIL against
    a change that broke nothing — 29 of 82 FAIL rows were the atlas's own invocation.
    """
    spec = (atlas().get("gate_tools") or {}).get(gate) or {}
    verb = " ".join(argv or [])
    if not argv:
        return {"argv": argv, "home": None}
    path = _anchored(path_value)
    if why := unadopted(path, argv[0], spec) or misread(path, argv[0], spec):
        return {"why": why}
    if marker := (spec.get("per_directory") or {}).get(verb):
        home = project_home(path, str(marker))
        if not home:
            return {"why": f"{verb} runs per project and no {marker} is above this file"}
        return {"argv": argv, "home": home, "cwd": os.path.relpath(home)}
    owner = (spec.get("project_owned") or {}).get(verb)
    if owner and project_home(path, str(owner)):
        return {
            "why": f"a member of the {owner} project above it, which its project build compiles; "
            f"`{verb}` alone cannot resolve its crate imports"
        }
    if why := built_by(path, argv[0], spec):
        return {"why": why}
    operand = spec.get("needs_operand") or {}
    if verb in operand:
        if not operand[verb] or not re.search(str(operand[verb]), path.name):
            return {"why": f"{verb} runs one test file and this file is not one it reads"}
        return {"argv": [*argv, path_value], "home": None}
    out = (spec.get("writes_output") or {}).get(argv[0])
    flags = [*out, gate_output()] if out else []
    return {"argv": [*argv, *flags, path_value] if spec.get("takes_path") else argv, "home": None}


def gate_output() -> str:
    """The one directory a compiling gate writes into: outside every checkout, and the same on every call, so a
    record's argv stays one (argv, cwd) and a dedupe still runs it once. Under Headron's own home, never the shared
    temp dir, where another user's file of that name would block every run. Made here: scalac -d needs it."""
    out = headron_home() / "gate-out"
    out.mkdir(parents=True, exist_ok=True)
    return str(out)


def built_by(path: Path, tool: str, spec: dict) -> str | None:
    """Why `tool` alone proves nothing here: a build file at or above `path`, inside its repository, names it.

    MEASURED (polyglot benchmark): per-file clang and swiftc FAILED 5 files on missing include paths and sibling
    symbols, each one compiled by a Makefile that names it with the flags the bare compile lacked. A build file
    that does not name the file (a task runner) leaves the per-file gate running."""
    names = (spec.get("built_by") or {}).get(tool) or []
    spelling = rf"(?<![\w-]){re.escape(path.name)}(?![\w.-])"
    for folder in path.resolve().parents:
        for name in names:
            if (folder / name).is_file() and _names(folder / name, spelling):
                return f"{name} in {folder.name or folder} names {path.name}, so its build carries the flags `{tool}` alone lacks"
        if (folder / ".git").exists():
            return None
    return None
