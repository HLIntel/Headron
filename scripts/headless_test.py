#!/usr/bin/env python3
"""Mutation tests for the headless runner.

Each check asserts one fact about how a run is labelled, refused or handed to the host. Every check
must hold; the check count is asserted at the end.

    python scripts/headless_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import headless  # noqa: E402

CONTRACT = str(ROOT / "tools" / "agent-task.example.headron")

sandboxless_refused, _ = headless.plan("none", False)
sandboxless_label = headless.plan("none", True)[1]
refused_record, refused_code = headless.run(CONTRACT, "none", False, False)
docker_record, docker_code = headless.run(CONTRACT, "docker", False, False)
none_record, _ = headless.run(CONTRACT, "none", True, False)

# (name, kills, holds)
CHECKS: list[tuple[str, str, bool]] = [
    (
        "a sandboxless run is refused without the explicit opt-in",
        "a default that runs with no isolation",
        not sandboxless_refused,
    ),
    (
        "a sandboxless run is labelled UNSANDBOXED, never as sandboxed",
        "an unsandboxed run that reads as sandboxed",
        sandboxless_label.startswith("UNSANDBOXED"),
    ),
    (
        "an unknown sandbox is refused",
        "a typo that silently falls back to a mode",
        headless.plan("sandboxish", True)[0] is False,
    ),
    (
        "a refused run exits 2 and records no outcome",
        "a refusal that reports a run",
        refused_code == 2 and "ran" not in refused_record and "outcome" not in refused_record,
    ),
    (
        "a host-sandboxed run is never claimed as run by this script",
        "a docker run reported as having executed here",
        docker_code == 3 and docker_record["ran"] is False and "command" in docker_record,
    ),
    (
        "the host command names the docker run it was built for",
        "a sandbox command that is not a docker run",
        docker_record["command"].startswith("docker run"),
    ),
    (
        "an executed sandboxless run carries the UNSANDBOXED label in its record",
        "an executed run whose isolation is missing",
        none_record["ran"] is True and none_record["isolation"].startswith("UNSANDBOXED"),
    ),
]


def test_every_check_holds() -> None:
    """Every case holds, and the case count is pinned so a dropped case is noticed."""
    for name, _kills, holds in CHECKS:
        assert holds, name
    assert len(CHECKS) == 7, len(CHECKS)


if __name__ == "__main__":
    test_every_check_holds()
    print(f"{len(CHECKS)} cases ok")
