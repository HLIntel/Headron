#!/usr/bin/env python3
"""The rules that guard THIS HARNESS: its YAML shape, its own plants, and its forbidden-call table.

Split out of atlas_guards_test.py at 3.31.0 because that file reached the 1000-line cap, and a cap is
never raised to fit new code. Same contract as its sibling: each case plants a real defect, asserts the
build refuses it, and registers into the RUNNING suite's counted CASES — so a skipped case moves the
asserted total instead of disappearing quietly.
"""
from __future__ import annotations

import functools
import subprocess
import tempfile
from pathlib import Path

import thealang
from atlascore import strict_yaml

T = None  # the running atlas_test module, bound by run()


def run(module) -> None:
    global T, ROOT, CASES, case, mutated, atlas
    T = module
    ROOT, CASES, case, mutated, atlas = (module.ROOT, module.CASES, module.case,
                                         module.mutated, module.atlas)
    import edges
    edges.refusal_cases(module)
    changed_edge_cases()
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
    squash_lane_cases()
    landed_cases()
    watch_cases()
    enforce_target_cases()
    shebang_cases()
    success_ledger_cases()
    vaultlinks_cases()
    markdown_cases()
    lesson_flow_cases()
    private_terms_cases()
    port_cases()
    brainstorm_cases()
    intake_prompt_cases()
    ledger_enforcer_cases()
    rekick_cases()


def rekick_cases() -> None:
    """An outage-stranded check is restarted; a check that ran and failed never is (branchstate --rekick)."""
    from branchstate import rekick_plan
    lost, ran = {"name": "Contract", "conclusion": "cancelled", "runner_name": "", "steps": []}, \
        {"name": "Contract", "conclusion": "failure", "runner_name": "GitHub Actions 7", "steps": [{}]}
    assert rekick_plan([{"id": 1, "event": "pull_request", "jobs": [lost]}]) == ([1], False, []), "a lost job was not rerun"
    assert rekick_plan([{"id": 2, "event": "dynamic", "jobs": [lost]}]) == ([], True, []), "CodeQL needs a push, not a rerun"
    assert rekick_plan([{"id": 3, "event": "pull_request", "jobs": [lost, ran]}]) == ([], False, ["Contract"]), \
        "a run holding a REAL failure was retried blind"
    CASES.append(("rekick restarts only checks no runner took, and pushes for a run the API cannot rerun",
                  "a blind retry over a real failure, or a merge left BLOCKED by an outage"))
    print("  ok    rekick retries an outage, never a failure")


def port_cases() -> None:
    """One socket: a path resolves to its stack tier, a tree may declare its own layers, and every command sits on a menu (3.46.0)."""
    import port
    plants = [
        ("a thea command on no port menu FAILS", "a capability an agent plugged in is never told exists",
         "check, verify, resume, intake, landed,", "check, verify, resume, intake,", "is on no port menu", 'inv:every_command_has_a_socket'),
        ("a stack tier with no glyph FAILS", "a layer the port line cannot draw",
         "database: '⠿', none", "none", "has no glyph", 'inv:every_command_has_a_socket'),
    ]
    for name, kills, old, new, needle, by in plants:
        with mutated("atlas.yaml", lambda s, o=old, n=new: s.replace(o, n, 1)):
            case(name, kills, True, needle, by=by)
    tiers = port.stack_tiers()
    want = {"web/components/Button.tsx": "frontend", "src/hooks/useCart.ts": "middle-frontend",
            "api/routes/users.py": "middle", "services/billing/charge.go": "middle-backend",
            "lib/core.py": "backend", "db/migrations/001_init.sql": "database", "README.md": "none"}
    got = {p: port.tier_of(p, tiers) for p in want}
    with tempfile.TemporaryDirectory() as tree:
        Path(tree, ".atlas.yaml").write_text("stack_tiers:\n  edge:\n    suffixes: [.py]\n")
        own = port.stack_tiers(Path(tree))
    line = port.line(port.record("scripts/port.py", None, "codebase", None), color=False)
    real, port.invocation = port.invocation, lambda c, t: f"thea {c}"  # planted: a next step printed bare
    try:
        bare = [e for e in port.port_menu_errors() if "refuses to parse" in e]
    finally:
        port.invocation = real
    runnable = [e for e in port.port_menu_errors() if "refuses to parse" in e]
    if got != want or list(own) != ["edge"] or "\033" in line or not line.startswith("◉ scripts/port.py") or not bare or runnable:
        raise SystemExit(f"FAIL port: got={got} own={list(own)} line={line!r} bare={len(bare)} runnable={runnable}")
    CASES.append(("a path resolves to its stack tier, a tree's own .atlas.yaml replaces the layers, the line is plain off a "
                  "terminal, and every next step parses as a thea command",
                  "a layer guessed from a file name, colour codes written into a pipe, or a next step printed without its operand"))
    print("  ok    the port resolves tiers, honours a tree's own layers and draws a plain line")


def brainstorm_cases() -> None:
    """A strategic brainstorm converges only from a diverged, pre-mortemed, undominated record (3.47.0)."""
    import brainstorm
    base = strict_yaml(brainstorm.SKELETON.format(question="q"), "skeleton")
    base["because"] = "best time_to_value"
    good = brainstorm.record_errors(base)
    no_base = {**base, "options": {k: v for k, v in base["options"].items() if k != "do_nothing"}}
    worse = {**base, "options": {**base["options"], "option_c": {**base["options"]["option_a"],
             "scores": {"value": 0, "cost": -2, "risk": -1, "time_to_value": 0}}}, "chosen": "option_c", "because": "value"}
    door = {**base, "reversible": False, "approver": None}
    if good or not brainstorm.undiverged(no_base) or not brainstorm.dominated_choice(worse) or not brainstorm.one_way_door(door):
        raise SystemExit(f"FAIL brainstorm: good={good} base={brainstorm.undiverged(no_base)!r} "
                         f"dominated={brainstorm.dominated_choice(worse)!r} door={brainstorm.one_way_door(door)!r}")
    CASES.append(("a brainstorm with no baseline, a dominated choice or an unowned one-way door is refused; the filled skeleton converges",
                  "a first idea argued as the only option, walked through a door nobody owns"))
    print("  ok    a brainstorm converges only when diverged, pre-mortemed and undominated")


def intake_prompt_cases() -> None:
    """A prompt read as written: an open list expands to its declared class, a typo is echoed, a decision is routed (3.47.0)."""
    import intake
    listed = intake.digest("wire claude, codex, opencode etc into the port")["open_lists"]
    typo, decision = intake.read_as("teha should evrify the routes"), intake.digest("should we move the router to a VPS or keep it local")
    loose = intake.open_lists("fix merges, rebase, clean ups, deblots, commands, edges etc")  # one item of six is a command
    if not listed or listed[0]["class"] != "runtimes" or len(listed[0]["scope"]) != 7 or loose[0]["class"] or \
            "clean ups" not in loose[0]["items"] or typo != {"teha": "thea", "evrify": "verify"} or decision["process"] != "strategic_brainstorm":
        raise SystemExit(f"FAIL intake: listed={listed} loose={loose} typo={typo} process={decision['process']}")
    CASES.append(("an open list expands to the declared class it samples, a one-edit typo is echoed back, a strategic ask routes to a brainstorm",
                  "a prompt's examples read as its whole scope, one stray match claiming a list, a typo guessed silently, a decision treated as an edit"))
    print("  ok    intake reads open lists, typos and decisions")


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
             True, "unquoted prose inside a flow collection", by='inv:yaml_prose_is_quoted')
def plant_anchor_cases() -> None:
    """A mutation anchor that matches nothing is refused, and the deliberate first-occurrence form is not (3.28.0).

    This rule is the one that pays for itself immediately: the two stale anchors it found at 3.28.0 were
    each discovered the expensive way first, five minutes into a mutating suite that then had to restore
    the tree. Reading them from the syntax tree costs under a second.
    """
    from plantcheck import anchors, hits, plant_anchor_errors
    rows = anchors()
    many = sum(1 for suite, target, a in rows if (ROOT / target).exists()
               and hits((ROOT / target).read_text(encoding="utf-8"), a) > 1)
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
             True, "matches NOTHING in", by='inv:plants_can_still_apply')
    # A REGEX-LOCATED anchor drifts the same way, from the TARGET's side: atlas_test finds this row with re.search.
    with mutated("atlas.yaml", lambda s: s.replace("  root_cause_outside_scope: {closed_by:", "  root_cause_elsewhere: {closed_by:", 1)):
        case("a regex that locates a plant and matches nothing FAILS before the suite runs",
             "a clean check followed by a suite that dies on AttributeError: NoneType has no group",
             True, "matches NOTHING in atlas.yaml", by='inv:plants_can_still_apply')
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
        "raw_tree_walk": ("scripts/roster.py", "\n\ndef _planted_walk(tree):\n    import ast\n    return list("
                          + "ast" + "." + "walk" + "(tree))\n", "calls ast.walk directly"),
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
                 True, detail, by="inv:forbidden_calls_are_refused")
    # SPECIFICITY: the owners and the exempted harnesses must stay silent, or the rows get switched off.
    from callshape import matches
    for name, expect_quiet in (("bare_sleep", "resilience.py"), ("yaml_loader_bypass", "atlascore.py"),
                               ("raw_tree_walk", "atlascore.py")):
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
             True, "named by no atlas.yaml/instruments entry", by='roster.instrument_roster_errors')
    with mutated("atlas.yaml", lambda s: s.replace(
            "    requirements.txt: 'a pip input read by the install, not an instrument that proves anything'\n", "", 1)):
        case("a file under scripts/ that is neither an instrument nor a declared non-script FAILS",
             "a data file quietly counted as an instrument, or an instrument quietly counted as data",
             True, "named by no atlas.yaml/instruments entry", by='roster.instrument_roster_errors')
    # AN UNREACHED INSTRUMENT MUST NAME ITS REASON. Removing the row must fail, because an arm that is
    # built, measured and wired to nothing reads as covered.
    with mutated("atlas.yaml", lambda s: s.replace("    'taskbench.py': '", "    'taskbench_moved.py': '", 1)):
        case("an instrument reached by no gate and declared nowhere FAILS",
             "an unshipped arm, which reads as covered precisely because it exists",
             True, "reached by no gate and no invariant", by='inv:instruments_are_reached_or_declared')
    # SPECIFICITY: a row naming something a gate DOES reach must fail too, or it hides the next one.
    # astshape.py IS a gate's own argv (the code_shape gate runs it), so declaring it unreached must
    # fail: a stale row is a place for the next genuinely unreached instrument to hide.
    with mutated("atlas.yaml", lambda s: s.replace("    'packprobe.py': '",
                                                   "    'astshape.py': 'a stale row'\n    'packprobe.py': '", 1)):
        case("an unreached row naming an instrument a gate does name FAILS",
             "a stale exemption that the next genuinely unreached instrument hides behind",
             True, "now names directly", by='inv:instruments_are_reached_or_declared')


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
    # EACH MARKER IS PLANTED, ONE PER TREE: the loop this replaces tested `not name` on a non-empty literal
    # and could never fail. A file matching the marker sits two levels above the source; it must be found.
    for marker in markers.values():
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / marker.replace("*", "app").replace("?", "f")).write_text("", encoding="utf-8")
            (Path(tmp) / "src/deep").mkdir(parents=True)
            if enforce._marker_home(Path(tmp) / "src/deep/file.x", marker) != Path(tmp).resolve():
                raise SystemExit(f"FAIL marker {marker!r} does not resolve to the directory that holds it")
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
             True, "does not declare machine_dependent", by='inv:declarations_are_read')
    with mutated("atlas.yaml", lambda s, d=declared: s.replace(
            d, "  - {id: lint, argv: [ruff, check, .], mutates: false, machine_dependent: true}", 1)):
        case("a machine-dependent gate with no stated reason FAILS",
             "a local-only verdict carrying a caveat nobody can act on",
             True, "states no why_machine_dependent", by='inv:declarations_are_read')


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
             "field nothing reads", True, "unknown key", by=('agentpolicy.agent_policy_errors', 'inv:autonomous_profile_is_enforced'))
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
             "is DERIVED", by=('agentpolicy.agent_policy_errors', 'inv:autonomous_profile_is_enforced'))
    # 4. AN EFFECT NOBODY DECLARED. The effects block takes bare words as well as settings, and a
    #    bare word that is not a declared effect must be refused rather than carried as free text.
    with mutated(surface, lambda s: s.replace("    execute\n", "    telepathy\n", 1)):
        case("an effect the roster does not declare, written in a program, FAILS",
             "a free-text effect field, where a typo grants nothing and refuses nothing", True,
             "telepathy", by=('agentpolicy.agent_policy_errors', 'inv:autonomous_profile_is_enforced'))
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


# (file, find, replace, case name, defect killed, needle). ONE table, ONE loop: two copy-pasted `with mutated(...)`
# functions were refused by the structure gate as one shape twice — a case list is data, not duplicated code.
DECLARATION_PLANTS: list[tuple[str, str, str, str, str, str]] = [
    ("atlas.yaml", "    routes: 36\n", "    routes: 37\n", "a surface line above the measured route count FAILS as stale",
     "a frozen surface with headroom, which absorbs the next route", "against a stale declaration of 37", 'contextcost.example_coverage_errors'),
    ("atlas.yaml", "    instruments: 77\n", "    instruments: 76\n", "an instrument beyond the frozen surface FAILS",
     "breadth added past the freeze while every other gate stays green", "the ratchet only falls", 'contextcost.example_coverage_errors'),
    ("atlas.yaml", "    traps: [a_validator_that_diverges_from_its_spec, a_round_trip_that_drops_what_the_format_allowed]",
     "    traps: [a_trap_nobody_recorded, a_round_trip_that_drops_what_the_format_allowed]",
     "a scope naming a trap the ledger does not record FAILS",
     "a place warning about a shape a reader cannot look up — a warning with no entry",
     "a_trap_nobody_recorded", 'dirscope.declaration_errors'),
    ("atlas.yaml", "    proves: [contract, planted_suite, code_shape, lint]",
     "    proves: [contract, planted_suite, code_shape, vibes]",
     "a scope naming a gate done_set does not declare FAILS",
     "a place requiring a proof no gate can produce, so the requirement is unmeetable",
     "verification_policy/done_set does not declare", 'dirscope.declaration_errors'),
    ("atlas.yaml", "    label: area/agent\n    proves: [contract, agent_controls]",
     "    label: area/telepathy\n    proves: [contract, agent_controls]",
     "a scope label the catalog does not carry FAILS",
     "a label a program emits and no repository files anything under",
     "label catalog", 'dirscope.declaration_errors'),
    ("atlas.yaml", "  fuzz:\n    is: property and fuzz targets",
     "  fuzzz:\n    is: property and fuzz targets",
     "a directory in the tree that no scope covers FAILS",
     "a place list measured against itself instead of the tree, so a directory added beside it is "
     "silently unscoped and answers 'none' to every question",
     "is in the tree and no directory_scopes entry covers it", 'dirscope.declaration_errors'),
    ("atlas.yaml", "    as: agentpolicy.Verdict", "    as: agentpolicy.NotAThing",
     "a harvest that resolves to nothing FAILS",
     "a claim to have taken a mechanism, with nothing in the tree to point at",
     "resolves to nothing in this tree", 'declcheck.mechanism_errors'),
    ("atlas.yaml", "    status: harvested\n    as: agenteffects.delegation_errors",
     "    status: planned\n    as: agenteffects.delegation_errors",
     "a third mechanism status FAILS",
     "a roster of someday-work, where an unshipped arm reads as covered",
     "only 'harvested' and 'refused' exist", 'declcheck.mechanism_errors'),
    ("atlas.yaml", "    because: a parser or a policy that resolves an ambiguous input",
     "    why_not: a parser or a policy that resolves an ambiguous input",
     "a refusal with no reason FAILS",
     "a no the next reader re-proposes, because nothing records why it was a no",
     "names no reason", 'declcheck.mechanism_errors'),
    ("atlas.yaml", "    from: go\n    proves: a failure is a value",
     "    from: golang\n    proves: a failure is a value",
     "a mechanism harvested from a pack that is not a route FAILS",
     "a roster pointing at a language this atlas does not route, so the claim cannot be checked",
     "which is not a route in this atlas", 'declcheck.mechanism_errors'),
    ("atlas.yaml", "    enforced_by_ref: atlascore.StrictLoader\n", "",
     "a sentence naming an enforcer with no bare reference beside it FAILS",
     "a reference only a regexp over prose could find — re-word the sentence and the graph silently "
     "loses an edge",
     "declares no enforced_by_ref", 'declcheck.enforced_reference_errors'),
    ("atlas.yaml", "    enforced_by_ref: packmanifest._check", "    enforced_by_ref: packmanifest.validate",
     "a bare reference disagreeing with its own sentence FAILS",
     "two answers to one question, where the prose and the identity drift apart unnoticed",
     "two answers to one question", 'declcheck.enforced_reference_errors'),
    ("atlas.yaml", "    enforced_by_ref: branchstate.land\n", "",
     "a parser rule whose enforcer is only a sentence FAILS",
     "a rule that reads as enforced while nothing in the tree is named to refuse it",
     "missing enforced_by or enforced_by_ref or defect", 'inv:parsers_refuse_rather_than_guess'),
    ("atlas.yaml", "      refuses_at: post_call", "      refuses_at: whenever",
     "a control declaring a phase the atlas does not name FAILS",
     "a control whose phase nobody declared, which a reader assumes prevents something when it may "
     "only describe what already happened",
     "is not one of the declared refusal_phases", ('agentpolicy.agent_policy_errors', 'inv:autonomous_profile_is_enforced')),
    ("docs/CONSUMING.md", "curl -fsSL", "curl \u2014fsSL",
     "a typographic dash inside a command block FAILS",
     "a line a reader copies that renders identically to the right one and is a different argv — the "
     "error names a flag indistinguishable from the one they typed",
     "renders like", 'generated_errors'),
    ("models/claude/README.md", "`thea intake", "`thea intakke",
     "a runtime adapter naming a command this CLI does not have FAILS",
     "eight adapters telling eight runtimes how to reach this atlas, and nothing checking that what "
     "they tell them to run exists — so a command renamed here keeps being advertised there",
     "which this CLI does not have", 'agreement.agreement_errors'),
    ("atlas.yaml", "    here: ['every ratchet — entry_paths', install_footprint, code_shape,", "    here: [",
     "an untiered ratchet VIOLATES its hard invariant", "a bound only the knowledge reader refuses",
     "governance_tiers/bounded does not name it", 'inv:every_bound_declares_its_tier'),
    ("atlas.yaml", "    gate: source_change", "    gate: no_such_gate", "a build step naming an undeclared gate FAILS",
     "a build order whose gate no policy defines", "which verification_policy does not declare", 'cross_reference_errors'),
    ("atlas.yaml", "  owner: HeartlandIntel\n", "  owner: ''\n", "an identity with no owner FAILS",
     "a URL segment every badge and checkout resolves, left blank", "identity declares no owner", '_identity_errors'),
    (".github/dependabot.yml", "  - package-ecosystem: pip\n    directory: /scripts\n",
     "  - package-ecosystem: pip\n    directory: /scripts\n    schedule:\n      interval: weekly\n\n"
     "  - package-ecosystem: pip\n    directory: /scripts\n",
     "a second dependabot entry for one ecosystem and directory FAILS",
     "a duplicate hidden in a list, where the strict loader sees no repeated key",
     "declares pip for /scripts more than once", 'dependabot_errors'),
]


def declaration_plant_cases() -> None:
    """Every declared roster this contract reads, one planted defect per way it stops resolving.

    Scopes and mechanisms are the same KIND of thing — a row whose every field must point at
    something that exists — so they are one table rather than two functions that differ only in
    their strings.
    """
    for where, find, replace, name, kills, needle, by in DECLARATION_PLANTS:
        with mutated(where, lambda s, f=find, r=replace: s.replace(f, r, 1)):
            case(name, kills, True, needle, by=by)


def _git_in(repo: str, *a: str, check: bool = True) -> str:  # with an identity: a commit cannot fail on a bare machine
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo,
                          capture_output=True, text=True, timeout=600, check=check).stdout


def _commit_in(repo: str, name: str, text: str, msg: str) -> None:
    (Path(repo) / name).write_text(text)
    _git_in(repo, "add", name)
    _git_in(repo, "commit", "-qm", msg)


def squash_lane_cases() -> None:
    """A squash-merged lane is FINISHED even though `git branch -d` cannot see it (3.24.0)."""
    import branchstate
    with tempfile.TemporaryDirectory() as repo:
        git = functools.partial(_git_in, repo)
        git("init", "-q", "-b", "main")
        _commit_in(repo, "f.txt", "base\n", "base")
        git("checkout", "-qb", "lane")
        _commit_in(repo, "f.txt", "base\nlane\n", "lane work")
        git("checkout", "-q", "main")
        git("merge", "--squash", "lane", check=False)          # the shape a forge's squash-merge leaves
        git("commit", "-qm", "lane work (squashed)")
        saved, branchstate._tree = branchstate._tree, lambda: Path(repo).resolve()
        try:
            squashed = branchstate.merged_by_patch("lane", "main")
            git("checkout", "-qb", "unmerged")
            _commit_in(repo, "g.txt", "new\n", "real work")
            git("checkout", "-q", "main")
            still_open = branchstate.merged_by_patch("unmerged", "main")
            for ref in ("main", "unmerged"):                    # a forge head nothing local tracks is stale
                git("update-ref", f"refs/remotes/origin/{ref}", ref)
            forgotten = [name for name, _ in branchstate.stale_remotes()]
            git("remote", "add", "origin", repo)
            git("branch", "-q", "-u", "origin/unmerged", "unmerged")
            forgotten += [name for name, _ in branchstate.stale_remotes()]
            refused = subprocess.run(["git", "branch", "-d", "lane"], cwd=repo, capture_output=True,
                                     timeout=600, check=False).returncode
        finally:
            branchstate._tree = saved
    if not squashed or still_open or refused == 0 or forgotten != ["origin/unmerged"]:
        raise SystemExit(f"FAIL squash detection: {squashed=} {still_open=} branch -d rc={refused} {forgotten=}")
    CASES.append(("a squash-merged lane reads FINISHED while `git branch -d` still refuses it",
                  "a landed lane kept forever because ancestry cannot see a squash merge"))
    print("  ok    a squash-merged lane reads FINISHED while `git branch -d` still refuses it")


def landed_cases() -> None:
    """A branch is landed by its CHANGE, never by its file list (3.42.0)."""
    import branchstate
    with tempfile.TemporaryDirectory() as repo:
        git = functools.partial(_git_in, repo)
        git("init", "-q", "-b", "main")
        _commit_in(repo, "f.txt", "base\n", "base")
        git("checkout", "-qb", "squashed")                      # two commits, one squash: no patch matches
        _commit_in(repo, "f.txt", "base\none\n", "one")
        _commit_in(repo, "f.txt", "base\none\ntwo\n", "two")
        git("checkout", "-qb", "same_files", "main")            # the trap: same file, different change
        _commit_in(repo, "f.txt", "base\nfix\n", "the fix nobody shipped")
        git("checkout", "-q", "main")
        git("merge", "--squash", "squashed", check=False)
        git("commit", "-qm", "one and two (squashed)")
        saved, branchstate._tree = branchstate._tree, lambda: Path(repo).resolve()
        try:
            squashed = branchstate.unlanded_commits("squashed", "main")
            trap = branchstate.unlanded_commits("same_files", "main")
        finally:
            branchstate._tree = saved
    if squashed or len(trap) != 1:
        raise SystemExit(f"FAIL landed-by-content: squashed={squashed} same_files={trap}")
    CASES.append(("a multi-commit squash reads LANDED and a same-files lane with a different change does not",
                  "a pull request closed as already-on-main because its file list matched"))
    print("  ok    a branch is landed by its change, never by its file list")


def watch_cases() -> None:
    """`watch` names ledger shapes; an unknown one is refused and a planned program is born with them (3.42.0)."""
    import agentvocab
    import atlascore
    known = next(iter(atlascore.atlas()["agent_failure_modes"]))
    refused = agentvocab.watch_errors({"watch": [known, "a_lesson_nobody_recorded"]})
    record = {"route": "python", "path": "scripts/branchstate.py", "task": "default",
              "change_class": "source_change", "required_gates": []}
    born = thealang.parse(thealang.program_from_plan(record, "Prove the landing verdict."))
    if len(refused) != 1 or "a_lesson_nobody_recorded" not in refused[0] or not born.get("watch"):
        raise SystemExit(f"FAIL watch: refused={refused} born={born.get('watch')}")
    CASES.append(("an unknown `watch` shape is refused and `plan --thea` names the lessons for its target",
                  "a lesson read once, far from the step it was about, and a lesson named that does not exist"))
    print("  ok    watch names real ledger shapes and travels with a planned program")


def enforce_target_cases() -> None:
    """`enforce check --tracked` sweeps the CALLER's repository, never the atlas's (3.43.0)."""
    import sys
    with tempfile.TemporaryDirectory() as repo:
        _git_in(repo, "init", "-q")
        (Path(repo) / "broken.py").write_text("def f(:\n")
        _git_in(repo, "add", "broken.py")
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "enforce.py"), "check", "--tracked"], cwd=repo,
                              capture_output=True, text=True, timeout=600, check=False)
    if "broken.py" not in done.stdout or "1 refused" not in done.stdout or "atlas.py" in done.stdout:
        raise SystemExit(f"FAIL enforce --tracked swept another tree: {done.stdout[-400:]}")
    CASES.append(("`enforce check --tracked` from a consumer sweeps the consumer's files and refuses its broken one",
                  "a sweep that reads the atlas's own tree and passes a consumer it never looked at"))
    print("  ok    enforce --tracked sweeps the caller's repository")


def shebang_cases() -> None:
    """The interpreter a shebang names chooses the checker; the suffix only names a family (3.43.0)."""
    import enforce
    body = "for f in *(N); do :; done\n"            # correct zsh, a syntax error to bash
    with tempfile.TemporaryDirectory() as scratch:
        zsh_file, bash_file = Path(scratch) / "z.sh", Path(scratch) / "b.sh"
        zsh_file.write_text("#!/usr/bin/env zsh\n" + body)
        bash_file.write_text("#!/bin/bash\n" + body)
        picked = enforce.shebang_argv(zsh_file, "bash")
        zsh_state, bash_state = enforce.check_file(zsh_file)[0], enforce.check_file(bash_file)[0]
    if picked != ["zsh", "-n"] or zsh_state == "FAIL" or bash_state != "FAIL":
        raise SystemExit(f"FAIL shebang: argv={picked} zsh={zsh_state} bash={bash_state}")
    CASES.append(("a `#!/usr/bin/env zsh` .sh file is checked by zsh, and the same text under bash is refused",
                  "correct zsh refused by `bash -n` because a suffix was read as the interpreter"))
    print("  ok    the shebang chooses the checker")


def success_ledger_cases() -> None:
    """Failure -> move -> guard is one wired graph, refused when a pairing dangles or a recurring failure has no move."""
    import knowledge
    plants = [
        ("a success pairing a failure nobody recorded FAILS", "a move wired to a lesson that does not exist",
         "    pairs: [a_verdict_printed_and_not_gated]\n",
         "    pairs: [a_verdict_printed_and_not_gated, a_lesson_nobody_recorded]\n", "does not hold", 'inv:successes_answer_recurring_failures'),
        ("a recurring failure with no move FAILS", "a shape seen three times whose ledger still says only what not to do",
         "    pairs: [a_roster_that_resolved_to_nothing, a_gate_that_resolves_to_silence]\n",
         "    pairs: [a_gate_that_resolves_to_silence]\n",
         "no success names the move", 'inv:successes_answer_recurring_failures'),
        ("a success that opens like an accomplishment FAILS", "a ledger of things built, read as moves to repeat",
         "    move: 'hand every path a command carries", "    move: 'shipped every path a command carries",
         "an accomplishment, not a move to repeat", 'inv:successes_answer_recurring_failures'),
    ]
    for name, kills, old, new, needle, by in plants:
        with mutated("atlas.yaml", lambda s, o=old, n=new: s.replace(o, n, 1)):
            case(name, kills, True, needle, by=by)
    moves = [k for k, _ in knowledge.moves_for("a_backtick_inside_a_double_quoted_shell_string")]
    found = [k for k, _ in knowledge.relevant("successes", "commit message with backticks in a heredoc", 3)]
    if "messages_through_a_quoted_heredoc" not in moves or "messages_through_a_quoted_heredoc" not in found:
        raise SystemExit(f"FAIL success lookup: moves={moves} found={found}")
    CASES.append(("a failure hands back its move, and `successes --for` finds it from the task's words",
                  "a success ledger nobody reaches from the failure it answers"))
    print("  ok    a failure hands back the move that replaces it")


def vaultlinks_cases() -> None:
    """A table-escaped pipe and a non-note file both resolve the way Obsidian resolves them (3.43.0)."""
    import sys
    with tempfile.TemporaryDirectory() as vault:
        Path(vault, "a.md").write_text("| x |\n|---|\n| [[b\\|B]] |\n\n[[c.base]] [[gone]]\n")
        Path(vault, "b.md").write_text("[[a]]\n")
        Path(vault, "c.base").write_text("views: []\n")
        done = subprocess.run([sys.executable, str(ROOT / "scripts" / "vaultlinks.py"), vault],
                              capture_output=True, text=True, timeout=600, check=False)
    if "DANGLING 1 ref(s) → 1 missing" not in done.stdout or "[[gone]]" not in done.stdout:
        raise SystemExit(f"FAIL vaultlinks: {done.stdout[:400]}")
    CASES.append(("vaultlinks resolves `[[b\\|B]]` in a table and `[[c.base]]`, and still reports the one missing note",
                  "working table links and .base links reported dangling, which buries the real ones"))
    print("  ok    vaultlinks resolves table-escaped and non-note links")


DATED = "docs/log-" + "2026" + "-09.md"  # a dated name, assembled so the tree carries no calendar date


def markdown_cases() -> None:
    """Every Markdown file has a class and a rule: living capped, current and reachable; a record append-only (3.44.0)."""
    import mdshape
    with tempfile.TemporaryDirectory() as repo:
        tree = Path(repo).resolve()
        _git_in(repo, "init", "-q")
        (tree / ".atlas.yaml").write_text("markdown_policy:\n  living_max_bytes: 200\n  entries: [README.md]\n")
        (tree / "README.md").write_text("# r\n\n[guide](docs/guide.md)\n")
        (tree / "docs").mkdir()
        (tree / "docs/guide.md").write_text("# g\n\n" + "x" * 300 + "\n")          # living, over its cap
        (tree / "docs/note.md").write_text("# n\n\n~~old claim~~ new claim\n")      # narration, and nobody links it
        (tree / DATED).write_text("# log\n\n- first\n- second\n")  # a record
        _git_in(repo, "add", "-A")
        _git_in(repo, "commit", "-qm", "base")
        found = mdshape.tree_errors(tree)
        (tree / DATED).write_text("# log\n\n- second\n- third\n")  # history edited back
        _git_in(repo, "add", "-A")
        rewritten = mdshape.preservation_errors(tree, mdshape.policy(tree), None)
        (tree / DATED).write_text("# log\n\n- first\n- second\n- third\n")
        _git_in(repo, "add", "-A")
        appended = mdshape.preservation_errors(tree, mdshape.policy(tree), None)
    text = " ".join(found)
    if not ("guide.md: 3" in text and "note.md: narration" in text and "note.md: a living note no entry" in text
            and "log-" not in text and rewritten and not appended):
        raise SystemExit(f"FAIL markdown classes: found={found} rewritten={rewritten} appended={appended}")
    CASES.append(("a living note over its cap, struck text and an unreached note are refused; a record may grow, never be rewritten",
                  "a bloated note, a narrated one, an orphan, and history edited back — each read as a normal file"))
    print("  ok    Markdown classes: living bounded and reachable, records append-only")
    with mutated("README.md", lambda s: s.replace("public on purpose", "public on purpose (was private)", 1)):
        case("a narrated line in a living note FAILS", "a note that tells its own history instead of the present",
             True, "narration in a living note", by='inv:markdown_is_bounded_and_preserved')


def lesson_flow_cases() -> None:
    """The ledger reaches design: route, learn, plan, decide and every place page carry the lesson and its move (3.44.0)."""
    import dirscope
    import knowledge
    owned = [lesson["failure"] for lesson in knowledge.lessons_for("scripts/enforce.py")]
    noise = knowledge.lessons_for("zzqqxx qqvvkk jjxxzz")  # tokens, not words: "nobody wrote" matched a real row
    page = dirscope.reference(".githooks")
    if "a_suffix_read_as_the_interpreter" not in owned or noise or "  - do: " not in page:
        raise SystemExit(f"FAIL lesson flow: owned={owned} noise={noise}")
    CASES.append(("a file's lessons include the shapes its own guards enforce, and a place page carries each trap's move",
                  "a ledger read only when someone asks, so the design it describes repeats the failure"))
    print("  ok    the ledger reaches route, learn, decide and each place page")


def private_terms_cases() -> None:
    """The owner's private names are refused from a list this tree never carries (3.45.0)."""
    import os

    import leaks
    term = "quux" + "fleetname"  # assembled, so the tree itself never contains the planted term
    with tempfile.TemporaryDirectory() as scratch, \
            mutated("README.md", lambda s: s.replace("public on purpose", f"public on purpose {term}", 1)):
        terms = Path(scratch, "terms.txt")
        terms.write_text(f"# the owner's names\n{term.upper()}\n")  # listed in another case: the match is case-blind
        saved = os.environ.get("THEA_PRIVATE_TERMS")
        try:
            os.environ["THEA_PRIVATE_TERMS"] = str(terms)
            refused = [e for e in leaks.leak_errors() if term.upper() in e]
            os.environ.pop("THEA_PRIVATE_TERMS")
            unset = [e for e in leaks.leak_errors() if term.upper() in e]
        finally:
            if saved is not None:
                os.environ["THEA_PRIVATE_TERMS"] = saved
    if not refused or unset:
        raise SystemExit(f"FAIL private terms: refused={refused} unset={unset}")
    CASES.append(("a private name in the tree is refused when the owner's untracked list names it",
                  "the owner's projects and routers written into a public atlas, found by a reader first"))
    print("  ok    private names are refused from a list the tree never carries")


def ledger_enforcer_cases() -> None:
    """A guard blind to a missing input, a dead owner, a stale skip, a phantom shipped module, a second
    sighting left in intake and an unranked sighting count are each refused (3.47.0).

    THE BLIND SKIP IS BUILT AT RUN TIME for the same reason callshape_cases builds its plants: a literal
    guard-shaped function here would be the defect, were test harnesses ever swept.
    """
    skip = ("\n\ndef _planted" + "_errors():\n    from pathlib import Path\n    if not Path('x').exists"
            + "():\n        return []\n    return ['x']\n")
    with mutated("scripts/doctor.py", lambda s: s + skip):
        case("a guard that passes when its input is missing is refused",
             "a check that answers a deleted input with the silence of a clean pass",
             True, "passes when its input is missing", by='inv:guards_see_their_input')
    with mutated("atlas.yaml", lambda s: s.replace("owned_by: contextcost.entry_cost_errors",
                                                   "owned_by: contextcost._no_such_owner", 1)):
        case("a skip whose declared owner is not in the tree is refused",
             "an exemption that outlived the guard it deferred to, a blind pass again",
             True, "contextcost._no_such_owner", by='inv:guards_see_their_input')
    with mutated("atlas.yaml", lambda s: s.replace("absent_input_owners:\n",
                                                   "absent_input_owners:\n  doctor.py:_gone_errors:\n"
                                                   "    reason: 'planted'\n", 1)):
        case("an owner row for a skip no longer in the tree is refused",
             "a stale exemption waiting for the next guard to borrow it", True, "no longer in the tree", by='inv:guards_see_their_input')
    with mutated("pyproject.toml", lambda s: s.replace('py-modules = ["atlas_cli"]',
                                                       'py-modules = ["atlas_cli", "no_such_module"]', 1)):
        case("a wheel shipping a module that does not exist is refused",
             "an import check over a missing file that passed because it read nothing",
             True, "scripts/no_such_module.py does not exist", by='contextcost.wheel_import_errors')
    with mutated("atlas.yaml", lambda s: s.replace(
            "    sightings: 2\n    unenforceable: which conditions",
            "    sightings: 2\n    intake: " + (ROOT / "VERSION").read_text().strip() + "\n    unenforceable: which conditions", 1)):
        case("a shape seen twice and still in intake is refused",
             "the second sighting deferred as if it were the first", True, "in intake at 2 sightings", by='inv:failure_modes_name_their_refusal')
    with mutated("atlas.yaml", lambda s: s.replace(
            "    sightings: 1\n    prevented_by: 'resolve paths", "    sightings: 0\n    prevented_by: 'resolve paths", 1)):
        case("a failure mode with no ranking sighting count is refused",
             "a shape sorted out of every summary because its count was not a count",
             True, "carries sightings 0", by='inv:failure_modes_name_their_refusal')


def changed_edge_cases() -> None:
    """`verify --changed` fails a diff that touches an enforcer no planted case names; a named one passes."""
    import inspect  # noqa: PLC0415

    import edges  # noqa: PLC0415
    ledger = Path(tempfile.mkdtemp()) / "edges.json"
    ledger.write_text('{"a case": "cross_reference_errors"}', encoding="utf-8")
    for enforcer, verdict in (("_identity_errors", "FAIL"), ("cross_reference_errors", "PASS")):
        first = inspect.getsourcelines(getattr(atlas, enforcer))[1]
        touch = lambda t, n=first: "\n".join(ln + "  # planted" * (i == n) for i, ln in enumerate(t.split("\n"), 1))  # noqa: E731
        with mutated("scripts/atlas.py", touch):
            row = edges.changed_row(["scripts/atlas.py"], ledger)
        if row["verdict"] != verdict:
            raise SystemExit(f"FAIL a diff touching {enforcer} gave {row['verdict']}, expected {verdict}: {row['why']}")
    if edges.changed_row(["scripts/atlasinv.py"], ledger)["verdict"] != "PASS":  # no diff: no line touched
        raise SystemExit("FAIL an unchanged tracked file read as every line touched")
    CASES.append(("a diff touching an enforcer no case names FAILS verify --changed", "an edited enforcer whose "
                  "only proof is a needle some other enforcer happens to print"))
    print("  ok    a diff touching an enforcer no case names FAILS verify --changed")

