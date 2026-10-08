"""Run the install command the documents give, in a clean home, and judge `thea doctor` by exit code.

WHY (3.52.0). The README and docs/CONSUMING.md advertised `pipx install thea-software && thea doctor`
while no index carried that name and the released tag had no fetch path: the index answered 404, and
a non-editable install from the tag left `thea doctor` at exit 2, "no atlas". A documented command
that nothing executes is a claim with no enforcer. The command is now declared once,
`atlas.yaml/install_commands`, rendered into both documents as the `install` block, and executed by
`cli_test.py --install`; this module is that instrument's runner, not an instrument of its own.

ONE TEMPLATE, TWO SOURCES, FORKED AT THE LAST STEP. `{repo}` and `{tag}` are the only holes:
  --source local       (default, every pull request) a throwaway clone of HEAD, tagged v<VERSION>,
                       so the tree being merged is the tree installed — before its tag exists
  --source published   (after a release) the public repository at its real tag
The documents render the published source. Uncommitted edits are NOT installed by a local run: it
clones HEAD and prints which commit it installed.

ISOLATED: HOME, XDG_CACHE_HOME and the tool directories point into a temporary directory, and
THEA_ROOT, CODE_DEVELOPMENT_ROOT, VIRTUAL_ENV and PYTHONPATH are dropped, so nothing on this machine
can resolve the atlas for the installed command.

WHAT IT DOES NOT PROVE. That the tree under review installs from the index: the `index` row has no
`{repo}` hole, so under either source it installs the latest published release, never HEAD.

  python scripts/cli_test.py --install                      # exit 0 PASS · 1 FAIL · 2 NOT RUN
  python scripts/cli_test.py --install --source published
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from atlascore import ROOT, atlas, read, tracked

BLOCK = "install"
DROPPED = ("THEA_ROOT", "CODE_DEVELOPMENT_ROOT", "VIRTUAL_ENV", "PYTHONPATH")
# A line that installs THIS package, in any spelling a reader could paste: the index name, the old
# distribution name, the repository, or the editable clone the block itself uses.
INSTALLS_THEA = re.compile(r"\binstall\b.*(thea-software|thea-harness|HLIntel/thea-software|--editable ~/thea)")
CI = ".github/workflows/atlas-ci.yml"
RUNNER = "python scripts/cli_test.py --install"


def _version() -> str:
    return read("VERSION").strip()


def published_repo() -> str:
    identity = atlas()["identity"]
    return f"https://github.com/{identity['owner']}/{identity['repository']}"


def commands() -> dict[str, str]:
    """name -> template, from the one declaration."""
    return {name: row["command"] for name, row in (atlas().get("install_commands") or {}).items()}


def rendered(template: str, repo: str) -> str:
    return template.format(repo=repo, tag=f"v{_version()}")


def install_block() -> str:
    rows = (atlas().get("install_commands") or {}).values()
    lines = [f"# {row['label']}\n{rendered(row['command'], published_repo())}" for row in rows]
    return "```bash\n" + "\n".join(lines) + "\n```"


def documented_install_errors() -> list[str]:
    """Every line that installs Thea sits in the generated block, and CI executes that block."""
    errors = [] if commands() else ["atlas.yaml/install_commands is empty: the documents have no install to give"]
    begin, end = f"<!-- BEGIN generated: {BLOCK} ", f"<!-- END generated: {BLOCK} -->"
    for path in tracked():
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix not in {".md", ".txt"}:
            continue
        inside = False
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            inside = (inside or line.startswith(begin)) and not line.startswith(end)
            if not inside and INSTALLS_THEA.search(line):
                errors.append(
                    f"{rel}:{number}: installs Thea outside the generated `{BLOCK}` block, so nothing executes it"
                )
    if RUNNER not in read(CI):
        errors.append(f"{CI} does not run `{RUNNER}`: the documented install has no enforcer")
    return errors


def _local_source(work: Path) -> tuple[str, str]:
    src = work / "src"
    subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(src)], check=True, timeout=300)
    subprocess.run(["git", "-C", str(src), "tag", "-f", f"v{_version()}"], check=True, capture_output=True, timeout=60)
    head = subprocess.run(
        ["git", "-C", str(src), "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True, timeout=60
    ).stdout.strip()
    return f"file://{src}", f"local HEAD {head}"


def _clean_env(work: Path) -> dict[str, str]:
    home = work / "home"
    bin_dir = home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if k not in DROPPED}
    # The package cache is shared on purpose: it holds downloads, never a resolved atlas.
    env.setdefault("UV_CACHE_DIR", str(Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache", "uv")))
    env |= {
        "HOME": str(home),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "UV_TOOL_DIR": str(home / ".uv-tools"),
        "UV_TOOL_BIN_DIR": str(bin_dir),
        "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
    }
    return env


def main(argv: list[str]) -> int:
    source = argv[argv.index("--source") + 1] if "--source" in argv else "local"
    if source not in {"local", "published"}:
        print(f"refused: --source {source!r} is neither local nor published", file=sys.stderr)
        return 2
    missing = [tool for tool in ("git", "uv") if shutil.which(tool) is None]
    if missing or not commands():
        print(f"install check NOT RUN: missing {', '.join(missing) or 'atlas.yaml/install_commands'}")
        return 2
    failed = 0
    for name, template in commands().items():
        with tempfile.TemporaryDirectory(prefix="thea-install-") as tmp:
            work = Path(tmp)
            repo, what = _local_source(work) if source == "local" else (published_repo(), f"published v{_version()}")
            command = rendered(template, repo)
            done = subprocess.run(
                ["bash", "-c", command], cwd=work, env=_clean_env(work), capture_output=True, text=True, timeout=900
            )
            verdict = "PASS" if done.returncode == 0 else "FAIL"
            print(f"{verdict} {name} (exit {done.returncode}, source {what}): {command}")
            if done.returncode:
                failed += 1
                print((done.stdout + done.stderr)[-4000:])
    print(f"install commands: {len(commands()) - failed}/{len(commands())} pass")
    return 1 if failed else 0
