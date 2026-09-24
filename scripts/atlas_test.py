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
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import atlas
import packmanifest

_VERSION = (ROOT / "VERSION").read_text().strip()  # the ONE declaration; never typed into a fixture

CASES: list[tuple[str, str]] = []


def run_check() -> tuple[int, str]:
    atlas.atlas.cache_clear()
    packmanifest.reset_caches()
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
        packmanifest.reset_caches()


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

    # 4b. THE MANIFEST GRAMMAR (1.3.0) — prose in a field an instrument has to evaluate.
    with mutated("languages/python/tools.yaml", lambda s: s.replace("  test: pytest", "  test: Test (stdlib)", 1)):
        case("a prose entry in a tool field FAILS", "49% of declared entries sitting in binary fields, "
             "so no instrument could evaluate them and the packs read as complete", True, "does not match the declared form")
    with mutated("languages/python/tools.yaml", lambda s: s.replace("  warnings: non_blocking", "  warnings: sometimes", 1)):
        case("a value outside a declared enum FAILS", "a hand-written validator that reads `required` and "
             "silently ignores every other keyword", True, "is not one of")
    # The anchor is DERIVED from the schema, never typed: a literal `"const": 1` stopped matching
    # the moment the manifest format moved to 2, and the harness refused — correctly — rather than
    # planting nothing. A fixture that names a version has to be re-typed at every bump.
    _format = json.loads((ROOT / atlas.MANIFEST_SCHEMA).read_text())["properties"]["schema"]["const"]
    _anchor = f'"const": {_format},'
    with mutated("tools/tools.schema.json", lambda s, a=_anchor: s.replace(a, a + ' "multipleOf": 7,', 1)):
        case("a schema keyword the harness cannot check FAILS LOUDLY", "a validator that skips an unknown "
             "keyword and prints a clean pass over an unchecked constraint", True, "keyword not implemented")

    # 4c. THE INSTRUMENT ROSTER — a limit with no owner, and a script nobody announces.
    with mutated("atlas.yaml", lambda s: s.replace(
            "    closed_by: '`atlas.py check`, which it calls'", "    closed_by: ''", 1)):
        case("an instrument whose limit has no closer FAILS", "a table of blind spots that ages into a "
             "table of defects because no row names who closes it", True, "limit with no owner")
    with mutated("atlas.yaml", lambda s: s.replace("    script: scripts/ghaudit.py", "    script: scripts/gone.py", 1)):
        case("an instrument naming a missing file FAILS", "a roster that describes an instrument the tree "
             "does not have", True, "does not exist")

    # 4d. A GENERATED FILE, not only a generated block.
    with mutated("llms.txt", lambda s: s.replace("# Code-Development", "# Code-Developmnt", 1)):
        case("a hand-edited generated file FAILS", "an agent-facing index maintained by hand, which narrows "
             "the moment something is added beside it", True, "generated file drifted")

    # 4e. DATES (1.3.1) — a claim stamped with a calendar date instead of a contract version.
    # The date is ASSEMBLED, never written: a literal here would be a dated claim in a tracked
    # file, so the guard would fire on its own test fixture and the clean sweep would fail.
    planted_date = "-".join(("2026", "01", "02"))
    with mutated("docs/VERIFY.md", lambda s: s.replace("# ", f"# Measured {planted_date} — ", 1)):
        case("a calendar date in a tracked file FAILS", "a measurement stamped with when somebody typed, "
             "which no later reader can re-check against anything", True, "calendar date in")
    with mutated("languages/python/tools.yaml", lambda s: s.replace("  since: '0.9.5'", "  since: 'recently'", 1)):
        case("a provenance version that is not a version FAILS", "provenance that reads as measured when it "
             "was recalled", True, "does not match the declared form")

    # 4f. HTML LINKS (2.1.0) — the README header is HTML, and none of it was checked.
    with mutated("README.md", lambda s: s.replace('src="docs/assets/', 'src="docs/assets/gone-', 1)):
        case("a broken HTML src FAILS", "a Markdown link checker reporting a clean pass over every anchor "
             "and image in the page a reader sees first", True, "broken local link")

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

    # 7b. PROPERTY SWEEP over the router and the manifest grammar (2.2.0).
    #     Not a fuzzer integration — Scorecard looks for OSS-Fuzz or ClusterFuzzLite and will not
    #     detect this, which docs/CERTIFICATION.md says plainly. It is the proportionate instrument
    #     for a local CLI: a seeded generator, so a failure is reproducible from the seed alone,
    #     and NO new dependency, so it runs everywhere the contract runs.
    import random as _random
    import string as _string

    import packmanifest as _pm

    rng = _random.Random(20260924)
    alphabet = _string.ascii_letters + _string.digits + "._-|/ ()+:*?\\\t"
    sweep = 0
    for _ in range(4000):
        candidate = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 24)))
        route = atlas.route_for(candidate)            # must never raise, whatever it is handed
        assert route is None or route in atlas.route_targets(), f"invented a route for {candidate!r}"
        kind = _pm.entry_kind(candidate)
        assert kind in {"command", "lib", "builtin", "concept", "none", "invalid"}, kind
        binaries = _pm.entry_binaries(candidate)
        assert (kind == "command") == bool(binaries), f"{candidate!r}: kind {kind} against {binaries}"
        assert all(" " not in b for b in binaries), f"{candidate!r} produced a binary with a space"
        assert kind != "invalid" or not _pm.manifest_pattern("entry").fullmatch(candidate), \
            f"{candidate!r} is invalid yet the grammar accepts it"
        if _pm.manifest_pattern("entry").fullmatch(candidate):
            # Anything the grammar ACCEPTS must be classifiable and, if a command, runnable-shaped.
            assert kind != "none" or candidate == "none", candidate
            assert not (kind == "command" and ("(" in candidate.split(" ", 1)[0])), candidate
        sweep += 1
    assert sweep == 4000, sweep
    CASES.append(("property sweep: 4000 generated inputs over the router and the entry grammar",
                  "a router that raises on a hostile path, and a grammar that accepts what nothing "
                  "can classify"))
    print("  ok    property sweep: 4000 seeded inputs, router and entry grammar total")

    # 8. HARD INVARIANTS — every name owned, and each check kills a real defect.
    violations, enforced, declared = atlas.invariants()
    assert not violations, f"invariants unowned or violated on a clean tree: {violations}"
    assert len(enforced) + len(declared) == len(atlas.atlas().get("hard_invariants")), "an invariant is neither enforced nor declared"
    with mutated("atlas.yaml", lambda t: t.replace("  - ci_enforces_contract\n", "  - ci_enforces_contract\n  - invented_invariant\n", 1)):
        case("an invariant with no owner FAILS", "a list of promises that accrues authority from being written down", True, "neither checked nor declared")
    with mutated(".github/workflows/atlas-ci.yml", lambda t: t.replace("python scripts/atlas.py check", "true", 1)):
        case("CI not running the contract FAILS ci_enforces_contract", "the invariant that says CI enforces, asserted by nothing", True, "ci_enforces_contract")
    with mutated("languages/python/tools.yaml", lambda t: t.replace("compiler_or_runtime: python3", "compiler_or_runtime:", 1)):
        case("a manifest naming no runtime FAILS native_language_tools_are_authoritative", "'native tools are authoritative' with no native tool named", True, "native_language_tools")

    # 8b. EVERY PROMOTED INVARIANT, ONE PLANTED DEFECT EACH (1.1.0).
    # A check that cannot fail is worse than a declaration: it reads as coverage.
    # Each row is (file, find, replace, invariant name, the defect it kills).
    promoted = [
        (".github/workflows/atlas-ci.yml", "    timeout-minutes: 10", "    # no timeout",
         "explicit_deadlines", "a CI job that hangs until GitHub kills it"),
        (".github/CODEOWNERS", "* @ApianSoftware", "# no default owner",
         "auditable_changes", "new paths landing with no reviewer"),
        (".github/pull_request_template.md", "## Verification", "## Vibes",
         "goal_acceptance_is_explicit", "a PR that never states what would prove the goal met"),
        # Indent the changelog LINE: the version string still appears in the file, so
        # the version-sync check stays satisfied and only this invariant can fire.
        #
        # THE VERSION IS DERIVED, NEVER TYPED. This fixture read "1.1.0" literally, so the moment
        # VERSION was bumped to 1.2.0 the mutation indented a line the check no longer looks at:
        # the case went green while planting nothing, and a silently-passing mutation test is worth
        # less than no test, because it is believed. One number, one declaration — VERSION owns it.
        ("docs/VERSIONING.md", f"\n{_VERSION} ", f"\n {_VERSION} ",
         "rollback_high_impact", "a released version with no changelog line to revert to"),
        ("languages/python/tools.yaml", "  avoid_by_default:\n  - duplicate_linters\n  - unbounded_async_tasks", "  avoid_by_default: []",
         "tool_surfaces_are_bounded", "a manifest that names nothing to avoid, so the surface is everything"),
        (".vscode/mcp.json.example", '"semgrep": {', '"exfiltrator": {',
         "mcp_is_task_scoped", "shipping an MCP server no published profile names"),
        # The word appears twice; replacing one leaves the check satisfied, which is
        # itself the lesson — a single-occurrence mutation proves nothing about a
        # check that greps. Replace BOTH.
        ("patterns/BOUNDARY-BREAKAGE.md", "timeout", "deadline",
         "production_boundaries_are_contracts", "a boundary doc that never mentions timeouts", -1),
        ("config/github-labels.json", '"namespaces"', '"namespaces"  ,,',
         "schema_first", "a machine-read file that no longer parses"),
    ]
    for row in promoted:
        rel_path, find, repl, invariant, kills = row[:5]
        count = row[5] if len(row) > 5 else 1
        with mutated(rel_path, lambda s, f=find, r=repl, c=count: s.replace(f, r, c) if c > 0 else s.replace(f, r)):
            case(f"{invariant} FAILS when its property is broken", kills, True, invariant)

    # SPECIFICITY, asserted once for the whole set: the clean tree satisfies all 25.
    violations, enforced, declared = atlas.invariants()
    assert not violations and len(enforced) == 25 and not declared, \
        f"clean tree: {len(enforced)} enforced, {len(declared)} declared, violations={violations}"
    CASES.append(("all 25 invariants pass on a clean tree", "checks so loose or so strict they cannot be trusted"))
    print("  ok    all 25 invariants enforced and satisfied on a clean tree")

    # 9. THE ENTRY POINT the reviewer called brittle: it must work from anywhere.
    out = shutil.which("python3")
    assert out, "python3 not on PATH"
    for cwd in (ROOT, ROOT / "scripts", Path("/tmp")):
        r = subprocess.run([out, str(ROOT / "scripts" / "check_contract.py")], cwd=cwd, capture_output=True, text=True, check=False)
        assert r.returncode == 0, f"check_contract.py failed from {cwd}: {r.stderr[-300:]}"
    CASES.append(("check_contract.py runs from any working directory", "an entry point that only works from scripts/"))
    print("  ok    check_contract.py runs from repo root, scripts/ and /tmp")

    # 9a. THE ENVIRONMENT DOCTOR — it must answer for every declared instrument, not a copy of
    #     the roster. A second list would narrow the moment an instrument is added beside it.
    import doctor as _doctor
    rows = _doctor.findings()
    declared = atlas.atlas().get("instruments") or {}
    instrument_row = next(r for r in rows if r["capability"] == "instrument files")
    assert instrument_row["measured"].endswith(f"/{len(declared)} present"), \
        f"doctor counts {instrument_row['measured']} against {len(declared)} declared instruments"
    assert [r for r in rows if r["required"]], "doctor marks nothing as required"
    assert all(r["costs_if_absent"] for r in rows), "a doctor row must say what its absence costs"
    CASES.append(("doctor answers for every declared instrument",
                  "a second roster of instruments that narrows silently beside the first"))
    print("  ok    doctor: every declared instrument answered for, every row states its cost")

    # 9b. AN INDEPENDENT IMPLEMENTATION, where one is installed. The risk in a hand-written
    #     validator is not being wrong, it is agreeing with itself. `jsonschema` is not a
    #     dependency of this harness, so the case is SKIPPED BY NAME rather than silently.
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("  skip  jsonschema cross-check (library not installed — stated, not silently passed)")
        cross_checked = False
    else:
        import yaml as _yaml
        schema = json.loads((ROOT / atlas.MANIFEST_SCHEMA).read_text())
        validator = Draft202012Validator(schema)
        found = 0
        for manifest in sorted((ROOT / "languages").rglob("tools.yaml")):
            doc = _yaml.safe_load(manifest.read_text())
            found += len(list(validator.iter_errors(doc)))
            assert not atlas.manifest_errors(
                manifest.parent.relative_to(ROOT / "languages").as_posix()), f"own validator rejects {manifest}"
        assert found == 0, f"jsonschema rejects {found} manifest constraint(s) this harness accepted"
        broken = _yaml.safe_load((ROOT / "languages/python/tools.yaml").read_text())
        broken["policy"]["warnings"] = "sometimes"
        assert list(validator.iter_errors(broken)), "the planted defect must fail the library too"
        CASES.append(("jsonschema agrees with this harness on every manifest",
                      "a validator that only ever agrees with itself"))
        print("  ok    jsonschema cross-check: 0 disagreements over every manifest")
        cross_checked = True

    # The number is MEASURED, not intended: the first draft said 14 against 12 real
    # cases, and an expectation nobody counted fails every run for the wrong reason.
    # The count is MEASURED, not intended: the first draft said 14 against 12 real cases, and an
    # expectation nobody counted fails every run for the wrong reason. The cross-check case is
    # counted only when it RAN, so an absent library cannot quietly reduce the total.
    expected = 35 + (1 if cross_checked else 0)
    if len(CASES) != expected:
        raise SystemExit(f"CASE COUNT MOVED: {len(CASES)} ran, {expected} expected — a harness that silently skips cases prints a full pass")
    print(f"atlas tests: {len(CASES)}/{expected} pass")
    print("SCOPE: these test the CONTRACT. Whether a declared tool EXISTS and RUNS is")
    print("       `python scripts/packprobe.py --mode smoke`; whether the live GitHub controls")
    print("       match the declaration is `python scripts/ghaudit.py`. Neither is left to prose.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
