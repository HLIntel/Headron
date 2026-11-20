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


def test_sensitive_names_in_any_case_and_common_shapes() -> None:
    # Lowercase spellings and the PAT / APIKEY / CREDENTIALS / AUTH shapes used to pass straight through.
    leaked = ["github_token", "openai_api_key", "GITLAB_PAT", "STRIPE_APIKEY", "GCP_CREDENTIALS", "NPM_AUTH"]
    leaked += ["ANTHROPIC_BASE_URL"]
    cleaned = isolation.isolated_environment({**dict.fromkeys(leaked, "v"), "EDITOR": "vi"}, allow_network=True)
    assert [k for k in leaked if k in cleaned] == []
    assert cleaned["EDITOR"] == "vi"


def test_denied_network_overrides_every_proxy_spelling() -> None:
    # An inherited upper-case proxy or a NO_PROXY exemption used to survive allow_network=False.
    ambient = {"HTTPS_PROXY": "http://real:8080", "ALL_PROXY": "socks5://real", "NO_PROXY": "*", "no_proxy": "*"}
    cleaned = isolation.isolated_environment(ambient, allow_network=False)
    assert {k: cleaned.get(k) for k in isolation.PROXY_VARS} == dict.fromkeys(
        isolation.PROXY_VARS, "http://127.0.0.1:0"
    )
    assert "NO_PROXY" not in cleaned and "no_proxy" not in cleaned

    caps = isolation.WorkerCapabilities(allow_network=False)
    probe = "import os, sys; print(*(os.environ.get(name) for name in sys.argv[1:]))"
    argv = [sys.executable, "-c", probe, "HTTPS_PROXY", "NO_PROXY"]
    done = isolation.run_isolated(argv, Path("."), caps, extra_env={"NO_PROXY": "*"})
    assert done.stdout.decode().split() == ["http://127.0.0.1:0", "None"]


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

    # extra_env cannot inject sensitive variables or disable network isolation
    leak_key = "AWS" + "_KEY"
    net_flag = "NO_" + "NETWORK"
    done_extra = isolation.run_isolated(
        [sys.executable, "-c", f"import os; print(os.environ.get('{leak_key}'), os.environ.get('{net_flag}'))"],
        Path("."),
        caps,
        extra_env={leak_key: "leak", net_flag: "0", "SAFE_VAR": "preserved"},
    )
    assert done_extra.returncode == 0
    assert "None 1" in done_extra.stdout.decode()


if __name__ == "__main__":
    test_isolated_environment_stripping()
    test_sensitive_names_in_any_case_and_common_shapes()
    test_denied_network_overrides_every_proxy_spelling()
    test_verify_command_capabilities()
    test_run_isolated_execution()
    print("isolation_test: PASS")
