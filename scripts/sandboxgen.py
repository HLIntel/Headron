#!/usr/bin/env python3
"""Generate the host sandbox a task contract needs, from config/agent-sandbox.json.

WHY (3.12.0). The runner refuses what it is asked about, and four sandbox rows are the HOST's job: home
directory, network, identity, resources. They were declared and printed UNOBSERVED, and whoever ran the
agent had to translate prose into flags. This writes the flags: the declaration becomes a command, so the
host that runs it provides exactly the rows the contract names, and nothing is left to a reading of prose.

  docker <contract> [--image IMG]   a `docker run` argv: no network, read-only root, only the worktree
                                    writable, non-root, all capabilities dropped, bounded cpu/memory/pids,
                                    the contract's wall clock as a hard timeout, and no credential variable
  macos  <contract>                 a sandbox-exec profile: deny by default, no network, no read of the
                                    home directory's secrets, writes only to the worktree and a temp dir

WHAT IT DOES NOT PROVE: that the host ran it. A generated command is a declaration until it runs; the
macOS profile is proven on this machine by atlas_guards_test (a home write and a connect must fail).
A network 'allowlist' is REFUSED: it needs an egress proxy, and a flag cannot provide one.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE.parent / "config" / "agent-sandbox.json"
UID = "10001:10001"


def _load(contract_path: str) -> tuple[dict, dict]:
    return json.loads(Path(contract_path).read_text(encoding="utf-8")), json.loads(CONFIG.read_text(encoding="utf-8"))


def _network(contract: dict) -> str:
    mode = str(contract.get("network") or "denied")
    if mode != "denied":
        raise SystemExit(f"REFUSED: network '{mode}' needs an egress proxy with an allowlist; a flag cannot provide one")
    return "none"


def docker_argv(contract: dict, config: dict, worktree: str, image: str) -> list[str]:
    rows = config["rows"]
    limits = rows["resources"]["container"]["limits"]
    wall = int((contract.get("budgets") or {}).get("wall_clock_seconds") or 900)
    argv = ["docker", "run", "--rm", "--network", _network(contract), "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m", "--user", UID, "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", str(limits["pids"]),
            "--memory", str(limits["memory"]), "--cpus", str(limits["cpus"]),
            "-v", f"{worktree}:/work:rw", "-w", "/work", "-e", "HOME=/tmp"]
    # docker passes no host variable unless asked; this asserts none of the credential names is asked for.
    assert not set(rows["home_directory"]["container"]["env_unset"]) & {a.split("=")[0] for a in argv}
    return [*argv, image, "timeout", str(wall)]


def macos_profile(contract: dict, worktree: str, home: str) -> str:
    _network(contract)
    secrets = [p.replace("$HOME", home) for p in
               json.loads(CONFIG.read_text(encoding="utf-8"))["rows"]["home_directory"]["container"]["mounts_forbidden"]
               if p != "$HOME"]
    real = os.path.realpath
    return "\n".join([
        "(version 1)", "(deny default)", "(allow process*)", "(allow sysctl-read)", "(allow mach-lookup)",
        "(allow file-read*)", *[f'(deny file-read* (subpath "{real(s)}"))' for s in secrets],
        f'(allow file-write* (subpath "{real(worktree)}") (subpath "/private/tmp") (subpath "/private/var/folders"))',
        '(allow file-write* (literal "/dev/null"))', "(deny network*)", ""])


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("docker", "macos"):
        print(__doc__.split("\n\n", 1)[0])
        print("usage: sandboxgen.py docker|macos <contract.json> [--image IMG] [--worktree PATH]")
        return 2
    contract, config = _load(argv[1])
    worktree = argv[argv.index("--worktree") + 1] if "--worktree" in argv else os.getcwd()
    if argv[0] == "docker":
        image = argv[argv.index("--image") + 1] if "--image" in argv else "python:3.12-slim"
        print(" ".join(docker_argv(contract, config, worktree, image)))
    else:
        print(macos_profile(contract, worktree, str(Path.home())))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
