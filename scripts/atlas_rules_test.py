#!/usr/bin/env python3
"""The rules that guard THIS HARNESS: its YAML shape, its own plants, and its forbidden-call table.

Split out of atlas_guards_test.py at 3.31.0 because that file reached the 1000-line cap, and a cap is
never raised to fit new code. Same contract as its sibling: each case plants a real defect, asserts the
build refuses it, and registers into the RUNNING suite's counted CASES — so a skipped case moves the
asserted total instead of disappearing quietly.
"""
from __future__ import annotations

from pathlib import Path

import thealang

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
    machine_dependence_cases()
    ast_cache_cases()
    surface_cases()
    declaration_plant_cases()


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


def machine_dependence_cases() -> None:
    """Every gate declares whether its verdict can depend on the machine, and a local pass says so (3.33.0).

    THE SIGHTING IS THIS REPOSITORY'S OWN: at 3.32.0 `own_enforcement` was green on the author's machine
    and RED in CI on the same tree, because this Mac has no dotnet and skipped an F# script that CI fed to
    a compiler. Nothing in the declaration said which gates carry that risk, so a clean local run was read
    as a verdict and cost a full cycle.
    """
    import verify
    from atlascore import atlas as declaration
    gates = (declaration().get("verification_policy") or {}).get("done_set") or []
    dependent = [g for g in gates if g.get("machine_dependent")]
    if not dependent or len(dependent) == len(gates):
        raise SystemExit(f"FAIL the flag separates no two gates: {len(dependent)} of {len(gates)}")
    for gate in dependent:
        if not str(gate.get("why_machine_dependent") or "").strip():
            raise SystemExit(f"FAIL done_set/{gate.get('id')} is machine dependent and says nothing about why")
    CASES.append((f"{len(dependent)} of {len(gates)} gates declare their verdict machine dependent, with reasons",
                  "a clean local run read as a universal verdict — measured green here and red in CI on "
                  "one tree"))
    print("  ok    the machine-dependent gates are declared, each with its reason")
    # THE FLAG TRAVELS ON THE ROW, not in a footnote: a consumer reading --json must see it too.
    row = verify.run_gate({"id": "probe", "argv": ["python", "-c", "pass"], "mutates": False,
                           "machine_dependent": True})
    plain = verify.run_gate({"id": "probe", "argv": ["python", "-c", "pass"], "mutates": False,
                             "machine_dependent": False})
    if not row.get("machine_dependent") or plain.get("machine_dependent"):
        raise SystemExit(f"FAIL the flag does not reach the row: {row.get('machine_dependent')} / "
                         f"{plain.get('machine_dependent')}")
    CASES.append(("a gate's machine dependence reaches its record, so --json carries it too",
                  "a caveat that lives only in the declaration, where a consumer reading the record "
                  "cannot see it"))
    print("  ok    a gate's machine dependence reaches its record")
    declared = "  - {id: lint, argv: [ruff, check, .], mutates: false, machine_dependent: false}"
    with mutated("atlas.yaml", lambda s, d=declared: s.replace(
            d, "  - {id: lint, argv: [ruff, check, .], mutates: false}", 1)):
        case("a done_set gate that does not declare machine_dependent FAILS",
             "a new gate silently assumed universal, which is the assumption that caused the sighting",
             True, "does not declare machine_dependent")
    with mutated("atlas.yaml", lambda s, d=declared: s.replace(
            d, "  - {id: lint, argv: [ruff, check, .], mutates: false, machine_dependent: true}", 1)):
        case("a machine-dependent gate with no stated reason FAILS",
             "a local-only verdict carrying a caveat nobody can act on",
             True, "states no why_machine_dependent")


def ast_cache_cases() -> None:
    """The syntax-tree cache is keyed by CONTENT, and a file that does not parse yields None (3.34.0).

    A NAME-KEYED TREE CACHE WOULD SILENTLY DISARM EVERY PLANT IN THIS SUITE: a case mutates a file and
    re-runs the contract, so a cache that answered by path would hand the guard the tree from before the
    mutation, and 186 cases would pass while proving nothing. That is the trap packmanifest.reset_caches
    records, and strict_yaml already avoids it the same way.
    """
    from atlascore import parsed_python
    one, two = "x = 1\n", "x = 2\n"
    if parsed_python(one, "a") is parsed_python(two, "a"):
        raise SystemExit("FAIL parsed_python answered from the NAME, not the content — every plant in "
                         "this suite would read a pre-mutation tree and pass while proving nothing")
    if parsed_python(one, "a") is not parsed_python(one, "b"):
        raise SystemExit("FAIL parsed_python missed a cache hit on identical text under a second name")
    if parsed_python("def (\n", "broken") is not None:
        raise SystemExit("FAIL parsed_python did not return None on a file that does not parse — a guard "
                         "crashing on it hides the parse check's own finding behind a traceback")
    CASES.append(("the syntax-tree cache answers from content, hits across names, and returns None on a "
                  "file that does not parse",
                  "a tree cache keyed by path, which would hand every planted defect the tree from "
                  "BEFORE its mutation and let 186 cases pass while proving nothing"))
    print("  ok    the syntax-tree cache answers from content, not from a name")


def surface_cases() -> None:
    """The surface notation: four planted defects, one per way a front end goes quietly wrong.

    Its own function per the rule written into the entry point — add a rule, add its planted defect,
    give the fixture its own *_cases(). The fourth case plants in a FUNCTION rather than a file,
    because the shape it kills (a printer that forgets a field the reader accepts) cannot be written
    into the example: the example is what the printer would be forgetting.
    """
    surface = "tools/agent-task.example.thea"
    # 1. IT MUST NOT COMPILE WHEN THE NOTATION IS BROKEN. A front end that repairs its input is
    #    worse than one that errors: the ambiguity leaves no trace.
    with mutated(surface, lambda s: s.replace("  route     python", "  flavour   python", 1)):
        case("an unknown key in a .thea program FAILS", "a notation that carries a typo through as a "
             "field nothing reads", True, "unknown key")
    # 2. THE ORACLE IS THE POINT. A surface free to disagree with the contract it claims to compile
    #    to is a SECOND representation, which is the two-systems shape this repository refuses.
    with mutated(surface, lambda s: s.replace("    tool_calls         12", "    tool_calls         13", 1)):
        case("a .thea program that no longer compiles to its contract FAILS",
             "a notation drifting from the schema it is a surface for, silently", True,
             "compiles to a contract that is not")
    # 3. ONE VALUE, ONE DECLARATION. The version typed into a program is the copy that goes stale.
    with mutated(surface, lambda s: s.replace("  route     python",
                                              '  atlas_version 9.9.9\n  route     python', 1)):
        case("a DERIVED field typed into a .thea program FAILS",
             "a second declaration of the contract version, free to disagree with VERSION", True,
             "is DERIVED")
    # 4. AN EFFECT NOBODY DECLARED. The effects block takes bare words as well as settings, and a
    #    bare word that is not a declared effect must be refused rather than carried as free text.
    with mutated(surface, lambda s: s.replace("    execute\n", "    telepathy\n", 1)):
        case("an effect the roster does not declare, written in a program, FAILS",
             "a free-text effect field, where a typo grants nothing and refuses nothing", True,
             "telepathy")
    # 5. THE NOTATION IS SHIPPED, NOT MERELY CHECKED. `load_contract` is the one function that
    #    knows a task may arrive as a program, and it is what agentrun and sandboxgen call — so a
    #    program and its contract must be the SAME task to them, by hash, not by inspection.
    import agentpolicy
    contract = thealang.compile_path(ROOT / surface)
    from_surface = thealang.load_contract(ROOT / surface)
    from_json = thealang.load_contract(ROOT / "tools/agent-task.example.json")
    assert agentpolicy.contract_hash(from_surface) == agentpolicy.contract_hash(from_json), \
        "the runtime loader returns two different tasks for the two forms of one contract"
    CASES.append(("the runtime loader gives one task for either form",
                  "a surface that checks clean and hands the runtime something else"))
    print("  ok    the runtime loader gives one task for either form")
    # 6. A PROGRAM OUTSIDE THE CHECKOUT. A portable notation whose compiler only works inside this
    #    repository is not portable, and the first version failed in the LABEL rather than the
    #    parse: `rel()` raises for any path not under the root, so a consumer's own program died
    #    with a pathlib traceback. Planted in a real temporary directory, because a unit test of
    #    _label would have asserted the fix and not the path that met it.
    import tempfile
    with tempfile.TemporaryDirectory() as outside:
        away = Path(outside) / "away.thea"
        away.write_text((ROOT / surface).read_text(encoding="utf-8"), encoding="utf-8")
        elsewhere = thealang.compile_path(away)
    assert thealang.render(elsewhere) == thealang.render(contract), \
        "a program outside the checkout compiled to something else"
    CASES.append(("a program outside the repository compiles",
                  "a portable notation whose compiler raises on a path it cannot make relative"))
    print("  ok    a program outside the repository compiles")
    # 7. THE NUMBERS COME FROM THE SCHEMA, and the mutation has to break the DERIVATION rather than
    #    the schema. Planting a string type in the schema was tried first and could not fail: the
    #    notation reads its types FROM that schema, so changing it changes both sides and they agree
    #    — which is the derivation working, and a case that cannot fail proves nothing. So the
    #    roster itself is emptied, exactly as a front end that decided types some other way would
    #    behave, and every budget in the program must then arrive as a string.
    honest_paths = thealang.integer_paths
    thealang.integer_paths = lambda: frozenset()
    try:
        undeclared = thealang.compile_path(ROOT / surface)
    finally:
        thealang.integer_paths = honest_paths
    import agentpolicy
    assert any("expected integer" in problem for problem in agentpolicy.contract_errors(undeclared)), \
        "a notation that stopped reading its types from the schema still produced a valid contract"
    CASES.append(("a notation that stops reading its number types from the schema FAILS",
                  "a front end deciding what is a number from a block name, so a new block of "
                  "integers silently compiles to strings"))
    print("  ok    a notation that stops reading its number types from the schema FAILS")
    # 8. A DECLARATION THAT IMPLEMENTS NOTHING. Planted in the RESOLVER, not in a declaration:
    #    pointing a row at a missing function already fails three other checks, and a case that
    #    cannot tell which guard refused it passes for the wrong reason.
    import agreement
    honest_file_of = agreement._file_of
    agreement._file_of = lambda reference: ""
    try:
        holes = agreement.agreement_errors()
    finally:
        agreement._file_of = honest_file_of
    assert any("resolves to no file" in problem for problem in holes), \
        "the agreement graph reported no hole while nothing resolved to a file"
    CASES.append(("a declaration implemented by no file FAILS",
                  "a roster pointing one way only, so a change lands against declarations nobody "
                  "listed and the only way to find out is to break something"))
    print("  ok    a declaration implemented by no file FAILS")
    # 9. A PRINTER THAT DROPS A FIELD THE READER ACCEPTED — `a_round_trip_that_drops_what_the_format
    #    _allowed`, already a measured shape here, and a notation is exactly where it lands.
    honest = thealang._read
    thealang._read = lambda record, path: None if path == "network" else honest(record, path)
    try:
        dropped = thealang.parse(thealang.render(contract), surface)
    finally:
        thealang._read = honest
    assert dropped != contract, "the round trip survived a printer that forgot a field"
    CASES.append(("the round trip catches a printer that forgets a field",
                  "a surface that accepts a key and prints a program without it"))
    print("  ok    the round trip catches a printer that forgets a field")


# (file, find, replace, case name, the defect it kills, the needle the refusal must carry). ONE table and
# ONE loop, because the first draft was two functions of four copy-pasted `with mutated(...)` blocks
# and the structure gate refused them as one shape in two copies — correctly: a case list is data,
# and writing it as code twice is the duplication this repository already counts.
DECLARATION_PLANTS: list[tuple[str, str, str, str, str, str]] = [
    ("atlas.yaml", "    traps: [a_validator_that_diverges_from_its_spec, a_round_trip_that_drops_what_the_format_allowed]",
     "    traps: [a_trap_nobody_recorded, a_round_trip_that_drops_what_the_format_allowed]",
     "a scope naming a trap the ledger does not record FAILS",
     "a place warning about a shape a reader cannot look up — a warning with no entry",
     "a_trap_nobody_recorded"),
    ("atlas.yaml", "    proves: [contract, planted_suite, code_shape, lint]",
     "    proves: [contract, planted_suite, code_shape, vibes]",
     "a scope naming a gate done_set does not declare FAILS",
     "a place requiring a proof no gate can produce, so the requirement is unmeetable",
     "verification_policy/done_set does not declare"),
    ("atlas.yaml", "    label: area/agent\n    proves: [contract, agent_controls]",
     "    label: area/telepathy\n    proves: [contract, agent_controls]",
     "a scope label the catalog does not carry FAILS",
     "a label a program emits and no repository files anything under",
     "label catalog"),
    ("atlas.yaml", "  fuzz:\n    is: property and fuzz targets",
     "  fuzzz:\n    is: property and fuzz targets",
     "a directory in the tree that no scope covers FAILS",
     "a place list measured against itself instead of the tree, so a directory added beside it is "
     "silently unscoped and answers 'none' to every question",
     "is in the tree and no directory_scopes entry covers it"),
    ("atlas.yaml", "    as: agentpolicy.Verdict", "    as: agentpolicy.NotAThing",
     "a harvest that resolves to nothing FAILS",
     "a claim to have taken a mechanism, with nothing in the tree to point at",
     "resolves to nothing in this tree"),
    ("atlas.yaml", "    status: harvested\n    as: agenteffects.delegation_errors",
     "    status: planned\n    as: agenteffects.delegation_errors",
     "a third mechanism status FAILS",
     "a roster of someday-work, where an unshipped arm reads as covered",
     "only 'harvested' and 'refused' exist"),
    ("atlas.yaml", "    because: a parser or a policy that resolves an ambiguous input",
     "    why_not: a parser or a policy that resolves an ambiguous input",
     "a refusal with no reason FAILS",
     "a no the next reader re-proposes, because nothing records why it was a no",
     "names no reason"),
    ("atlas.yaml", "    from: go\n    proves: a failure is a value",
     "    from: golang\n    proves: a failure is a value",
     "a mechanism harvested from a pack that is not a route FAILS",
     "a roster pointing at a language this atlas does not route, so the claim cannot be checked",
     "which is not a route in this atlas"),
    ("atlas.yaml", "    enforced_by_ref: atlascore.StrictLoader\n", "",
     "a sentence naming an enforcer with no bare reference beside it FAILS",
     "a reference only a regexp over prose could find — re-word the sentence and the graph silently "
     "loses an edge",
     "declares no enforced_by_ref"),
    ("atlas.yaml", "    enforced_by_ref: packmanifest._check", "    enforced_by_ref: packmanifest.validate",
     "a bare reference disagreeing with its own sentence FAILS",
     "two answers to one question, where the prose and the identity drift apart unnoticed",
     "two answers to one question"),
    ("atlas.yaml", "      refuses_at: post_call", "      refuses_at: whenever",
     "a control declaring a phase the atlas does not name FAILS",
     "a control whose phase nobody declared, which a reader assumes prevents something when it may "
     "only describe what already happened",
     "is not one of the declared refusal_phases"),
    ("models/claude/README.md", "`thea intake", "`thea intakke",
     "a runtime adapter naming a command this CLI does not have FAILS",
     "eight adapters telling eight runtimes how to reach this atlas, and nothing checking that what "
     "they tell them to run exists — so a command renamed here keeps being advertised there",
     "which this CLI does not have"),
]


def declaration_plant_cases() -> None:
    """Every declared roster this contract reads, one planted defect per way it stops resolving.

    Scopes and mechanisms are the same KIND of thing — a row whose every field must point at
    something that exists — so they are one table rather than two functions that differ only in
    their strings.
    """
    for where, find, replace, name, kills, needle in DECLARATION_PLANTS:
        with mutated(where, lambda s, f=find, r=replace: s.replace(f, r, 1)):
            case(name, kills, True, needle)
