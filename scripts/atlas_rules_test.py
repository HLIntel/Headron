#!/usr/bin/env python3
"""The rules that guard THIS HARNESS: its YAML shape, its own plants, and its forbidden-call table.

Split out of atlas_guards_test.py at 3.31.0 because that file reached the 1000-line cap, and a cap is
never raised to fit new code. Same contract as its sibling: each case plants a real defect, asserts the
build refuses it, and registers into the RUNNING suite's counted CASES — so a skipped case moves the
asserted total instead of disappearing quietly.
"""
from __future__ import annotations

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
