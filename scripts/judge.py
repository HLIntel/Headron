"""`thea judge` — a small decision asked as a closed question, acted on only above a declared bar.

    thea judge                                   every judgment: kind, bar, question
    thea judge <id>                              the card: what each answer means, the bar, what happens below it
    thea judge <id> <answer> <p> [--fact F]...   ONE line; exit 0 act · 3 below the bar · 2 refused
    thea judge <id> --fact F                     a declared fact forces its answer, no probability needed
    thea judge <id> [<answer> <p>] --state TEXT|-   the student rung answers from the state when the attached
                                                 bundle puts <id> on it and verifies; else the caller's answer
                                                 and p (the existing rung) do, and the line names the rung
    thea judge --calibrate <tsv> [--strict]      rows `id<TAB>answer<TAB>p<TAB>pass|fail`; exit 1 when a bar does not hold;
                                                 --strict also exits 1 when a bar holds on the point but not on its lower bound

The records are systems/judgments.yaml. No model is called here: the caller brings the answer and the
probability, or the student rung's micro pack answers in-process (model.py; no key, no port), and this decides
only what code may do with them. The student's p is its calibrated probability and is held to the same bar. A probability is believed; a fact is
checked — so a declared fact overrides any probability, and an undeclared fact is refused rather than
ignored (a misspelt fact silently ignored is a hard rule that never fires).
"""

from __future__ import annotations

import sys

KINDS = ("yes_no", "choice", "score")
FIELDS = ("kind", "asks", "act_at", "below", "verified_by", "prevents")
# Below this many acted-on rows a bar is UNMEASURED, never "holding": a bar that clears five rows
# proves nothing about the sixth. Calibration prints the count beside every verdict.
MIN_ROWS = 20
Z95 = 1.96  # the lower bound is one-sided in effect: Wilson 95% interval, lower end


def wilson_lower(right: int, n: int, z: float = Z95) -> float:
    """Lower end of the Wilson interval on a rate: what the data still supports once n is counted."""
    if n == 0:
        return 0.0
    phat = right / n
    centre = phat + z * z / (2 * n)
    spread = z * ((phat * (1 - phat) + z * z / (4 * n)) / n) ** 0.5
    return (centre - spread) / (1 + z * z / n)


def clean_run(bar: float, z: float = Z95) -> int:
    """Fewest acted rows, all right, whose lower bound reaches the bar: n >= z^2 * bar / (1 - bar)."""
    return int(z * z * bar / (1 - bar)) + 1 if bar < 1 else 0


def records() -> dict:
    from knowledge import system_records  # noqa: PLC0415

    return system_records("judgments")


def answers(spec: dict) -> list[str]:
    return ["yes", "no"] if spec.get("kind") == "yes_no" else [str(o) for o in spec.get("options") or []]


def meanings(spec: dict) -> dict[str, str]:
    if spec.get("kind") == "yes_no":
        return {"yes": str(spec.get("true_when")), "no": str(spec.get("false_when"))}
    return {str(k): str(v) for k, v in (spec.get("when") or {}).items()}


def judgment_record_errors() -> list[str]:
    """Every judgment is closed, every answer has a meaning, and its bar is above a coin flip."""
    recs = records()
    if not recs:
        return ["systems/judgments.yaml holds no judgments"]
    from atlascore import atlas  # noqa: PLC0415

    failures = set(atlas().get("agent_failure_modes") or {})
    errors: list[str] = []
    for name, spec in recs.items():
        spec = spec or {}
        errors += [f"judgment {name} declares no {f}" for f in FIELDS if spec.get(f) in (None, "")]
        if spec.get("kind") not in KINDS:
            errors.append(f"judgment {name} kind '{spec.get('kind')}' is not one of {', '.join(KINDS)}")
            continue
        offered = answers(spec)
        if len(offered) < 2:
            errors.append(f"judgment {name} offers fewer than two answers")
            continue
        means = meanings(spec)
        errors += [
            f"judgment {name} answer '{a}' has no declared meaning"
            for a in offered
            if means.get(a) in (None, "None", "")
        ]
        errors += [
            f"judgment {name} gives a meaning to '{a}', which is not one of its answers"
            for a in means
            if a not in offered
        ]
        bar = spec.get("act_at")
        if not isinstance(bar, (int, float)) or not 1 / len(offered) < bar <= 1:
            errors.append(
                f"judgment {name} act_at {bar} must be above 1/{len(offered)} (a guess clears it) and at most 1"
            )
        below = str(spec.get("below") or "")
        if below not in ("ask", "escalate") and not (below.startswith("default:") and below[8:] in offered):
            errors.append(f"judgment {name} below '{below}' is not ask, escalate or default:<one of its answers>")
        errors += [
            f"judgment {name} fact {f} forces '{a}', which is not one of its answers"
            for f, a in (spec.get("hard") or {}).items()
            if str(a) not in offered or not isinstance(a, str)
        ]
        if spec.get("prevents") and str(spec.get("prevents")) not in failures:
            errors.append(
                f"judgment {name} prevents '{spec.get('prevents')}', which is not in atlas.yaml/agent_failure_modes"
            )
    return errors


def card(name: str, spec: dict) -> int:
    print(f"{name} ({spec['kind']}): {spec['asks']}")
    for answer, means in meanings(spec).items():
        print(f"  {answer:<14} {means}")
    hard = ", ".join(f"{f} → {a}" for f, a in (spec.get("hard") or {}).items()) or "none"
    print(f"act at p ≥ {spec['act_at']} · below: {spec['below']} · facts: {hard}")
    print(f"scored by: {spec['verified_by']}")
    return 0


def verdict(name: str, spec: dict, answer: str | None, p: str | None, facts: list[str], rung: str = "") -> int:
    hard = {str(f): str(a) for f, a in (spec.get("hard") or {}).items()}
    unknown = [f for f in facts if f not in hard]
    if unknown:
        print(f"refused: fact {', '.join(unknown)} is not declared for {name} (declared: {', '.join(hard) or 'none'})")
        return 2
    forced = {hard[f] for f in facts}
    if len(forced) > 1:
        print(f"refused: facts {', '.join(facts)} force different answers ({', '.join(sorted(forced))})")
        return 2
    if forced:
        print(f"{name} = {forced.pop()} (fact {', '.join(facts)}) → act")
        return 0
    if answer is None or p is None:
        return card(name, spec)
    if answer not in answers(spec):
        print(f"refused: '{answer}' is not an answer to {name} ({', '.join(answers(spec))})")
        return 2
    try:
        prob = float(p)
    except ValueError:
        prob = -1.0
    if not 0 <= prob <= 1:
        print(f"refused: p '{p}' is not a probability in [0, 1]")
        return 2
    if prob >= float(spec["act_at"]):
        print(f"{name} = {answer} p={prob:g} → act{rung}")
        return 0
    below = str(spec["below"]).replace("default:", "default ")
    print(f"{name} = {answer} p={prob:g} < {spec['act_at']} → {below}{rung}")
    return 3


def student_rung(name: str, spec: dict, answer: str | None, p: str | None, state: str, to: str | None) -> int:
    """The student answers when the bundle puts `name` on its rung and verifies; otherwise the caller's answer and p
    answer on the rung the manifest declares (rules when no bundle verifies). The line always names the rung."""
    from model import student  # noqa: PLC0415

    got = student(name, sys.stdin.read() if state == "-" else state, to)
    if got.get("verdict") != "NOT RUN":
        return verdict(name, spec, got["answer"], str(got["p"]), [], f" · rung student ({got['bundle']})")
    fallback = got["rung"] if got["rung"] in ("rules", "teacher") else "rules"
    if answer is None or p is None:
        print(f"refused: {name} student NOT RUN ({got['why']}) and no answer and p for the {fallback} rung")
        return 2
    return verdict(name, spec, answer, p, [], f" · rung {fallback} (student NOT RUN: {got['why']})")


def _rows(path: str, recs: dict) -> tuple[list[tuple[str, str, float, bool]], str | None]:
    rows = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) != 4 or parts[0] not in recs or parts[3] not in ("pass", "fail"):
            return [], f"line {n}: want id<TAB>answer<TAB>p<TAB>pass|fail with a known id, got {line.strip()!r}"
        try:
            rows.append((parts[0], parts[1], float(parts[2]), parts[3] == "pass"))
        except ValueError:
            return [], f"line {n}: p '{parts[2]}' is not a number"
    return rows, None


def calibrate(path: str, strict: bool = False) -> int:
    """Does each bar hold on what happened? Acted-on rows must be right at least act_at of the time.

    A point rate over 20 rows can clear a bar by luck, so each held bar also prints its Wilson lower bound:
    PROVEN when the bound clears the bar too, NOT PROVEN when only the point does (--strict fails those)."""
    recs = records()
    rows, problem = _rows(path, recs)
    if problem:
        print(f"refused: {path} {problem}")
        return 2
    print(f"{len(rows)} rows over {len({r[0] for r in rows})} of {len(recs)} judgments")  # the roster it read
    failed = 0
    for name in sorted({r[0] for r in rows}):
        mine = [r for r in rows if r[0] == name]
        bar = float(recs[name]["act_at"])
        acted = [r for r in mine if r[2] >= bar]
        brier = sum((r[2] - r[3]) ** 2 for r in mine) / len(mine)
        head = f"{name:<20} n={len(mine):<4} acted={len(acted):<4} brier={brier:.3f}"
        if len(acted) < MIN_ROWS:
            print(f"{head} unmeasured (acted < {MIN_ROWS})")
            continue
        right = sum(r[3] for r in acted) / len(acted)
        low = wilson_lower(sum(r[3] for r in acted), len(acted))
        if right >= bar:
            if low >= bar:
                print(f"{head} right={right:.2f} ≥ {bar} bar holds · lower bound {low:.2f} ≥ {bar} PROVEN")
                continue
            note = f"{head} right={right:.2f} ≥ {bar} bar holds · lower bound {low:.2f} < {bar} NOT PROVEN"
            print(f"{note} (a clean run proves it from {clean_run(bar)} acted rows)")
            failed += strict
            continue
        failed += 1

        def top(t: float) -> list:
            return [r for r in mine if r[2] >= t]

        def point(t: float) -> bool:
            return len(top(t)) >= MIN_ROWS and sum(r[3] for r in top(t)) / len(top(t)) >= bar

        thresholds = sorted({r[2] for r in mine})
        proven = [t for t in thresholds if point(t) and wilson_lower(sum(r[3] for r in top(t)), len(top(t))) >= bar]
        better = [t for t in thresholds if point(t)]
        if proven:
            fix = f"raise act_at to {proven[0]:.2f} (lower bound clears it)"
        elif better:
            fix = f"raise act_at to {better[0]:.2f} (point only: NOT PROVEN, a clean run needs {clean_run(bar)} rows)"
        else:
            fix = "no bar holds on this data — take `below` every time"
        print(f"{head} right={right:.2f} < {bar} BAR FAILS → {fix}")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="thea judge", description=(__doc__ or "").splitlines()[0])
    parser.add_argument("id", nargs="?")
    parser.add_argument("answer", nargs="?")
    parser.add_argument("p", nargs="?")
    parser.add_argument("--fact", action="append", default=[])
    parser.add_argument("--calibrate", metavar="TSV")
    parser.add_argument("--strict", action="store_true", help="with --calibrate: a bar proven only on the point fails")
    parser.add_argument("--state", default=None, help="the state the student answers from; - reads stdin")
    parser.add_argument("--to", default=None, help="where the bundle is: home | repo | DIR")
    args = parser.parse_args(argv)
    if args.calibrate:
        return calibrate(args.calibrate, args.strict)
    recs = records()
    if args.id is None:
        for name, spec in sorted(recs.items()):
            print(f"{name:<20} {spec.get('kind'):<7} p≥{spec.get('act_at'):<5} {spec.get('asks')}")
        print(f"{len(recs)} judgments; `thea judge <id>` for the card")
        return 0
    spec = recs.get(args.id)
    if not spec:
        print(f"unknown judgment: {args.id}\navailable: {', '.join(sorted(recs))}")
        return 2
    if args.state is not None and not args.fact:  # a declared fact is checked, so it beats every rung
        return student_rung(args.id, spec, args.answer, args.p, args.state, args.to)
    return verdict(args.id, spec, args.answer, args.p, args.fact)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
