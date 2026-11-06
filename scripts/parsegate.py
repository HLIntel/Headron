"""Every tracked artifact parses: the first thing the contract asks, since nothing after it means anything otherwise.

Python, JSON, TOML, YAML, shell and Markdown fences, each read by the reader that really loads it. A verdict is
held per exact bytes, so an unchanged file is judged once and a planted one is always judged afresh.
"""

from __future__ import annotations

import hashlib
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

import yaml
from atlascore import (
    ROOT,
    blame_ignore_errors,
    interpreter_named,
    python_refusal,
    read_jsonc,
    rel,
    strict_yaml,
    text_of,
    tracked,
)
from headronlang import surface_errors

_VERDICTS: dict[bytes, list[str]] = {}
LOAD_FAILURES = (ValueError, SyntaxError, yaml.YAMLError)  # what a reader raises on a file `load_errors` refused


def judged_once(kind: str, raw: bytes, judge: Callable[[], list[str]]) -> list[str]:
    """`judge()` once per (kind, exact bytes). MEASURED 3.51.0: parse_errors is the preflight of every
    staged case and re-judged every unchanged file each time — 40% of the planted suite. The key is the
    content, never the name, so a planted file is always judged afresh (see parsed_python)."""
    key = hashlib.blake2b(kind.encode() + b"\0" + raw, digest_size=16).digest()
    if key not in _VERDICTS:
        _VERDICTS[key] = judge()
    return _VERDICTS[key]


def _refusal(
    path: Path,
    what: str,
    reader: Callable[[], object],
    exc_types: type[BaseException] | tuple[type[BaseException], ...],
) -> list[str]:
    try:
        reader()
    except exc_types as exc:
        return [f"{rel(path)} is not valid {what}: {str(exc).splitlines()[0] if what == 'YAML' else exc}"]
    return []


def _shell_errors(path: Path, raw: bytes) -> list[str]:
    shebang = raw[:64].split(b"\n", 1)[0].decode("utf-8", "replace")
    shell = interpreter_named(shebang) or ("bash" if path.suffix == ".sh" else "")  # the shebang first, then the suffix
    if not (shebang.startswith("#!") or path.suffix == ".sh") or shell not in {"sh", "bash", "dash", "zsh", "ksh"}:
        return []
    try:  # a missing interpreter is NOT RUN, said aloud: never a silent pass
        done = subprocess.run([shell, "-n", str(path)], capture_output=True, text=True, check=False, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"{rel(path)}: `{shell} -n` did not finish ({type(exc).__name__}), so its syntax was NOT checked"]
    if done.returncode:
        return [f"{rel(path)} is not valid {shell}: {(done.stderr.strip().splitlines() or ['?'])[0]}"]
    return []


def load_errors() -> list[str]:
    """The files later readers load and trust: Python, JSON, TOML and YAML. The check keeps reporting past one
    of these, and a reader that then raises on it is explained by this finding, not a crash of its own."""
    errors: list[str] = []
    for path in tracked():
        if path.suffix != ".py" or path.is_symlink() or not path.exists():
            continue
        if problem := python_refusal(text_of(path), str(path)):
            errors.append(f"{rel(path)} is not valid Python: {problem}")
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
    for path in (p for p in tracked() if p.suffix == ".toml" and p.is_file()):  # 3.19.0: a duplicate key hid here
        raw = path.read_bytes()
        errors += judged_once(
            f"toml:{rel(path)}",
            raw,
            lambda: _refusal(path, "TOML", lambda: tomllib.loads(raw.decode()), tomllib.TOMLDecodeError),
        )
    # YAML TOO (3.49.0). A CI workflow that does not load never runs, and only the forge says so, after the push.
    for path in (p for p in tracked() if p.suffix in {".yaml", ".yml"} and p.is_file() and not p.is_symlink()):
        raw = path.read_bytes()
        errors += judged_once(
            f"yaml:{rel(path)}",
            raw,
            lambda: _refusal(
                path, "YAML", lambda: strict_yaml(raw.decode("utf-8"), rel(path)), (ValueError, yaml.YAMLError)
            ),
        )
    return errors


def parse_errors(loaded: list[str] | None = None) -> list[str]:
    """Every tracked artifact PARSES — source and configuration alike, and this runs first.

    Nothing below this check means anything otherwise. A source file that does not compile makes
    every document count a report about a tree that cannot run; a configuration file that does not
    load is a capability that silently does nothing while looking present to whoever wrote it.

    Both halves were earned. A mechanical re-indent wrote invalid Python twice and the contract
    printed all of its counts. Two host configurations carried an invalid JSON escape, so neither
    loaded at all and the tasks they declared had never run.
    """
    errors = load_errors() if loaded is None else list(loaded)
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, check=False, timeout=20)
    blame = ROOT / ".git-blame-ignore-revs"
    errors += judged_once(
        "blame", head.stdout + (blame.read_bytes() if blame.is_file() else b"\0missing"), blame_ignore_errors
    )
    # SHELL IS READ BY ITS OWN INTERPRETER: bash judging zsh refuses correct code. A hook script with a syntax
    # error refuses nothing, and its caller reads the failure as a pass.
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
        fences = sum(1 for line in text_of(path, errors="replace").splitlines() if line.startswith("```"))
        if fences % 2:
            errors.append(
                f"{rel(path)} has {fences} code fences — an odd count means one never "
                "closes, and everything after it renders as code"
            )

    # AND THE SURFACE NOTATION, reported from this one call site. This check enumerates artifacts BY SUFFIX,
    # the shape that stops looking the moment a new kind of tracked file appears, and `.headron` was that file.
    errors += surface_errors()
    return errors
