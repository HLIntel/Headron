#!/usr/bin/env python3
"""Plants for localtools: a project's own tool is found and run, and a clone can never choose what a hook runs."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

from localtools import find_tool, local_bin_dirs

TOOL = "headron-localtools-probe"
HERE = Path(__file__).resolve().parent


def _git(repo: Path, *args: str) -> None:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env, timeout=60)  # noqa: S603, S607


def _repo(top: Path) -> Path:
    repo = top / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    return repo


def _stub(folder: Path, name: str = TOOL, code: int = 0) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    stub = folder / name
    stub.write_text(f"#!/bin/sh\necho local-stub-ran\nexit {code}\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _expect(got: object, want: object, what: str) -> None:
    if got != want:
        raise SystemExit(f"FAIL localtools: {what}: got {got!r}, want {want!r}")


def untracked_install_wins_case(top: Path) -> None:
    repo = _repo(top)
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    stub = _stub(repo / "node_modules/.bin")
    _expect(find_tool(TOOL, repo), str(stub.resolve()), "an installed tool in node_modules/.bin")
    git_stub = _stub(repo / "node_modules/.bin", "git")
    _expect(find_tool("git", repo / "a.ts"), str(git_stub.resolve()), "the project's copy over PATH's, from a file")


def nearest_wins_and_top_stops_case(top: Path) -> None:
    _git(top, "init", "-q")  # a repository around this one: its install is still not this project's
    _stub(top / "node_modules/.bin")
    repo = _repo(top)
    _expect(find_tool(TOOL, repo), None, "a directory above the repository's top")
    _stub(repo / ".venv/bin")
    nearest = _stub(repo / "packages/app/node_modules/.bin")
    _expect(find_tool(TOOL, repo / "packages/app/a.ts"), str(nearest.resolve()), "the nearest of two installs")


def tracked_directory_refused_case(top: Path) -> None:
    repo = _repo(top)
    _stub(repo / "node_modules/.bin")
    _git(repo, "add", "-f", "node_modules")
    _expect(local_bin_dirs(repo), [], "a directory the clone itself delivered")
    _expect(find_tool(TOOL, repo), None, "a tool the clone itself delivered")


def tracked_symlink_refused_case(top: Path) -> None:
    repo = _repo(top)
    _stub(repo / "evil/.bin")
    (repo / "node_modules").symlink_to("evil")
    _git(repo, "add", "-A")
    _expect(find_tool(TOOL, repo), None, "a tracked symlink named node_modules")


def case_variant_refused_case(top: Path) -> None:
    """On a case-folding disk a tracked Node_Modules IS node_modules; a name comparison would trust it."""
    repo = _repo(top)
    _stub(repo / "Node_Modules/.bin")
    _git(repo, "add", "-f", "Node_Modules")
    _expect(find_tool(TOOL, repo), None, "a tracked directory spelled in another case")


def no_repository_refused_case(top: Path) -> None:
    _stub(top / "node_modules/.bin")
    _expect(find_tool(TOOL, top), None, "an unpacked tree with no repository")


def run_sites_case(top: Path) -> None:
    """The verdicts, not the finder: with tsc nowhere on PATH, the commit rung and the verify gate both run the stub."""
    repo = _repo(top)
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    (repo / "tsconfig.json").write_text("{}\n", encoding="utf-8")
    (repo / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    _stub(repo / "node_modules/.bin", "tsc", code=3)
    script = (
        f"import sys; sys.path.insert(0, {str(HERE)!r})\n"
        "from pathlib import Path\n"
        "import enforce, verify\n"
        f"repo = Path({str(repo)!r})\n"
        "print(enforce.check_file(repo / 'a.ts')[0])\n"
        "print(verify.run_gate({'id': 'g', 'argv': ['tsc']}, repo)['verdict'])\n"
    )
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["PATH"] = "/usr/bin:/bin"
    done = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, env=env, timeout=120, check=False
    )  # noqa: S603
    _expect(
        done.stdout.split(), ["FAIL", "FAIL"], f"tsc exiting 3 from node_modules/.bin (stderr {done.stderr[-200:]!r})"
    )


def run(module: ModuleType | None) -> None:
    for case in (
        untracked_install_wins_case,
        nearest_wins_and_top_stops_case,
        tracked_directory_refused_case,
        tracked_symlink_refused_case,
        case_variant_refused_case,
        no_repository_refused_case,
        run_sites_case,
    ):
        with tempfile.TemporaryDirectory(prefix="localtools-") as directory:
            case(Path(directory).resolve())


if __name__ == "__main__":
    run(None)
    print("localtools: 7 cases pass")
