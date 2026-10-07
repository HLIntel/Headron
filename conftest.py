"""A bare `pytest` at the root refuses: this repository has no pytest suite.

Without this, `python3 -m pytest` collects the planted failing tests under benchmarks/agent/
and reports them as broken code. They are agentbench fixtures (atlas.yaml/planted_failure_paths).
A path given on the command line still runs, so one fixture can be checked on its own.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent


def pytest_configure(config: pytest.Config) -> None:
    # config.args holds positional paths only; option values such as `-p name` never reach it.
    if any(Path(config.invocation_params.dir, a).resolve() != ROOT for a in config.args):
        return
    raise pytest.UsageError(
        "no pytest suite here: the contract runs `python3 scripts/verify.py`; "
        "benchmarks/agent/ holds planted failing tests for `python3 scripts/agentbench.py`"
    )
