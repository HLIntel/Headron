#!/usr/bin/env python3
"""brainstorm — a strategic brainstorm as a record a program can refuse: diverge, pre-mortem, converge, prove.

WHY (3.47.0). A brainstorm that lives in chat ends where the model's first idea was: one option, argued
for, with the alternatives named only to be dismissed. The failures that follow are the expensive ones —
a one-way door walked through without anyone owning it, an option chosen that another beat on every axis,
a plan that never said what would make it wrong. So the brainstorm is a FILE, and the discipline is checked:

  diverge     at least `min_options` options, one of them `do_nothing` — the baseline every option must beat
  score       every option scores every declared axis, -2..2, so the choice is made on axes and not on prose
  pre-mortem  every option says how it fails (`premortem`) and the signal that kills it (`kill_when`)
  converge    the chosen option is not DOMINATED (another option at least as good on every axis and better on
              one), and `because` names at least one axis
  one-way     `reversible: false` names an `approver` — an irreversible choice is escalated, never assumed
  prove       `next` names one step and the proof that it worked (a command, a number, an observable)

    thea brainstorm <record.yaml> [--json]     check a record; exit 0 only if every rule holds
    thea brainstorm --new "<question>"         print a skeleton record to fill in

WHAT IT DOES NOT PROVE: that the options are the right options or the scores honest — it proves the shape
that makes a bad choice visible: a missing baseline, an unowned one-way door, a dominated pick, no kill signal.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from atlascore import atlas, strict_yaml

SKELETON = """question: {question}
horizon: quarter            # now | quarter | year — how far the consequences reach
reversible: true            # false = a one-way door: name the approver below
approver: null
constraints: [the budget, the deadline, or the rule this must respect]
axes: [value, cost, risk, time_to_value]
options:
  do_nothing:
    thesis: what happens if nothing changes — the baseline every option must beat
    scores: {{value: 0, cost: 0, risk: 0, time_to_value: 0}}
    premortem: how standing still fails
    kill_when: the signal that says doing nothing has become the expensive choice
  option_a:
    thesis: one sentence
    scores: {{value: 1, cost: -1, risk: 0, time_to_value: 1}}
    premortem: the most likely way this fails, written as if it already had
    kill_when: the observable that makes you abandon it
  option_b:
    thesis: one sentence, genuinely different from option_a
    scores: {{value: 2, cost: -2, risk: -1, time_to_value: -1}}
    premortem: how it fails
    kill_when: when to stop
chosen: option_a
because: names the axis that decided it
next:
  step: the first concrete action
  proof: the command, number or observable that shows it worked
"""


def spec() -> dict:
    return dict(atlas().get("brainstorm") or {})


def _dominated(options: dict, chosen: str, axes: list[str]) -> str | None:
    """The option that beats `chosen` on every axis it scores and strictly on one, or None."""
    mine = (options.get(chosen) or {}).get("scores") or {}
    for name, opt in options.items():
        theirs = (opt or {}).get("scores") or {}
        if name != chosen and all(theirs.get(a, -9) >= mine.get(a, -9) for a in axes) \
                and any(theirs.get(a, -9) > mine.get(a, -9) for a in axes):
            return name
    return None


def record_errors(record: dict) -> list[str]:
    """Every rule the module docstring names, as findings. An empty list is a brainstorm that may converge."""
    floor = int(spec().get("min_options") or 3)
    errors: list[str] = []
    if not str(record.get("question") or "").strip():
        errors.append("no question — a brainstorm serves one decision, named first")
    axes = [str(a) for a in record.get("axes") or []]
    options = dict(record.get("options") or {})
    if len(axes) < 2:
        errors.append(f"{len(axes)} axis — options compared on one axis are a ranking, not a trade-off (want 2+)")
    if len(options) < floor:
        errors.append(f"{len(options)} option(s) — diverge to at least {floor} before converging")
    if "do_nothing" not in options:
        errors.append("no do_nothing option — without the baseline, every option looks like progress")
    for name, opt in options.items():
        opt = opt or {}
        scores = opt.get("scores") or {}
        missing = [a for a in axes if a not in scores]
        bad = [a for a, v in scores.items() if not isinstance(v, int) or not -2 <= v <= 2]
        errors += [f"option {name} does not score {', '.join(missing)}"] if missing else []
        errors += [f"option {name} scores {', '.join(bad)} outside -2..2"] if bad else []
        errors += [f"option {name} has no {f} — an option that cannot fail was not thought through"
                   for f in ("thesis", "premortem", "kill_when") if not str(opt.get(f) or "").strip()]
    vectors = {}
    for name, opt in options.items():
        vec = tuple((opt or {}).get("scores", {}).get(a) for a in axes)
        if vec in vectors and None not in vec:
            errors.append(f"options {vectors[vec]} and {name} score identically — the same option twice is not divergence")
        vectors.setdefault(vec, name)
    chosen = str(record.get("chosen") or "")
    if chosen not in options:
        errors.append(f"chosen '{chosen}' is not an option")
    elif not errors:
        beater = _dominated(options, chosen, axes)
        if beater:
            errors.append(f"chosen '{chosen}' is DOMINATED by '{beater}' — as good or better on every axis; pick it, or add the axis that separates them")
    because = str(record.get("because") or "").lower()
    if axes and not any(a.lower().replace("_", " ") in because.replace("_", " ") for a in axes):
        errors.append("`because` names no axis — the choice must be made on what was scored")
    if record.get("reversible") is False and not str(record.get("approver") or "").strip():
        errors.append("reversible: false with no approver — a one-way door is escalated, never assumed")
    nxt = record.get("next") or {}
    errors += [f"next has no {f} — a decision ends in a step and the proof it worked"
               for f in ("step", "proof") if not str(nxt.get(f) or "").strip()]
    return errors


def undiverged(record: dict) -> str:
    """process_conditions/options_undiverged: fewer options than the floor, or no do_nothing baseline."""
    return next((e for e in record_errors(record) if "option(s)" in e or "do_nothing" in e), "")


def dominated_choice(record: dict) -> str:
    """process_conditions/choice_dominated: another option is at least as good on every axis."""
    return next((e for e in record_errors(record) if "DOMINATED" in e), "")


def one_way_door(record: dict) -> str:
    """process_conditions/one_way_door: irreversible with no approver — escalate, never assume."""
    return next((e for e in record_errors(record) if "one-way door" in e), "")


def main(argv: list[str]) -> int:
    if argv[:1] == ["--new"]:
        print(SKELETON.format(question=" ".join(argv[1:]) or "the decision this serves, in one sentence"), end="")
        return 0
    paths = [a for a in argv if not a.startswith("--")]
    if len(paths) != 1:
        print(__doc__)
        return 2
    record = strict_yaml(Path(paths[0]).read_text(encoding="utf-8"), paths[0]) or {}
    errors = record_errors(record)
    if "--json" in argv:
        print(json.dumps({"schema": "thea-brainstorm/1", "record": paths[0], "chosen": record.get("chosen"),
                          "findings": errors}, indent=2))
    else:
        for e in errors:
            print(f"  REFUSED {e}")
        print(f"brainstorm: {len(record.get('options') or {})} option(s), {len(record.get('axes') or [])} axes, "
              f"{len(errors)} finding(s) — " + (f"converge on {record.get('chosen')}" if not errors else "not ready to converge"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
