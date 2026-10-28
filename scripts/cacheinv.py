"""Refuse cache artifacts in the repository index or unignored source tree."""

from pathlib import PurePosixPath

from atlascore import ROOT, ls_files

CACHE_COMPONENTS = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".pyright",
        ".cache",
        "node_modules",
        ".npm",
        ".pnpm-store",
        ".next",
        ".zig-cache",
        "zig-out",
        ".coverage",
    }
)
CACHE_SUFFIXES = (".pyc", ".pyo", ".pyd", ".egg-info")


def _inv_no_repo_caches() -> str | None:
    for path in ls_files(ROOT, flags=("--cached", "--others", "--exclude-standard")):
        parts = PurePosixPath(path).parts
        if any(part in CACHE_COMPONENTS or part.endswith(CACHE_SUFFIXES) for part in parts) or any(
            parts[i : i + 2] == (".agent", "index") for i in range(len(parts) - 1)
        ):
            return f"cache artifact in repository: {path}"
    return None
