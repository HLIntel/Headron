#!/usr/bin/env python3
"""instrument_roster: which scripts are instruments, and which instrument no gate reaches.

Split out of atlasinv.py at 3.31.0, which reached its line cap — a cap is never raised to fit new code.

TWO MEASUREMENTS EARNED THIS FILE. The roster's denominator was `scripts/*.py`, an enumeration BY
SUFFIX, and `heavyidle.mjs` is a declared instrument that sat OUTSIDE its own completeness check, so a
second non-Python script needed no row and nothing would have fired. And five instruments were
reachable by no gate and no invariant while not one of them said so anywhere — an unshipped arm reads
as covered, which is the shape this repository refuses in every other roster.

BOTH ROSTERS ARE DERIVED, NOT TYPED. The scripts come from the directory by exclusion, so a new script
of any language is counted and fails loudly until declared. The reachable set is the transitive import
closure of the gates themselves plus every script a workflow names, so it cannot narrow by hand.

WHAT THIS DOES NOT PROVE. That a reached instrument is reached USEFULLY — only that a path to it
exists. The closure errs toward calling something reached, because over-counting hides a finding while
under-counting fires on correct code and gets the guard switched off.
"""
from __future__ import annotations

import sys

from atlascore import ROOT, atlas, parsed_python, rel


def instrument_scripts() -> list:
    """Every file under scripts/ that is a script, by EXCLUSION rather than by suffix.

    The suffix version excluded `heavyidle.mjs`, a declared instrument, from its own completeness
    check — so a second non-Python script needed no row and nothing fired. Excluding declared data
    files instead means a new script of ANY language is counted and fails loudly until it is declared,
    and a new data file fails loudly until it is named with its reason. Loud both ways beats an
    extension list that silently stops looking (code-quality §8).
    """
    import dirscope  # noqa: PLC0415
    excluded = set((atlas().get("instrument_roster") or {}).get("not_a_script") or {})
    # A GENERATED PER-DIRECTORY READ IS NOT AN UNDECLARED SCRIPT. Excluded by DERIVATION from
    # directory_scopes rather than by a typed row: a hand-written exclusion here would be a second
    # declaration of that roster, and this file exists because the first version of this denominator
    # enumerated by suffix and stopped looking.
    generated = {ref.split("/", 1)[1] for ref in dirscope.generated_references() if ref.startswith("scripts/")}
    return sorted(p for p in (ROOT / "scripts").iterdir()
                  if p.is_file() and not p.name.startswith(".")
                  and p.name not in excluded and p.name not in generated)

def instrument_roster_errors() -> tuple[list[str], int, int]:
    """(errors, declared instruments resolving to a script here, scripts present) — both counts travel
    with the verdict, because refusing 0 of 0 and 0 of many print the same 0."""
    errors: list[str] = []
    instruments = atlas().get("instruments") or {}
    claimed = {str(spec.get("script")) for spec in instruments.values() if isinstance(spec, dict)}
    for name, spec in instruments.items():
        if not isinstance(spec, dict):
            errors.append(f"atlas.yaml/instruments/{name} is not a mapping")
            continue
        for field in ("script", "proves", "does_not_prove", "closed_by"):
            if not str(spec.get(field) or "").strip():
                errors.append(f"instrument '{name}' leaves '{field}' empty — a limit with no owner "
                              "is the blind spot this roster exists to make unrepresentable")
        script = str(spec.get("script") or "")
        if script and not (ROOT / script).exists():
            errors.append(f"instrument '{name}' names a file that does not exist: {script}")
    present = instrument_scripts()
    for path in present:
        if rel(path) not in claimed:
            errors.append(f"{rel(path)} is in the tree and named by no atlas.yaml/instruments entry "
                          f"(declare it, or name it under instrument_roster/not_a_script with its reason)")
    for excluded, reason in sorted(((atlas().get("instrument_roster") or {}).get("not_a_script") or {}).items()):
        if not str(reason or "").strip():
            errors.append(f"instrument_roster/not_a_script/{excluded} states no reason — an exemption "
                          f"without its reason inline is a snooze button")
        elif not (ROOT / "scripts" / excluded).exists():
            errors.append(f"instrument_roster/not_a_script names {excluded}, which is not in scripts/ — "
                          f"a stale exemption hides the next file that lands on that name")
    return errors, len(claimed & {rel(p) for p in present}), len(present)

def _import_closure(seeds: set[str]) -> set[str]:
    """Every module stem reachable from `seeds` by a static import, plus by a subprocess that names a
    script path. Derived from the syntax tree, never from a hand-written list, because a roster of
    reachable modules narrows the moment one is added beside it."""
    import ast as _ast
    reached, frontier = set(seeds), list(seeds)
    while frontier:
        stem = frontier.pop()
        source = ROOT / "scripts" / f"{stem}.py"
        if not source.is_file():
            continue
        tree = parsed_python(source.read_text(encoding="utf-8"), str(source))
        if tree is None:
            continue
        found: set[str] = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.Import):
                found |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, _ast.ImportFrom) and node.module and node.level == 0:
                found.add(node.module.split(".")[0])
            elif isinstance(node, _ast.Constant) and isinstance(node.value, str):
                # A SUBPROCESS NAMES ITS SCRIPT AS A STRING, and three shapes were missed by a probe
                # that only read "scripts/<name>.py": a path built from parts (`ROOT / "scripts" /
                # "check_contract.py"`), a bare module stem (`LAUNCHER = "atlas_cli"`), and a path
                # prefixed by a checkout directory. Any constant naming a file or stem under scripts/
                # counts. This errs toward calling something REACHED, which is the safe direction for
                # a guard: over-counting hides a finding, under-counting fires on correct code.
                text = node.value.strip()
                if "/" in text or " " in text:
                    text = text.rsplit("/", 1)[-1]
                stem = text.rsplit(".", 1)[0] if text.endswith((".py", ".mjs")) else text
                if stem and " " not in stem and ((ROOT / "scripts" / f"{stem}.py").is_file()
                                                 or (ROOT / "scripts" / f"{stem}.mjs").is_file()):
                    found.add(stem)
        for name in found - reached:
            if (ROOT / "scripts" / f"{name}.py").is_file() or (ROOT / "scripts" / f"{name}.mjs").is_file():
                reached.add(name)
                frontier.append(name)
    return reached

def instrument_reach_errors() -> list[str]:
    """Every instrument is reached by a gate or an invariant, or says here why it is not.

    MEASURED at 3.31.0: four of the declared instruments were reachable by neither, and not one of
    them said so anywhere — an unshipped arm reads as covered, which is the shape this repository
    refuses in every other roster. The seeds are the gates themselves plus the scripts named in a
    workflow, so the closure is derived and cannot narrow by hand.
    """
    errors: list[str] = []
    policy = atlas().get("verification_policy") or {}
    seeds: set[str] = set()
    for gate in policy.get("done_set") or []:
        for token in (gate or {}).get("argv") or []:
            text = str(token)
            if text.startswith("scripts/"):
                seeds.add(text.rsplit("/", 1)[-1].rsplit(".", 1)[0])
    for workflow in sorted((ROOT / ".github/workflows").glob("*.yml")):
        for line in workflow.read_text(encoding="utf-8").splitlines():
            for word in line.replace("'", " ").replace('"', " ").split():
                # A WORKFLOW MAY PREFIX A CHECKOUT DIRECTORY: `.atlas-checkout/scripts/atlasci.py` is
                # the same instrument as `scripts/atlasci.py`, and requiring the prefix missed it.
                if "scripts/" in word and word.endswith((".py", ".mjs")):
                    seeds.add(word.rsplit("/", 1)[-1].rsplit(".", 1)[0])
    if not seeds:
        return ["instrument reachability found no seed gate or workflow at all — an empty closure "
                "would report every instrument as unreached, which is a broken probe, not a finding"]
    reached = _import_closure(seeds)
    declared = dict((atlas().get("instrument_roster") or {}).get("unreached") or {})
    for name, spec in sorted((atlas().get("instruments") or {}).items()):
        script = str((spec or {}).get("script") or "")
        if not script.startswith("scripts/"):
            continue
        stem, base = script.rsplit("/", 1)[-1].rsplit(".", 1)[0], script.rsplit("/", 1)[-1]
        if stem in reached or base in declared:
            continue
        errors.append(f"instrument '{name}' ({script}) is reached by no gate and no invariant, and "
                      f"instrument_roster/unreached does not say why — wire it, delete it, or declare "
                      f"what it costs and what would run it")
    for base, reason in sorted(declared.items()):
        stem = base.rsplit(".", 1)[0]
        if not str(reason or "").strip():
            errors.append(f"instrument_roster/unreached/{base} states no reason — an exemption without "
                          f"its reason inline is a snooze button")
        elif stem in seeds:
            # THE EXACT SEEDS, NOT THE INFERRED CLOSURE. A declared row goes stale when a GATE or a
            # WORKFLOW names the script — both exact. The closure is deliberately loose (any constant
            # naming a script counts), and at 3.31.0 that looseness read a planted suite's own mutation
            # STRING as evidence that heavyidle.mjs was reached, so this check fired on a correct tree.
            # Loose is right for deciding an undeclared instrument is reached, because over-counting
            # hides a finding; it is wrong for retiring a declared row, because it invents one.
            errors.append(f"instrument_roster/unreached names {base}, which a gate or workflow now "
                          f"names directly — remove the row, or the next genuinely unreached "
                          f"instrument hides behind it")
        elif not (ROOT / "scripts" / base).exists():
            errors.append(f"instrument_roster/unreached names {base}, which is not in scripts/")
    return errors


def main() -> int:
    """Both verdicts with both coverages, because 0 of 0 and 0 of many print the same 0."""
    roster, named, present = instrument_roster_errors()
    reach = instrument_reach_errors()
    for line in roster + reach:
        print(f"- {line}")
    declared = len((atlas().get("instrument_roster") or {}).get("unreached") or {})
    print(f"{named} of {present} script(s) under scripts/ are declared instruments; "
          f"{declared} declared unreached with a reason")
    return 1 if roster or reach else 0


if __name__ == "__main__":
    sys.exit(main())
