#!/usr/bin/env python3
"""Mutation tests for the contract harness.

WHY: `atlas.py check` is the only thing standing between this repository and
silent drift, and until now nothing tested IT. A guard that is never mutation-
tested is decoration: when it works it prints nothing, and so does a broken one.

Every case below names the WRONG IMPLEMENTATION it kills, and each one plants a
real defect on disk, runs the real check, and restores the file. The case COUNT
is asserted at the end, because a harness can print "all pass" over cases that
never ran.

    python scripts/atlas_test.py
"""
from __future__ import annotations

import contextlib
import io
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import atlas

CASES: list[tuple[str, str]] = []


def run_check() -> tuple[int, str]:
    atlas.atlas.cache_clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = atlas.check()
    return rc, buf.getvalue()


def case(name: str, kills: str, expect_fail: bool, needle: str | None = None) -> None:
    rc, out = run_check()
    failed = rc != 0
    if failed != expect_fail:
        raise SystemExit(f"FAIL {name}\n  kills: {kills}\n  rc={rc}, expected {'non-zero' if expect_fail else '0'}\n{out[:800]}")
    if needle and needle not in out:
        raise SystemExit(f"FAIL {name}\n  kills: {kills}\n  expected {needle!r} in output\n{out[:800]}")
    CASES.append((name, kills))
    print(f"  ok    {name}")


@contextlib.contextmanager
def mutated(rel: str, transform):
    """Plant a defect in a tracked file, then restore it byte for byte."""
    path = ROOT / rel
    backup = path.read_bytes()
    try:
        planted = transform(backup.decode("utf-8"))
        # A MUTATION THAT DID NOT MUTATE. str.replace with no match returns the
        # string unchanged and says nothing, so the case then "passes" against a
        # pristine file — a green harness over a defect that was never planted.
        if planted == backup.decode("utf-8"):
            raise SystemExit(f"MUTATION DID NOT APPLY to {rel}: the pattern no longer matches this file")
        path.write_text(planted, encoding="utf-8")
        yield
    finally:
        path.write_bytes(backup)
        atlas.atlas.cache_clear()


def main() -> int:
    print("atlas contract — mutation tests")

    # 0. SPECIFICITY FIRST. A guard that fires on the real tree gets silenced,
    #    so the unmutated repository must pass before any defect is planted.
    case("a clean tree passes", "a check so strict it fires on correct content", False, "contract")

    # 1. GENERATED-BLOCK DRIFT — the reviewer's risk: a doc edited by hand.
    with mutated("MODEL.md", lambda t: t.replace("source_change", "source_changed", 1)):
        case("a hand-edited generated block FAILS", "a generator nobody checks the output of", True, "generated block")

    # 2. The generator must be the thing that repairs it, and be idempotent.
    with mutated("MODEL.md", lambda t: t.replace("source_change", "source_changed", 1)):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            atlas.index(write=True)
        case("index --write repairs the drift it detects", "a check that reports drift nothing can fix", False)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        atlas.index(write=True)
    assert "wrote" not in buf.getvalue(), "index --write is not idempotent: a second run rewrote a file"
    CASES.append(("index --write is idempotent", "a generator that rewrites on every run, so drift is invisible in diffs"))
    print("  ok    index --write is idempotent")

    # 3. VERSION SKEW across the six declared sites.
    with mutated("VERSION", lambda t: "0.0.1\n"):
        case("a version skew FAILS", "six files free to disagree about which contract this is", True, "version mismatch")

    # 4. MANIFEST SCHEMA — the reviewer's 'policy says it, nothing proves it'.
    with mutated("languages/python/tools.yaml", lambda t: t.replace("policy:", "policies:", 1)):
        case("a manifest missing a top-level key FAILS", "an existence check passing a manifest with no policy", True, "manifest missing key")
    with mutated("languages/python/tools.yaml", lambda t: t.replace("language: python", "language: pyhton", 1)):
        case("a manifest whose identity disagrees FAILS", "a rust manifest copied into the python pack", True, "identity mismatch")
    with mutated("languages/python/tools.yaml", lambda t: t.replace("  blockers:", "  blokers:", 1)):
        case("a manifest missing a policy key FAILS", "a manifest that declares no blockers and still gates a change", True, "policy missing")

    # 5. LABEL ROUTING — a route printing a label nobody created.
    with mutated("config/github-labels.json", lambda t: t.replace('"lang/python"', '"lang/pythonx"', 1)):
        case("a route whose label is not in the catalog FAILS", "atlas printing lang/quantum/qsharp, a label that never existed", True, "route label not in")

    # 6. A ROUTE WITH NO PACK.
    with mutated("atlas.yaml", lambda t: t.replace("  '.py': python", "  '.py': pythonx", 1)):
        case("a route pointing at a missing pack FAILS", "an artifact_routes entry with nothing behind it", True)

    # 7. ROUTE EDGE CASES — the reviewer's 'weird path'. Behaviour, not I/O.
    assert atlas.route_for("a/b/c.py") == "python", "extension routing broke"
    assert atlas.route_for("Makefile") is None, "a file with NO extension must not route"
    assert atlas.route_for("README") is None, "an extensionless name must not route"
    assert atlas.route_for(".gitignore") is None, "a dotfile's suffix is empty, not a route"
    assert atlas.route_for("x.PY") == "python", "an uppercase extension must route (case is a rendering)"
    assert atlas.route_for("/tmp/elsewhere/languages/go/x.txt") is None, "a path OUTSIDE the repo must not route on a matching segment"
    assert atlas.route_for(str(ROOT / "languages/go/README.md")) == "go", "a pack's own guide must route to that pack"
    assert atlas.route_for(str(ROOT / "languages/quantum/qsharp/OPERATING.md")) == "quantum/qsharp", "a nested pack must route to the deepest match"
    assert atlas.route_for("x.unheard-of") is None, "an unknown extension must not route"
    assert atlas.label_for("quantum/qsharp") == "lang/qsharp", "a nested route's label is its basename"
    CASES.append(("route_for: 10 edge cases", "suffix-only routing that claimed unrelated paths and refused its own guides"))
    print("  ok    route_for: 10 edge cases (no extension, case, outside-repo, nested pack)")

    # 8. THE ENTRY POINT the reviewer called brittle: it must work from anywhere.
    out = shutil.which("python3")
    assert out, "python3 not on PATH"
    import subprocess
    for cwd in (ROOT, ROOT / "scripts", Path("/tmp")):
        r = subprocess.run([out, str(ROOT / "scripts" / "check_contract.py")], cwd=cwd, capture_output=True, text=True)
        assert r.returncode == 0, f"check_contract.py failed from {cwd}: {r.stderr[-300:]}"
    CASES.append(("check_contract.py runs from any working directory", "an entry point that only works from scripts/"))
    print("  ok    check_contract.py runs from repo root, scripts/ and /tmp")

    # The number is MEASURED, not intended: the first draft said 14 against 12 real
    # cases, and an expectation nobody counted fails every run for the wrong reason.
    expected = 12
    if len(CASES) != expected:
        raise SystemExit(f"CASE COUNT MOVED: {len(CASES)} ran, {expected} expected — a harness that silently skips cases prints a full pass")
    print(f"atlas tests: {len(CASES)}/{expected} pass")
    print("BLIND SPOT: these test the CONTRACT, not the truth of a manifest's tool names —")
    print("            that is what provenance.verify and a codespace are for.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
