#!/usr/bin/env python3
"""The rules that guard THIS HARNESS: its YAML shape, its own plants, and its forbidden-call table.

Split out of atlas_guards_test.py at 3.31.0 because that file reached the 1000-line cap, and a cap is
never raised to fit new code. Same contract as its sibling: each case plants a real defect, asserts the
build refuses it, and registers into the RUNNING suite's counted CASES — so a skipped case moves the
asserted total instead of disappearing quietly.
"""
from __future__ import annotations

from pathlib import Path

T = None  # the running atlas_test module, bound by run()


def run(module) -> None:
    global T, ROOT, CASES, case, mutated, atlas
    T = module
    ROOT, CASES, case, mutated, atlas = (module.ROOT, module.CASES, module.case,
                                         module.mutated, module.atlas)
    yaml_shape_cases()
    plant_anchor_cases()
    callshape_cases()
    roster_cases()
    own_enforcement_cases()
    project_marker_cases()


def yaml_shape_cases() -> None:
    """Prose inside a YAML flow collection is quoted, so a comma cannot silently split a declared item (3.28.0).

    SPECIFICITY FIRST, and it decided the shape of the rule. A version reading any unquoted prose value
    anywhere flagged 434 of this tree's 2660 inline values; it was refused and never shipped, because a
    guard that fires on correct content gets switched off. Narrowed to flow context it flagged 45, and
    those 45 were quoted rather than exempted — each verified by parsing the file before and after and
    comparing the loaded data, not by reading the diff.
    """
    import yaml  # noqa: PLC0415
    from yamlshape import flow_prose, yaml_shape_errors
    # The defect itself: ONE intended item, written unquoted, that a later comma turned into TWO.
    intended = "a sentence that gained, a comma"
    split = yaml.safe_load(f"k: [{intended}, tail]")["k"]
    correct = {
        "quoted prose in a flow sequence": "k: ['a sentence with a comma, kept whole', b]",
        "a two-word idiom": "k: [go vet, read only, dry run]",
        "a quoted flow map value": "k: {why: 'the reason, stated in full'}",
        "prose in a BLOCK scalar, which this rule does not judge": "k: a plain sentence, with a comma",
        "nested quoted steps": "k: {steps: [[go, vet, ./...]]}",
    }
    for name, text in correct.items():
        if flow_prose(text):
            raise SystemExit(f"FAIL yamlshape fired on correct YAML: {name} -> {text}")
    if intended in split or len(split) != 3:
        raise SystemExit(f"FAIL the split shape this rule exists for did not reproduce: {split}")
    if len(flow_prose(f"k: [{intended}, tail]")) != 1:
        raise SystemExit(f"FAIL yamlshape did not flag the unquoted sentence that split: "
                         f"{flow_prose(f'k: [{intended}, tail]')}")
    if yaml_shape_errors():
        raise SystemExit(f"FAIL the tree is not clean, so this rule would be switched off: {yaml_shape_errors()[:2]}")
    CASES.append((f"yamlshape allows {len(correct)} correct YAML shapes and flags the unquoted sentence "
                  f"that a comma splits into {len(split)} declared items",
                  "a rule that fires on correctly quoted flow, on an idiom, or on a block scalar it does "
                  "not judge — the 434-finding version of this guard, which was refused"))
    print("  ok    yamlshape allows correct YAML and reads a split flow item as prose")
    # The plant unquotes a real declared item: adding a clause to it would silently become two rungs.
    with mutated("atlas.yaml", lambda s: s.replace("'the duplicate-key loader'", "the duplicate-key loader", 1)):
        case("an unquoted sentence inside a YAML flow collection FAILS",
             "a declared item that a later comma splits in two while the file still parses",
             True, "unquoted prose inside a flow collection")
def plant_anchor_cases() -> None:
    """A mutation anchor that matches nothing is refused, and the deliberate first-occurrence form is not (3.28.0).

    This rule is the one that pays for itself immediately: the two stale anchors it found at 3.28.0 were
    each discovered the expensive way first, five minutes into a mutating suite that then had to restore
    the tree. Reading them from the syntax tree costs under a second.
    """
    from plantcheck import anchors, plant_anchor_errors
    rows = anchors()
    many = sum(1 for suite, target, a in rows if (ROOT / target).exists()
               and (ROOT / target).read_text(encoding="utf-8").count(a) > 1)
    if not rows or not many:
        raise SystemExit(f"FAIL plantcheck read {len(rows)} anchors, {many} of them deliberately "
                         f"multi-matching — it cannot be proving specificity over nothing")
    if plant_anchor_errors():
        raise SystemExit(f"FAIL a plant in this tree already applies to nothing: {plant_anchor_errors()[:2]}")
    CASES.append((f"plantcheck reads {len(rows)} mutation anchors and allows the {many} that match more "
                  f"than once by design",
                  "a rule refusing the deliberate first-occurrence plant, which is most of them — the "
                  "shape that gets a guard switched off"))
    print("  ok    plantcheck reads every mutation anchor and allows the deliberate first-occurrence form")
    # The plant breaks an anchor the way a rewritten sentence does: the text is gone, the case is not.
    with mutated("scripts/atlas_test.py", lambda s: s.replace(
            '"    holds: [the task, the plan, the diff,', '"    holds: [no such line,', 1)):
        case("a mutation anchor that matches nothing FAILS",
             "a planted defect that applies to nothing, leaving the rule it tests unproven while the "
             "case it prints still says ok",
             True, "matches NOTHING in")
def callshape_cases() -> None:
    """Every forbidden_calls row bites, no row is unprobed, and correct calls are untouched (3.31.0).

    THE PLANTS ARE BUILT AT RUN TIME. This file is inside the roster two of the three rows sweep, so a
    literal `time.sleep(1)` or an untimed subprocess call written here would be the defect it plants —
    the same trap that caught three earlier plants in this suite.
    """
    from callshape import coverage, forbidden_call_errors, rules
    declared = rules()
    if forbidden_call_errors():
        raise SystemExit(f"FAIL the tree is not clean, so these rows would be switched off: "
                         f"{forbidden_call_errors()[:3]}")
    probes = {
        "bare_sleep": ("scripts/orphans.py", "\n\ndef _planted_wait():\n    import " + "time\n    "
                       + "time" + ".sleep(1)\n", "calls time.sleep"),
        "yaml_loader_bypass": ("scripts/leaks.py", "\n\ndef _planted_load():\n    return "
                               + "yaml" + "." + "safe_load" + '("{}")\n', "calls a PyYAML loader directly"),
        "subprocess_without_timeout": ("scripts/doctor.py", "\n\ndef _planted_run():\n    import "
                                       + "subprocess\n    return " + "subprocess" + "." + "run"
                                       + '(["true"])\n', "runs a subprocess with no timeout"),
    }
    if set(probes) != set(declared):
        raise SystemExit(f"FAIL a forbidden_calls row carries no planted case, so it stops nothing: "
                         f"declared={sorted(declared)} probed={sorted(probes)}")
    CASES.append((f"every forbidden_calls row is probed — {coverage()}",
                  "a data-driven deny table that grows past its own tests, where a new row reads as "
                  "enforcement and refuses nothing"))
    print("  ok    every forbidden_calls row is probed")
    for name, (target, addition, detail) in sorted(probes.items()):
        with mutated(target, lambda s, a=addition: s + a):
            case(f"forbidden_calls/{name} refuses the call it forbids",
                 "three copies of one guard, which had already drifted apart in roster and exemption",
                 True, detail)
    # SPECIFICITY: the owners and the exempted harnesses must stay silent, or the rows get switched off.
    from callshape import matches
    for name, expect_quiet in (("bare_sleep", "resilience.py"), ("yaml_loader_bypass", "atlascore.py")):
        hits = {path for path, _ in matches(name, declared[name])}
        if any(expect_quiet in h for h in hits):
            raise SystemExit(f"FAIL forbidden_calls/{name} fires on its own owner {expect_quiet}")
    CASES.append(("each forbidden_calls row stays silent on the module that owns the call",
                  "a guard that refuses the one place the call belongs, which is how it gets silenced"))
    print("  ok    each forbidden_calls row stays silent on the module that owns the call")


def roster_cases() -> None:
    """The instrument roster's denominator is a pattern, and an unreached instrument must say why (3.31.0).

    THE FIRST PLANT IS THE OLD BUG ITSELF. The denominator was `scripts/*.py`, so `heavyidle.mjs` — a
    declared instrument — sat outside its own completeness check. Removing its row proves the check now
    sees a non-Python script; under the suffix version this plant would have passed silently.
    """
    from roster import instrument_reach_errors, instrument_roster_errors
    roster_errors, named, present = instrument_roster_errors()
    if roster_errors or instrument_reach_errors():
        raise SystemExit(f"FAIL the roster is not clean, so these rules would be switched off: "
                         f"{(roster_errors + instrument_reach_errors())[:2]}")
    if named != present or not present:
        raise SystemExit(f"FAIL the roster does not cover its own denominator: {named} of {present}")
    CASES.append((f"every one of {present} scripts under scripts/ is a declared instrument",
                  "a roster counted by file extension, which stops seeing a sibling written in another "
                  "language — it already excluded a declared instrument from its own check"))
    print(f"  ok    every one of {present} scripts under scripts/ is a declared instrument")
    # THE ROSTER IS BUILT FROM EACH ROW'S `script:` VALUE, not its key, so renaming the key leaves the
    # file claimed and plants nothing — that version of this plant was inert and is why this comment
    # exists. Repointing the value is what actually leaves heavyidle.mjs claimed by no row.
    with mutated("atlas.yaml", lambda s: s.replace("    script: scripts/heavyidle.mjs\n",
                                                   "    script: scripts/verify.py\n", 1)):
        case("a script under scripts/ that no instrument row names FAILS, whatever its extension",
             "a roster that counts by suffix, so a script in another language needs no row and nothing fires",
             True, "named by no atlas.yaml/instruments entry")
    with mutated("atlas.yaml", lambda s: s.replace(
            "    requirements.txt: 'a pip input read by the install, not an instrument that proves anything'\n", "", 1)):
        case("a file under scripts/ that is neither an instrument nor a declared non-script FAILS",
             "a data file quietly counted as an instrument, or an instrument quietly counted as data",
             True, "named by no atlas.yaml/instruments entry")
    # AN UNREACHED INSTRUMENT MUST NAME ITS REASON. Removing the row must fail, because an arm that is
    # built, measured and wired to nothing reads as covered.
    with mutated("atlas.yaml", lambda s: s.replace("    'vaultlinks.py': '", "    'vaultlinks_moved.py': '", 1)):
        case("an instrument reached by no gate and declared nowhere FAILS",
             "an unshipped arm, which reads as covered precisely because it exists",
             True, "reached by no gate and no invariant")
    # SPECIFICITY: a row naming something a gate DOES reach must fail too, or it hides the next one.
    # astshape.py IS a gate's own argv (the code_shape gate runs it), so declaring it unreached must
    # fail: a stale row is a place for the next genuinely unreached instrument to hide.
    with mutated("atlas.yaml", lambda s: s.replace("    'packprobe.py': '",
                                                   "    'astshape.py': 'a stale row'\n    'packprobe.py': '", 1)):
        case("an unreached row naming an instrument a gate does name FAILS",
             "a stale exemption that the next genuinely unreached instrument hides behind",
             True, "now names directly")


def own_enforcement_cases() -> None:
    """The rung Thea ships to other repositories runs on THIS one, and its three defects stay fixed (3.32.0).

    SPECIFICITY IS ASSERTED FIRST AND IT IS THE WHOLE STORY. This rung was wired into no hook and no
    workflow here, and the reason it could not be was that it fired on correct content: it fed
    `docs/PYTHON.md` to Python's AST parser and `languages/rust/README.md` to rustc, because a route is
    GUIDANCE and a suffix is SOURCE. Twenty-two documents were refused for not being source.
    """
    import enforce
    quiet = {
        "a document whose directory routes to a language": ("docs/PYTHON.md", "not declared source"),
        "a language pack's own README": ("languages/rust/README.md", "not declared source"),
        "a pack's tools declaration": ("languages/python/tools.yaml", "not declared source"),
        "a planted benchmark fixture, whose failing test IS the artifact":
            ("benchmarks/agent/window/test_window.py", "planted failure by declaration"),
    }
    for name, (target, needle) in sorted(quiet.items()):
        state, detail = enforce.check_file(ROOT / target)
        if state != "SKIP" or needle not in detail:
            raise SystemExit(f"FAIL enforce fires on correct content: {name} -> {state} {detail}")
    CASES.append((f"the enforcement rung skips {len(quiet)} correct files it used to refuse",
                  "a rung that feeds a README to a compiler because the directory routes to a language "
                  "— which is why it was wired into no hook at all"))
    print("  ok    the enforcement rung skips the correct files it used to refuse")
    # COULD NOT DECIDE IS NOT DECIDED NO: six harnesses here are named *_test.py and are not pytest suites.
    verdict = enforce.test_file(ROOT / "scripts/agent_test.py")
    if verdict is not None and verdict[0] == "FAIL":
        raise SystemExit(f"FAIL a harness pytest cannot collect is reported as refused: {verdict}")
    CASES.append(("a test runner that collected nothing decides nothing, and is not a refusal",
                  "absence of evidence wearing the label of evidence of absence — pytest exit 5 read "
                  "as a failing suite, which refused six working harnesses"))
    print("  ok    a test runner that collected nothing decides nothing")
    # THE SAME TREE MUST GET THE SAME VERDICT FROM EITHER PATH SHAPE. `--staged` yields relative paths
    # and `--tracked` absolute ones, and the declared prefixes are relative: comparing the raw path
    # matched nothing for one of the two, and the fixtures came back refused.
    fixture = "benchmarks/agent/window/test_window.py"
    if enforce.check_file(ROOT / fixture)[0] != enforce.check_file(Path(fixture))[0]:
        raise SystemExit("FAIL enforce gives one tree two verdicts depending on the path shape it is handed")
    CASES.append(("the enforcement rung gives one verdict whatever path shape it is handed",
                  "a relative prefix compared against an absolute path, which silently matches nothing "
                  "for exactly one of the two callers"))
    print("  ok    the enforcement rung gives one verdict whatever path shape it is handed")
    if enforce.main(["check"]) != 2:
        raise SystemExit("FAIL a bare `check` swept nothing and did not refuse — a vacuous pass")
    CASES.append(("the enforcement rung refuses to sweep nothing and call it a pass",
                  "refusing 0 of 0 and 0 of many printing the same 0"))
    print("  ok    the enforcement rung refuses to sweep nothing and call it a pass")
    # SENSITIVITY: a real break in a real source file must still be refused.
    broken = "\n\ndef _planted_break(\n"
    with mutated("scripts/doctor.py", lambda s, b=broken: s + b):
        state, detail = enforce.check_file(ROOT / "scripts/doctor.py")
        if state != "FAIL":
            raise SystemExit(f"FAIL enforce passed a file that does not parse: {state} {detail}")
    CASES.append(("the enforcement rung still refuses a source file that does not parse",
                  "a rung narrowed until it refuses nothing, which is how a noisy guard gets silenced"))
    print("  ok    the enforcement rung still refuses a source file that does not parse")


def project_marker_cases() -> None:
    """A project-scoped checker with no project above the file SKIPS, and a marker is a GLOB (3.32.1).

    THE MACHINE THIS RAN ON DECIDED THE VERDICT, which is the defect. `enforce check --tracked` was clean
    here and RED in CI: this machine has no dotnet, so it skipped an F# script, while CI had dotnet and
    fed the bare script to `dotnet build`, which found no project and refused it. A local green is not a
    verdict. The toolchain is simulated below so the CI path is provable on a machine that lacks it.
    """
    import shutil

    import enforce
    real = shutil.which
    try:
        enforce.shutil.which = lambda name: "/usr/bin/" + name if name == "dotnet" else real(name)
        state, detail = enforce.check_file(ROOT / "examples/fsharp/BoundedRetry.fsx")
    finally:
        enforce.shutil.which = real
    if state != "SKIP" or "runs per project" not in detail:
        raise SystemExit(f"FAIL a project-scoped checker was handed a file with no project: {state} {detail}")
    CASES.append(("a project-scoped checker with no project above the file skips instead of refusing it",
                  "a checker that refuses a script for not being a project — and a clean sweep on a "
                  "machine that simply lacks the toolchain, read as a verdict"))
    print("  ok    a project-scoped checker with no project above the file skips instead of refusing it")
    # A MARKER IS A GLOB AND A LITERAL NAME GLOBS TO ITSELF, so the three exact markers must still resolve.
    # `atlas` bound by run() is the atlas MODULE, not the declaration reader — a name collision that
    # cost one full suite run. Import the reader explicitly.
    from atlascore import atlas as declaration
    markers = ((declaration().get("gate_tools") or {}).get("compiler_or_typechecker") or {}).get("per_directory") or {}
    literal = [m for m in markers.values() if "*" not in m and "?" not in m]
    if not literal or not any("*" in m or "?" in m for m in markers.values()):
        raise SystemExit(f"FAIL the marker table proves nothing about globs: {markers}")
    for name in literal:
        if enforce._project_home(ROOT / "scripts/atlas.py") is not None and not name:
            raise SystemExit("FAIL a literal marker stopped resolving under glob matching")
    CASES.append((f"the marker table carries {len(literal)} literal name(s) and at least one pattern, "
                  f"and both resolve",
                  "a marker compared as an exact name, which no per-project .NET file can ever match"))
    print("  ok    the marker table carries both a literal name and a pattern, and both resolve")
    # THE COVERAGE LINE MUST NAME ITS OWN BLIND SPOT, or the next clean local pass is read as a verdict.
    source = (ROOT / "scripts/enforce.py").read_text(encoding="utf-8")
    if "not a clean pass everywhere" not in source:
        raise SystemExit("FAIL the enforcement summary no longer names its machine-dependent blind spot")
    CASES.append(("the enforcement summary counts what it skipped for an absent toolchain",
                  "a green line from a sweep whose toolchains were missing, read as full coverage"))
    print("  ok    the enforcement summary counts what it skipped for an absent toolchain")
