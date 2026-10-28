"""Exercise example runner verdicts for unconfigured launchers and real failures."""

import subprocess
from unittest.mock import patch

import exrun


def run(module) -> None:
    path = module.ROOT / "examples/lean4/bounded.lean"
    for command, error, expected in (
        ("lean", "error: no default toolchain configured. run elan default stable", "SKIP"),
        ("lean", "error: invalid theorem", "FAIL"),
        ("other", "error: no default toolchain configured.", "FAIL"),
    ):
        result = subprocess.CompletedProcess([command], 1, "", error)
        with (
            patch.object(exrun.shutil, "which", return_value="/installed"),
            patch.object(exrun.subprocess, "run", return_value=result),
        ):
            verdict, _ = exrun.run_one(path, [[command]])
        if verdict != expected:
            raise SystemExit(f"example launcher: {command} {error!r} -> {verdict}, expected {expected}")
    module.CASES.append(
        (
            "an unconfigured Lean launcher skips while a compiler failure is refused",
            "a launcher mistaken for a compiler",
        )
    )
