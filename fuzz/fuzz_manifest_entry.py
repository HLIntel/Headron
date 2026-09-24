#!/usr/bin/env python3
"""Coverage-guided fuzz target for the manifest entry grammar and the router.

WHAT IT IS FOR. The entry grammar decides how every declared tool in every language pack is
classified, and the router decides which pack answers for a file. Both take arbitrary text from a
document a human wrote, and both are consulted by instruments whose output is trusted. A seeded
property sweep already covers them in `scripts/atlas_test.py`; this is the coverage-guided version,
which explores inputs a generator picks rather than inputs a person imagined.

IT RUNS TWO WAYS ON PURPOSE:
  * under atheris (ClusterFuzzLite, CI fuzzing) — `TestOneInput` is the libFuzzer entry point;
  * on its own, with a deterministic corpus — `python fuzz/fuzz_manifest_entry.py`, so the target
    is EXERCISED even where atheris is not installed. A fuzz target nobody can run is a skeleton,
    and this repository refuses those; the corpus run is what keeps it honest between campaigns.

THE INVARIANTS IT ASSERTS, each one a way the classifier could be wrong:
  1. `entry_kind` always returns one of the declared kinds, or `invalid`. Never an exception.
  2. A `command` entry yields at least one PATH name; every other kind yields none. These two
     functions disagreed on "" and "|" before the property sweep found it.
  3. No produced binary name contains a space — a name with a space cannot be resolved.
  4. Anything the grammar ACCEPTS must be classifiable: the pattern and the classifier cannot
     disagree about what a legal entry is.
  5. `route_for` never raises and never invents a route that is not a declared target.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from atlascore import route_for, route_targets  # noqa: E402
from packmanifest import entry_binaries, entry_kind, manifest_pattern  # noqa: E402

KINDS = {"command", "lib", "builtin", "concept", "none", "invalid"}


def check(text: str) -> None:
    """Every invariant, on one input. Raises AssertionError when one fails."""
    kind = entry_kind(text)
    assert kind in KINDS, f"{text!r}: unknown kind {kind!r}"

    binaries = entry_binaries(text)
    assert (kind == "command") == bool(binaries), f"{text!r}: kind {kind} against {binaries}"
    assert all(" " not in name for name in binaries), f"{text!r}: a binary name contains a space"

    if manifest_pattern("entry").fullmatch(text):
        assert kind != "invalid", f"{text!r}: the grammar accepts what the classifier cannot classify"

    route = route_for(text)
    assert route is None or route in route_targets(), f"{text!r}: invented the route {route!r}"


def TestOneInput(data: bytes) -> None:  # noqa: N802  (libFuzzer's required entry-point name)
    check(data.decode("utf-8", errors="replace"))


def corpus() -> list[str]:
    """A deterministic corpus: every shape the grammar distinguishes, plus the two that broke it."""
    return [
        "", "|", "none", "go test", "lldb|gdb", "cargo miri", "lib:hypothesis",
        "builtin:EXPLAIN ANALYZE", "concept:schema-or-ABI boundary", "ruff format",
        "node --inspect", "dotnet add package", "psql|sqlite3", "a" * 200,
        "lib:", "builtin:", "concept:", "|||", " ", "\t", "\n", "()", "a b(c)",
        "languages/python/README.md", "scripts/atlas.py", "/etc/passwd", "../../escape.py",
        "x.py", "x.PY", "Makefile", ".gitignore", "x.unheard-of", "\u0000", "é", "🙂",
    ]


def main() -> int:
    try:
        import atheris
    except ImportError:
        for text in corpus():
            check(text)
        print(f"fuzz_manifest_entry: {len(corpus())} corpus inputs held every invariant "
              "(atheris absent — run under ClusterFuzzLite for the coverage-guided campaign)")
        return 0
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
    return 0


if __name__ == "__main__":
    sys.exit(main())
