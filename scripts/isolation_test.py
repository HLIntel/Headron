"""Tests for worker capability isolation (scripts/isolation.py).

proves: sensitive ambient keys are removed from the worker environment; safe execution variables
  are preserved; network commands are refused under default isolation; commands within capabilities run
does_not_prove: host OS kernel isolation guarantees
closed_by: isolation_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import isolation


def test_isolated_environment_stripping() -> None:
    ambient = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/home/user",
        "AWS_SECRET_ACCESS_KEY": "secret-value",
        "GITHUB_TOKEN": "ghp_token",
        "OPENAI_API_KEY": "sk-key",
        "DATABASE_PASSWORD": "db-pw",
        "SAFE_CUSTOM_VAR": "custom-val",
    }
    cleaned = isolation.isolated_environment(ambient, allow_network=False)
    assert "PATH" in cleaned
    assert "HOME" in cleaned
    assert "SAFE_CUSTOM_VAR" in cleaned
    assert "AWS_SECRET_ACCESS_KEY" not in cleaned
    assert "GITHUB_TOKEN" not in cleaned
    assert "OPENAI_API_KEY" not in cleaned
    assert "DATABASE_PASSWORD" not in cleaned
    assert cleaned.get("NO_NETWORK") == "1"
    assert cleaned.get("http_proxy") == "http://127.0.0.1:0"


def test_verify_command_capabilities() -> None:
    caps_no_net = isolation.WorkerCapabilities(allow_network=False)
    assert isolation.verify_command_capabilities(["curl", "https://example.com"], caps_no_net) is not None
    assert isolation.verify_command_capabilities(["wget", "https://example.com"], caps_no_net) is not None
    assert isolation.verify_command_capabilities(["python", "script.py"], caps_no_net) is None

    caps_net = isolation.WorkerCapabilities(allow_network=True)
    assert isolation.verify_command_capabilities(["curl", "https://example.com"], caps_net) is None


def test_run_isolated_execution() -> None:
    caps = isolation.WorkerCapabilities(allow_network=False)
    done = isolation.run_isolated([sys.executable, "-c", "print('isolated_ok')"], Path("."), caps)
    assert done.returncode == 0
    assert "isolated_ok" in done.stdout.decode()

    # Network command raises CapabilityViolation
    try:
        isolation.run_isolated(["curl", "http://example.invalid"], Path("."), caps)
        raise AssertionError("curl should have been refused by worker isolation")
    except isolation.CapabilityViolation:
        pass


if __name__ == "__main__":
    test_isolated_environment_stripping()
    test_verify_command_capabilities()
    test_run_isolated_execution()
    print("isolation_test: PASS")
