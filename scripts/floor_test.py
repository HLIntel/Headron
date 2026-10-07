#!/usr/bin/env python3
"""Regression case for the interpreter floor: below requires-python the primitives refuse as NOT RUN, never crash."""

from __future__ import annotations

import subprocess
import sys


def below_floor_case(module) -> None:
    """A bare `python3` resolving to 3.9 died on `import tomllib` in five sessions and read as a broken contract."""
    plant = "import sys; sys.modules['tomllib'] = None; sys.path.insert(0, 'scripts'); import atlascore"
    done = subprocess.run(
        [sys.executable, "-c", plant], cwd=module.ROOT, capture_output=True, text=True, timeout=60, check=False
    )
    if done.returncode != 2 or "NOT RUN" not in done.stderr or ">=3.11" not in done.stderr:
        raise SystemExit(f"FAIL interpreter floor: rc={done.returncode} stderr={done.stderr[-300:]!r}")
    if "Traceback" in done.stderr:
        raise SystemExit("FAIL interpreter floor: the refusal still printed a traceback")
    module.CASES.append(
        (
            "an interpreter without tomllib makes atlascore exit 2 with NOT RUN and the 3.11 floor",
            "a bare python3 resolving to 3.9 read as ModuleNotFoundError in the contract",
        )
    )
    print("  ok    an interpreter below the floor is NOT RUN, not a crash")


def run(module) -> None:
    below_floor_case(module)
