#!/usr/bin/env python3
"""The toolchain invariant: every typed pin equals the atlas.yaml/toolchain declaration.

proves: a toolchain version typed in a workflow, the replay shell, or a derived tool is the
declared one, so an upgrade is one declaration edit plus a regenerate and a stale pin cannot land.
does_not_prove: that the pinned tool runs correctly on every host; each gate still checks its own.
closed_by: atlas_test's invariant cases and `headron check`.
"""

from __future__ import annotations

import re

from atlascore import ROOT, rel, text_of, toolchain


def _workflows() -> list:
    """The workflow files, found here so this invariant stays outside the module import cycle."""
    return sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def _inv_toolchain_pins_agree() -> str | None:
    """toolchain_pins_agree — every typed toolchain pin equals the atlas.yaml/toolchain declaration.

    THE OWNER PATTERN (see identity): a value declared once, derived in the Python tools, and CHECKED
    in the places that must stay literal — GitHub Actions yaml and the replay shell cannot import this
    package, so their pins are typed and this check refuses their drift. An upgrade is: edit the
    declaration, run the rewrite where a generator writes it, and this names any site left behind."""
    pins = toolchain()
    py, uv_pin = pins.get("python"), pins.get("uv")

    def typed_version(line: str) -> str | None:
        found = re.search(r'"(\d+(?:\.\d+)+)"', line)
        return found.group(1) if found else None

    for workflow in _workflows():
        for n, line in enumerate(text_of(workflow).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("python-version:") and typed_version(stripped) != py:
                return f"{rel(workflow)}:{n} pins python {typed_version(stripped)!r}, not the declared {py!r}"
            if "uv==" in line:
                found = re.search(r"uv==([\d.]+)", line)
                if found and found.group(1) != uv_pin:
                    return f"{rel(workflow)}:{n} pins uv {found.group(1)!r}, not the declared {uv_pin!r}"

    shell = ROOT / ".github" / "ci-local.sh"
    if shell.is_file():
        for n, line in enumerate(text_of(shell).splitlines(), 1):
            found = re.search(r"uv run --frozen --python (\d+(?:\.\d+)*)", line)
            if found and found.group(1) != py:
                return f"{rel(shell)}:{n} replays python {found.group(1)!r}, not the declared {py!r}"

    # the derived sites read the declaration — a generator that stopped reading it is named here
    pipeline = text_of(ROOT / "scripts" / "cipipeline.py")
    if "toolchain()" not in pipeline:
        return "scripts/cipipeline.py no longer derives its pins from atlas.yaml/toolchain"
    return None
