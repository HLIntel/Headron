"""Conservative Python import impact from a consumer's base commit.

Static imports find candidates, not all consumers: dynamic imports, data files and other languages
remain unresolved. A candidate only adds checks; it never closes a deletion obligation.
"""

import ast
import io
import subprocess
import tokenize
from pathlib import Path, PurePosixPath

from atlascore import atlas, parsed_python, walked


def _git(tree: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=tree, capture_output=True, check=True, timeout=30).stdout


def _names(path: str) -> set[str]:
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return {".".join(parts[i:]) for i in range(len(parts))}


def _imports(source: bytes) -> set[str]:
    found: set[str] = set()
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(source).readline)
        parsed = parsed_python(source.decode(encoding), "base file")
        nodes = walked(parsed) if parsed else ()
        for node in nodes:
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module:
                    found.add(module)
                found.update(".".join(filter(None, (module, alias.name))) for alias in node.names)
    except (SyntaxError, ValueError, UnicodeError):
        pass  # the deletion remains unresolved even if a base file cannot be parsed
    return found


def python_dependents(tree: Path, deleted: list[str], base: str | None) -> list[str] | None:
    """Return surviving candidates from the merge base; None when the base could not be inspected at all.

    An empty list says the base was read and nothing imports the deleted file. None says nothing was read, and
    a caller that reports the two alike tells a reader the dependents were looked for."""
    if not any(path.endswith(".py") for path in deleted):
        return []
    default = (atlas().get("branch_policy") or {}).get("default_base") or "main"
    refs = (base,) if base else ("origin/HEAD", f"origin/{default}")
    commit = None
    for ref in refs:
        try:
            commit = _git(tree, "merge-base", str(ref), "HEAD").decode().strip()
            break
        except (subprocess.SubprocessError, OSError):
            continue
    if not commit:
        return None
    try:
        paths = [
            p.decode("utf-8", "surrogateescape")
            for p in _git(tree, "ls-tree", "-rz", "--name-only", commit).split(b"\0")
            if p.endswith(b".py")
        ]
        imports = {p: _imports(_git(tree, "show", f"{commit}:{p}")) for p in paths}
    except (subprocess.SubprocessError, OSError):
        return None
    affected = set(deleted)
    while True:
        names = set().union(*(_names(path) for path in affected if path.endswith(".py")))
        added = {path for path, uses in imports.items() if path not in affected and uses & names}
        if not added:
            break
        affected.update(added)
    return sorted(path for path in affected - set(deleted) if (tree / path).is_file())
