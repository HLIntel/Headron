#!/usr/bin/env python3
"""Does Thea make a model better at work OTHER than routing? Blind against with-Thea, per task kind.

WHY (2.29.0). `abtest.py` asks which command or pack answers a file — one narrow skill. The owner
asked whether Thea improves reasoning, process, rule-following and more. Only a task whose correct
answer THIS REPOSITORY DECLARES can be scored without a judge, so each kind below reads its ground
truth from the tree:

  diagnose  REASONING. Given what a failure looks like from outside (`agent_failure_modes/looks_like`),
            name the failure mode. Blind gets the mode ids; with Thea gets each id beside its
            mechanism (`shape`). The model still has to go from symptom to cause.
  plan      PROCESS. Given a described change, list every gate that must pass before merge. Blind
            gets every gate name; with Thea gets `verification_policy/profiles`. The description
            never names the change class, so the model must classify before it can look anything up.
  hygiene   RULE-FOLLOWING. Would this repository's build refuse a sentence? Blind is told only that
            rules exist; with Thea gets the two rules that decide it. Labels come from the SAME
            patterns the build runs, and the run refuses if a fixture's label disagrees with them.

NOT MEASURED, AND SAID SO: visual design, open-ended strategy and arithmetic. Nothing in this tree
declares a right answer for them, and a judge model would score its own taste. A kind is added here
only when its ground truth is a declaration.

THE FIXTURES FOR `plan` AND `hygiene` ARE AUTHORED — written to exercise each class and each rule,
counted in K like every other choice. Results are a SAMPLE per model and phrasing, never an edge.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from atlascore import ROOT, atlas

# One plain description per change class. None names its class, a gate or a tool.
PLAN_CASES = {
    "source_change": "Rename a private helper inside one module and update its three call sites.",
    "api_change": "Add a required field to the JSON body a public HTTP endpoint accepts.",
    "dependency_change": "Upgrade the HTTP client library from one minor version to the next and re-lock.",
    "security_sensitive": "Change how session tokens are compared when a user signs in.",
    "concurrency_change": "Let the job queue run four workers in parallel instead of one.",
    "performance_change": "Replace a linear scan with an index to make search faster on large inputs.",
    "retrieval_change": "Change how documents are split into chunks before they are embedded for search.",
    "quantum_change": "Swap the circuit's entangling layer for a shallower one on the simulator.",
}

KINDS: list[str] = ["diagnose", "plan", "hygiene"]
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")  # the same pattern atlas.dated_claim_errors applies


def _date_parts() -> tuple[str, str]:
    # ASSEMBLED, never typed: a literal date in this tracked file would fail the rule it tests.
    return "-".join(("2026", "03", "14")), "-".join(("2025", "11", "02"))


def hygiene_cases() -> list[tuple[str, bool]]:
    """(sentence, would the build refuse it). Each label is RE-DERIVED below and must agree."""
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    old = ".".join(str(max(int(x) - 1, 0)) for x in version.split("."))
    d1, d2 = _date_parts()
    cases = [
        (f"Measured on {d1}: the router answered every task.", True),
        (f"The cache was cleared on {d2} and has not grown since.", True),
        (f"See https://example.org/notes/{d1}/report for the raw data.", False),
        ("Measured at contract v1.0.0: the router answered every task.", False),
        (f"This is Thea, contract v{old}.", True),
        (f"This is Thea, contract v{version}.", False),
        ("The router answered every task in the fixed set.", False),
        (f"Since contract v{old} the parser refuses ambiguous input.", False),
        (f"Release notes, {d2}: three new packs.", True),
        ("Stamp every claim with the contract version it was measured at.", False),
    ]
    for sentence, refused in cases:
        dated = any(_DATE.search(t) and not t.startswith(("http://", "https://")) for t in sentence.split())
        stale = any(m.group(2) != version and (m.group(1) or "").strip().lower() not in {"at", "since"}
                    for m in re.finditer(r"(\w+\s+)?contract v(\d+\.\d+\.\d+)", sentence))
        if (dated or stale) != refused:
            raise SystemExit(f"fixture label disagrees with the build's own rule: {sentence!r}")
    return cases


def questions() -> list[dict]:
    """Every question, both arms, and the check that scores it."""
    data = atlas()
    rows: list[dict] = []
    modes = data.get("agent_failure_modes") or {}
    ids = ", ".join(sorted(modes))
    catalogue = "\n".join(f"- {k}: {v.get('shape', '')}" for k, v in sorted(modes.items()))
    for mode, spec in sorted(modes.items()):
        # `tell` — the ONE observable that separates this mode from its neighbours. Added at 2.29.0 after
        # Sonnet, holding the whole catalogue, mis-named 13 of 27: most short symptoms ("a clean pass")
        # fit five modes. TUNED ON SONNET'S MISSES ONLY; Haiku and Opus are the held-out check.
        seen = spec.get("looks_like", "") + (f"; concretely, {spec['tell']}" if spec.get("tell") else "")
        ask = (f"An engineer reports this, and nothing more: \"{seen}\"\n"
               "Which failure mode is it? Answer with ONLY its id.")
        rows.append({"kind": "diagnose", "task": mode, "truth": [mode],
                     "blind": f"Failure mode ids: {ids}\n\n{ask}",
                     "thea": f"Failure modes and their mechanisms:\n{catalogue}\n\n{ask}"})
    from agentpolicy import required_gates  # the RESOLVED policy — what `atlas plan` answers, extends included
    profiles = (data.get("verification_policy") or {}).get("profiles") or {}
    every_gate = ", ".join(sorted(data.get("gate_tools") or {}))

    def resolved(change: str) -> list[str]:
        return required_gates({"change_class": change, "risk_modifiers": []})
    table = "\n".join(f"- {k}: {', '.join(resolved(k))}" for k in sorted(profiles))
    for change, text in PLAN_CASES.items():
        required = resolved(change)
        ask = (f"The change: {text}\nList every gate that must pass before it merges, as gate names "
               "separated by commas. Nothing else.")
        rows.append({"kind": "plan", "task": change, "truth": required, "gates": list(data.get("gate_tools") or {}),
                     "blind": f"Gate names: {every_gate}\nYou do not have this project's policy; give your best "
                              f"guess — a guess is expected.\n\n{ask}",
                     "thea": f"Change classes and the gates each requires:\n{table}\n\n{ask}"})
    rules = ("Rule A: a calendar date (YYYY-MM-DD) in a tracked document is refused, unless it is part "
             "of a URL. Rule B: a typed 'contract vX.Y.Z' must equal the current version "
             f"({(ROOT / 'VERSION').read_text(encoding='utf-8').strip()}) unless preceded by 'at' or 'since'.")
    for i, (sentence, refused) in enumerate(hygiene_cases()):
        ask = f"Would this repository's build refuse this line in a document?\n\"{sentence}\"\nAnswer yes or no."
        rows.append({"kind": "hygiene", "task": f"h{i}", "truth": ["yes" if refused else "no"],
                     "blind": ("You cannot see this repository's rules. Give your best guess from what documentation "
                               f"builds commonly refuse; a guess is expected.\n\n{ask}"),
                     "thea": f"{rules}\n\n{ask}"})
    return rows


def score(row: dict, answer: str) -> bool | None:
    """True, False, or None when the answer is not an answer at all. A None is never scored as wrong:
    FOUND AT 2.29.0, blind models DECLINED the yes/no questions, and a 0% blind arm read as a finding
    when it measured the prompt. None blocks the run from being recorded until the prompt is fixed."""
    text = " ".join(answer.lower().split())
    if row["kind"] == "hygiene":
        # THE FIRST yes/no ON THE FIRST LINE. Matching only the first WORD read "# Answer: No" as a
        # non-answer (2.29.0) — a scorer defect that blocked a run, found by printing the misses.
        first = re.search(r"\b(yes|no)\b", " ".join(answer.lower().strip().splitlines()[:1]))
        return None if not first else first.group(1) == row["truth"][0]
    if row["kind"] == "plan":
        # EVERY required gate named, and no dumping: listing all the gates would pass "every required
        # is present" while planning nothing, so the answer may name at most two extras.
        named = {g.strip(" .`*") for g in re.split(r"[,\n]", text) if g.strip(" .`*")}
        if not named & set(row["gates"]):
            return None  # names no gate at all: a decline, not a plan — never scored as a wrong one
        return set(row["truth"]) <= named and len(named) <= len(row["truth"]) + 2
    return row["truth"][0] in text


def run(provider: str, model: str, timeout: int, max_tokens: int, misses: bool = False) -> dict:
    import providers
    from abtest import _reader_lock  # SHARED with abtest: the mutating suite never plants into a question
    _held = _reader_lock()  # noqa: F841 — held for the whole run
    kinds: dict[str, dict] = {}
    wanted = set(KINDS)
    for row in (r for r in questions() if r["kind"] in wanted):
        for arm in ("blind", "thea"):
            answer, tokens = providers.complete(provider, model, row[arm], timeout, max_tokens)
            cell = kinds.setdefault(row["kind"], {}).setdefault(arm, {"correct": 0, "asked": 0, "tokens": 0, "unanswered": 0})
            cell["asked"] += 1
            cell["tokens"] += tokens or 0
            verdict = score(row, answer) if answer.strip() else None
            cell["unanswered"] += int(verdict is None)
            cell["correct"] += int(bool(verdict))
            if misses and not verdict:
                print(f"  MISS {row['kind']}/{arm} {row['task']}: wanted {row['truth']}, got {answer.strip()[:160]!r}")
    return {"provider": provider, "model": model, "kinds": kinds}


def record(result: dict) -> None:
    import fcntl
    path = ROOT / "benchmarks" / "tasks-latest.json"
    with open(path.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        evidence = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "_why": "taskbench.py's recorded result: blind against with-Thea on reasoning, process and "
                    "rule-following tasks whose answers the tree declares. Re-run per model; a sample, not an edge.",
            "models": {}}
        evidence["models"][f"{result['provider']}:{result['model']}"] = {
            "measured_at": str(atlas().get("version")), **result["kinds"]}
        path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="taskbench.py", description=__doc__.split("\n", 1)[0])
    parser.add_argument("--provider", default="claude-cli")
    parser.add_argument("--model", default="haiku", help="comma-separated")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=400, dest="max_tokens")
    parser.add_argument("--record", action="store_true", help="write benchmarks/tasks-latest.json")
    parser.add_argument("--list", action="store_true", help="print the question count per kind and exit")
    parser.add_argument("--misses", action="store_true",
                        help="print every wrong or non-answer: a bad result is diagnosed on the run that produced it")
    parser.add_argument("--kinds", default="diagnose,plan,hygiene", help="comma-separated subset")
    args = parser.parse_args(argv)
    KINDS[:] = [k.strip() for k in args.kinds.split(",") if k.strip()]
    rows = questions()
    counts = {k: sum(r["kind"] == k for r in rows) for k in ("diagnose", "plan", "hygiene")}
    print(f"questions: {counts} — K={2 * len(rows)} per model (two arms)")
    if args.list:
        return 0
    failed = 0
    for model in (m.strip() for m in args.model.split(",") if m.strip()):
        try:
            result = run(args.provider, model, args.timeout, args.max_tokens, args.misses)
        except (OSError, ValueError, KeyError) as exc:
            print(f"- {model}: REFUSED, partial sample not reported ({type(exc).__name__}: {exc})")
            failed = 1
            continue
        empty = sum(c["unanswered"] for k in result["kinds"].values() for c in k.values())
        print(f"model {model} ({args.provider}){' — ' + str(empty) + ' empty answers, NOT recorded' if empty else ''}")
        for kind, arms in result["kinds"].items():
            b, t = arms["blind"], arms["thea"]
            print(f"  {kind:<9} blind {b['correct']}/{b['asked']}  with Thea {t['correct']}/{t['asked']}"
                  f"  | tokens/question {b['tokens'] / b['asked']:.0f} vs {t['tokens'] / t['asked']:.0f}")
        # A BAD RESULT IS FIXED, NOT RECORDED. Thea scoring below blind on any kind means the question,
        # the data or the policy is wrong — diagnose it with --misses on this run. Never caption it.
        worse = [k for k, a in result["kinds"].items() if a["thea"]["correct"] < a["blind"]["correct"]]
        if worse:
            print(f"  REFUSED to record: with Thea scored below blind on {', '.join(worse)} — fix the cause first")
        if args.record and not empty and not worse:
            record(result)
        failed |= int(bool(empty or worse))
    print("SCOPE: reasoning, process and rule-following with declared answers only. Design, open-ended\n"
          "       strategy and arithmetic are NOT measured: nothing here declares a right answer for them.")
    return failed


if __name__ == "__main__":
    sys.exit(main())
