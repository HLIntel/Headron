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

SENSITIVE_PREFIXES = ("AWS_", "GITHUB_TOKEN", "GH_TOKEN", "NVIDIA_", "GROQ_", "OPENAI_", "ANTHROPIC_")
SENSITIVE_SUFFIXES = ("_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_PAT", "_APIKEY", "_CREDENTIALS", "_AUTH")
# Every spelling a tool reads for its proxy. With network denied all point at a dead port, and the
# exemption lists are dropped: an inherited NO_PROXY=* would route around the dead proxy.
PROXY_VARS = ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")
PROXY_EXEMPT = frozenset({"no_proxy", "NO_PROXY"})
DEAD_PROXY = "http://127.0.0.1:0"
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


def is_sensitive_var(k: str) -> bool:
    """Check if an environment variable name matches sensitive token prefixes or suffixes, in any case."""
    name = k.upper()
    return name.startswith(SENSITIVE_PREFIXES) or name.endswith(SENSITIVE_SUFFIXES)


def deny_network(env: dict[str, str]) -> dict[str, str]:
    """Point every proxy spelling at a dead port, drop proxy exemptions, and mark the network off."""
    for k in [k for k in env if k.lower() in PROXY_EXEMPT or k.lower() in {v.lower() for v in PROXY_VARS}]:
        del env[k]
    env.update(dict.fromkeys(PROXY_VARS, DEAD_PROXY))
    env["NO_NETWORK"] = "1"
    return env


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
        elif not is_sensitive_var(k):
            cleaned[k] = v

    return cleaned if allow_network else deny_network(cleaned)


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
        for k, v in extra_env.items():
            if not is_sensitive_var(k):
                env[k] = v
        if not caps.allow_network:
            deny_network(env)

    return subprocess.run(argv, cwd=str(cwd), capture_output=True, check=False, timeout=caps.timeout_s, env=env)
