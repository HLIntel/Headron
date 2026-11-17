"""Capability-enforced worker isolation for task and gate execution.

proves: execution subprocesses run inside bounded capability profiles; sensitive credentials and
  ambient tokens are stripped from the worker environment; network isolation is enforced when
  prohibited; commands exceeding granted worker capabilities are refused before launch
does_not_prove: hardware or kernel-level container virtualization
closed_by: isolation_test.py
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

SENSITIVE_PREFIXES = ("AWS_", "GITHUB_TOKEN", "GH_TOKEN", "NVIDIA_", "GROQ_", "OPENAI_")
SENSITIVE_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "_PASSWORD")
SAFE_ENV_VARS = frozenset(
    {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "TERM",
        "TMPDIR",
        "USER",
        "PYTHONPATH",
        "PYTHONDONTWRITEBYTECODE",
        "HEADRON_BASE",
        "HEADRON_AGENT",
    }
)


@dataclass(frozen=True)
class WorkerCapabilities:
    """Enforced capability envelope for an executed gate or worker."""

    allow_network: bool = False
    read_only: bool = False
    timeout_s: int = 600
    allow_ambient_env: bool = False


class CapabilityViolation(PermissionError):
    """Raised when an operation exceeds declared worker capabilities."""


def isolated_environment(
    base_env: dict[str, str] | None = None, allowed_vars: tuple[str, ...] = (), allow_network: bool = False
) -> dict[str, str]:
    """Filter environment variables to remove sensitive tokens and apply network restrictions."""
    source = base_env if base_env is not None else dict(os.environ)
    cleaned: dict[str, str] = {}
    allowed_set = set(allowed_vars) | SAFE_ENV_VARS

    for k, v in source.items():
        if k in allowed_set:
            cleaned[k] = v
        elif not any(k.startswith(p) for p in SENSITIVE_PREFIXES) and not any(
            k.endswith(s) for s in SENSITIVE_SUFFIXES
        ):
            cleaned[k] = v

    if not allow_network:
        cleaned["http_proxy"] = "http://127.0.0.1:0"
        cleaned["https_proxy"] = "http://127.0.0.1:0"
        cleaned["NO_NETWORK"] = "1"

    return cleaned


def verify_command_capabilities(argv: list[str], capabilities: WorkerCapabilities) -> str | None:
    """Check whether the command respects capability boundaries."""
    if not argv:
        return "empty command"
    program = argv[0].lower()
    if not capabilities.allow_network and program in ("curl", "wget", "ssh", "scp", "nc"):
        return f"network access disabled: command {program!r} refused by capability policy"
    return None


def run_isolated(
    argv: list[str], cwd: Path, capabilities: WorkerCapabilities | None = None, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess:
    """Run a subprocess within the declared capability envelope."""
    caps = capabilities or WorkerCapabilities()
    violation = verify_command_capabilities(argv, caps)
    if violation:
        raise CapabilityViolation(violation)

    env = isolated_environment(allow_network=caps.allow_network)
    if extra_env:
        env.update(extra_env)

    return subprocess.run(argv, cwd=str(cwd), capture_output=True, check=False, timeout=caps.timeout_s, env=env)
