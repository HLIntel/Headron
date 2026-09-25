#!/usr/bin/env python3
"""Does the atlas actually help a model? Three arms, one model, automatic scoring.

WHY THIS AND NOT `bench.py`. bench.py measures the ROUTER — it is deterministic and it proves the
routes are right. It cannot say whether a language model given this repository answers better than
the same model without it, because no model is involved. This runs one.

THE THREE ARMS, AND WHY THE THIRD IS THE ONE THAT MATTERS:

  unassisted   the question plus the names of the packs. Cheap, and it has to guess.
  routed       the question plus what `atlas route` returns for that file. Cheap AND specific.
  whole_tree   the question plus EVERY pack's declared tools. Accurate by brute force, and it is
               what an agent without a router actually has to read.

`routed` versus `unassisted` measures whether the atlas helps at all. `routed` versus `whole_tree`
is the token claim, and it is the only honest form of it: the atlas does not make a prompt smaller
than asking blind, it makes an ACCURATE answer cheap. Comparing a cheap wrong answer against an
expensive right one and calling the first efficient is the thing this file exists not to do.

SCORING IS MECHANICAL. Ground truth comes from the repository's own declarations — the route a
file resolves to, and the command that pack declares for a role. A substring match against a
declared string, with no judge and no rubric, so the number cannot drift with whoever reads it.

WHAT IT DOES NOT PROVE. One model, one phrasing, a handful of questions. It is evidence about
THIS model on THESE questions, it prints K and its own sample size, and a result from a single
phrasing is a sample and not an edge — the prompt is part of the experiment.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

import resilience
from atlascore import ROOT, route_targets

ENDPOINT = "http://127.0.0.1:8799/v1/chat/completions"
_ENDPOINT_BREAKER = resilience.Breaker(threshold=3, cooldown=60.0)


def _manifest(route: str) -> dict:
    from agentpolicy import pack_manifest
    return pack_manifest(route)


def _truth(route: str, gate: str = "unit_tests") -> str | None:
    """The command the CONTRACT resolves for a pack's unit tests — the answer a correct agent gives.

    The first version scored against the raw authority entry, which for eight packs is a LIBRARY
    rather than a command. The model answered with the real invocation and was marked wrong: the
    scorer was measuring whether the model would repeat a name, not whether it would produce
    something runnable. That is an instrument wrong in its scope, and it is in this repository's
    own failure ledger — found here by the instrument's own misses reading as model errors.
    """
    from agentpolicy import gate_command
    argv, _ = gate_command(route, gate)
    return " ".join(argv) if argv else None


def ask(model: str, prompt: str, timeout: int, provider: str = "freeroute",
        max_tokens: int = 120) -> tuple[str, int | None]:
    """(answer, prompt_tokens or None). Tokens come from the SERVER; a server that reports none gives
    None, and that question is left out of the token mean rather than counted as free."""
    import providers
    return providers.complete(provider, model, prompt, timeout, max_tokens)

def questions(limit: int, every_pack: bool) -> list[dict]:
    """The question set, with ground truth read from the tree rather than written down twice.

    `--all-packs` is the honest sample and the default is not. The benchmark tasks lean on the
    languages a model already knows, where its prior is strong and the atlas adds least; asking
    once per pack reaches the ones where the prior is weakest, which is exactly where a router
    earns anything. A result from the easy half only is a sample of the easy half.
    """
    rows: list[dict] = []
    if every_pack:
        for route in sorted(route_targets()):
            truth = _truth(route)
            if not truth:
                continue  # a pack whose gate resolves to nothing has no correct answer to score
            rows.append({"task": route, "target": f"languages/{route}/OPERATING.md",
                         "route": route, "truth": truth, "kind": "runner"})
            rows.append({"task": f"{route}:route", "target": f"languages/{route}/OPERATING.md",
                         "route": route, "truth": route, "kind": "route"})
            # A THIRD KIND, ADDED AT 2.27.0 BECAUSE THE FORMATTER GATE BECAME ANSWERABLE. Two
            # kinds meant two prompt shapes, and a suite that asks two shapes measures two shapes.
            # This one also exercises the 43 role resolutions that closing `runner` opened, so the
            # coverage work and the accuracy measurement are not independent claims about the tree.
            style = _truth(route, "formatter")
            if style:
                rows.append({"task": f"{route}:format", "target": f"languages/{route}/OPERATING.md",
                             "route": route, "truth": style, "kind": "formatter"})
        return rows[:limit]
    for path in sorted((ROOT / "benchmarks" / "tasks").glob("*.json")):
        task = json.loads(path.read_text(encoding="utf-8"))
        route = task.get("expected_route")
        if not route:
            continue  # the no-route tasks test the router, not a model's recall
        truth = _truth(route)
        if not truth:
            continue
        rows.append({"task": task["task_id"], "target": task["target"], "route": route,
                     "truth": truth})
    return rows[:limit]


def prompts(row: dict) -> dict[str, str]:
    return _prompts_for(row, row.get("kind", "runner"))


def _prompts_for(row: dict, kind: str) -> dict[str, str]:
    """The same question under three context regimes. Only the CONTEXT differs, never the ask."""
    # TWO QUESTION KINDS, because one measures recall of a command and the other measures ROUTING.
    # A suite that only ever asks the same shape of question measures that shape, and the arm that
    # wins is the one whose context happens to suit it.
    ask_line = f"File: {row['target']}\n" + {
        "runner": "Answer with ONLY the exact shell command this project declares for running that "
                  "file's tests. No prose, no explanation, no backticks.",
        "formatter": "Answer with ONLY the exact shell command this project declares for formatting "
                     "that file. No prose, no explanation, no backticks.",
        # "ONE WORD" WAS A DEFECT IN THE QUESTION, found at 2.28.0: a nested pack id is `quantum/silq`,
        # and Sonnet answering `silq` was OBEYING it. Fixed in the question, never by loosening the
        # scorer to accept a leaf, which would only make every model's number friendlier. It touched at
        # most one of 39 sampled questions per model; runs recorded before the fix carry the old wording.
        "route": "Answer with ONLY the id of the language pack that owns this file, exactly as the "
                 "project writes it (it may contain a slash). No prose.",
    }[kind]
    packs = ", ".join(sorted(route_targets()))
    manifest = _manifest(row["route"])
    routed = {"authority": manifest.get("authority") or {}, "runner": manifest.get("runner") or {}}
    # THE WHOLE-TREE ARM MUST CARRY WHAT THE QUESTION NEEDS, or it is not the brute-force arm, it
    # is a worse-informed one — and the token ratio would then be measured against a straw man.
    role = {"formatter": "formatter"}.get(kind, "test")
    whole = {target: {role: (_manifest(target).get("authority") or {}).get(role),
                      "runner": (_manifest(target).get("runner") or {}).get(role)}
             for target in sorted(route_targets())}
    return {
        "unassisted": f"The project supports these language packs: {packs}.\n\n{ask_line}",
        "routed": (f"`atlas route` resolved this file to the `{row['route']}` pack, whose declared "
                   f"tools are: {json.dumps(routed)}\n\n{ask_line}"),
        "whole_tree": (f"Every pack's declared {role}: {json.dumps(whole)}\n\n{ask_line}"),
        # THE FOURTH ARM, ADDED AT 2.27.0 ON A MEASURED HYPOTHESIS: `routed` hands over the pack's
        # WHOLE manifest — every role — when a question needs ONE. This is what `gate_resolution`
        # returns for the gate asked about, and nothing else. If it scores with `routed` at the
        # cost of `unassisted`, routing's accuracy is nearly free in tokens.
        "scoped": (f"`atlas route` resolved this file to the `{row['route']}` pack; its declared "
                   + (f"{role} command is: {_scoped(row['route'], kind)}"
                      if kind != "route" else "route id is that pack name")
                   + f"\n\n{ask_line}"),
    }


def _scoped(route: str, kind: str) -> str:
    """Exactly what one gate resolves to — the smallest record that answers the question."""
    from agentpolicy import gate_command
    argv, why = gate_command(route, {"formatter": "formatter"}.get(kind, "unit_tests"))
    return " ".join(argv) if argv else f"none ({why})"


def _reader_lock():
    """A SHARED lock beside atlas_test's exclusive one, so a measurement never reads a planted file.

    FOUND AT 2.27.0: this reads pack manifests for every prompt, and the mutating suite had been
    run alongside it — so any question could have been scored against a manifest carrying a
    planted defect. The suite takes the lock exclusively and refuses to start while this holds it;
    this waits while the suite holds it. Readers share, a writer excludes both.
    """
    import fcntl
    import subprocess as _sp
    where = _sp.check_output(["git", "rev-parse", "--git-path", "atlas-test.lock"], cwd=ROOT).decode().strip()
    handle = open(where if where.startswith("/") else ROOT / where, "w")  # noqa: SIM115
    fcntl.flock(handle, fcntl.LOCK_SH)
    return handle


def stratified(rows: list[dict], n: int, seed: int) -> list[dict]:
    """n questions, each KIND kept in proportion, chosen by a seeded shuffle. Taking the first n
    would take the alphabetically first packs — a sample of the start of the alphabet."""
    import random
    if n <= 0 or n >= len(rows):
        return rows
    kinds: dict[str, list[dict]] = {}
    for row in rows:
        kinds.setdefault(str(row.get("kind")), []).append(row)
    rng, picked = random.Random(seed), []
    for group in kinds.values():
        rng.shuffle(group)
        picked += group[:max(1, round(n * len(group) / len(rows)))]
    return picked


def run(model: str, limit: int, timeout: int, every_pack: bool = False, provider: str = "freeroute",
        arm_names: tuple[str, ...] = ("unassisted", "routed", "whole_tree", "scoped"), sample: int = 0,
        seed: int = 7, max_tokens: int = 120) -> dict:
    _held = _reader_lock()  # noqa: F841 — held for the whole run, released at exit
    rows = stratified(questions(limit, every_pack), sample, seed)
    arms: dict[str, dict] = {name: {"correct": 0, "tokens": 0, "asked": 0, "metered": 0, "unanswered": 0}
                            for name in arm_names}
    misses: list[str] = []
    for row in rows:
        for arm, prompt in prompts(row).items():
            if arm not in arms:
                continue
            try:
                answer, tokens = ask(model, prompt, timeout, provider, max_tokens)
            except (urllib.error.URLError, OSError, KeyError, ValueError, resilience.BreakerOpen) as exc:
                # REFUSE RATHER THAN REPORT A SHORT SAMPLE AS A FULL ONE.
                return {"error": f"{type(exc).__name__} talking to {provider}: {exc}"}
            arms[arm]["asked"] += 1
            if tokens is not None:
                arms[arm]["tokens"] += tokens
                arms[arm]["metered"] += 1
            # AN EMPTY ANSWER MEASURES THE OUTPUT CAP, NOT THE MODEL: counted apart, never as wrong.
            arms[arm]["unanswered"] += int(not answer.strip())
            hit = row["truth"].lower() in " ".join(answer.split()).lower()
            arms[arm]["correct"] += int(hit)
            if not hit and arm == "routed":
                misses.append(f"{row['task']}: wanted {row['truth']!r}, got {answer.strip()[:60]!r}")
    return {"model": model, "provider": provider, "questions": len(rows), "k": len(rows) * len(arms),
            "arms": arms, "routed_misses": misses,
            "chance": round(1 / max(len(route_targets()), 1), 4)}


def unanswered(result: dict) -> int:
    """Empty answers across every arm. Non-zero means the run measured the output cap: never recorded."""
    return sum(v.get("unanswered", 0) for v in result.get("arms", {}).values())


def record(results: list[dict]) -> None:
    """MERGE each finished model into benchmarks/ab-latest.json under `provider:model`, so separate
    provider runs accumulate into one evidence file. A refused (partial) run is never written."""
    import fcntl

    from atlascore import atlas as _atlas
    path = ROOT / "benchmarks" / "ab-latest.json"
    # PARALLEL PROVIDER RUNS ALL MERGE INTO THIS FILE. Without an exclusive lock around the read-modify-
    # write, two runs finishing together each read the old file and the second erases the first —
    # the lost update this repository already paid for once, in the mutation harness.
    lock = open(path.with_suffix(".lock"), "w")  # noqa: SIM115 — held until the merge is written
    fcntl.flock(lock, fcntl.LOCK_EX)
    evidence = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"models": {}}
    version = str(_atlas().get("version"))
    for r in results:
        if "arms" not in r or unanswered(r):
            continue
        evidence["models"][f"{r['provider']}:{r['model']}"] = {
            "measured_at": version, "questions": r["questions"], **{arm: {
                "correct": v["correct"], "asked": v["asked"],
                "tokens_per_question": round(v["tokens"] / v["metered"], 1) if v["metered"] else None}
                for arm, v in r["arms"].items()}}
        evidence["chance_baseline"] = r["chance"]
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    lock.close()


def measured_block() -> str:
    """What it measurably buys you — EVERY figure computed from its instrument on each build.

    Typed, this table went stale four times in one session (the entry cost, the pair count, the
    footprint, the instrument count). Generated, it cannot: `check` fails the moment a figure here
    differs from what the instrument now measures. The A/B rows read recorded evidence, because that
    experiment cannot re-run per build; its version stamp says when it was measured.

    BULLETS IN PLAIN WORDS, rewritten at 2.28.0 on the owner's read: "fewer tokens than every pack"
    and "K=2,076, chance 0.0278" were accurate and unreadable. Each arm is named once at the top in
    words, then used by that name.
    """
    import json as _json

    from atlascore import atlas as _atlas  # noqa: PLC0415
    from atlasinv import declared_case_total, role_coverage  # noqa: PLC0415 — atlasinv imports this module
    from contextcost import footprint, lazy_bytes, measure, tokens
    ab = _json.loads((ROOT / "benchmarks" / "ab-latest.json").read_text(encoding="utf-8"))
    models = ab["models"]
    # POOLED ACROSS MODELS OF EVERY KIND, AND PAIRED FOR TOKENS. A model is compared only on arms it
    # ran: scoped tokens from every model against whole-tree tokens from a subset would be a ratio of
    # two different populations. The per-model range is printed beside the pool so one strong model
    # cannot carry a weak field unseen.
    def pooled(arm: str) -> float:
        runs = [m[arm] for m in models.values() if arm in m and m[arm]["asked"]]
        return 100 * sum(r["correct"] for r in runs) / sum(r["asked"] for r in runs)

    def fewer(against: str) -> tuple[int, int]:
        pairs = [(m["scoped"]["tokens_per_question"], m[against]["tokens_per_question"]) for m in models.values()
                 if "scoped" in m and against in m and m["scoped"]["tokens_per_question"] and m[against]["tokens_per_question"]]
        return (round(100 * (1 - sum(a for a, _ in pairs) / sum(b for _, b in pairs))) if pairs else 0), len(pairs)
    spread = sorted(100 * m["scoped"]["correct"] / m["scoped"]["asked"] for m in models.values() if "scoped" in m)
    providers = {name.split(":", 1)[0] if ":" in name else "freeroute" for name in models}
    k = sum(m[a]["asked"] for m in models.values() for a in m if isinstance(m[a], dict) and "asked" in m[a])
    versions = sorted({str(m.get("measured_at", ab.get("measured_at"))) for m in models.values()})
    v = "v" + " / v".join(versions)
    (whole, _), (blind, _) = fewer("whole_tree"), fewer("unassisted")
    cover, weight = role_coverage(), footprint()
    lazy, docs = lazy_bytes()
    entry = tokens(int(measure()["agent"]["bytes"]))
    controls = list(((_atlas().get("agent_policy") or {}).get("controls") or {}))
    lines = [
        "*With Thea* = the model is given the one line `atlas gate` returns. *Blind* = it gets only the list",
        "of language names. Token savings are against the usual alternative: pasting in every language's tool list.",
        "",
        *claude_lines(models),
        "",
        *task_lines(),
        f"**Across all {len(models)} models tested** ({len(providers)} providers, {k:,} questions, `abtest.py` {v})",
        f"- **Right answers:** {pooled('scoped'):.0f}% with Thea, {pooled('unassisted'):.0f}% blind; every model "
        f"{spread[0]:.0f}–{spread[-1]:.0f}% with Thea. A random guess scores {100 * ab['chance_baseline']:.1f}%.",
        f"- **Tokens:** reads {whole}% fewer than pasting every tool list, and {blind}% fewer than asking blind.",
        "",
        "**The repository itself** (recomputed on every build)",
        f"- **Before routing:** an agent reads {entry:,} tokens. The other {docs} documents ({lazy // 1024} KiB) load "
        "only when a route names one.",
        f"- **Coverage:** all {cover['total']} language × check pairs answer — {cover['runnable']} with a command, "
        f"{cover['absent']} with a declared *no tool*, {cover['undeclared']} silently.",
        f"- **Mistakes caught:** {declared_case_total()} kinds are planted in the tests, and each must be refused.",
        f"- **Agent controls that block, not warn:** {', '.join(controls)}.",
        f"- **Install:** {weight['bytes'] // 1024} KiB, {weight['modules']} modules, {weight['dependencies']} dependency — "
        f"{weight['declared'].get('resolved_closure')} package in total once its own dependencies are counted.",
    ]
    return "\n".join(lines)


def task_lines() -> list[str]:
    """Beyond routing: `taskbench.py`'s recorded kinds, blind -> with Thea, per model. Empty until a run
    is recorded, and it says what it does NOT measure every time, so a missing kind is never implied."""
    path = ROOT / "benchmarks" / "tasks-latest.json"
    if not path.exists():
        return []
    models = json.loads(path.read_text(encoding="utf-8"))["models"]

    def pct(cell: dict) -> str:
        return f"{100 * cell['correct'] / cell['asked']:.0f}%" if cell.get("asked") else "—"
    stamp = "v" + " / v".join(sorted({str(m.get("measured_at")) for m in models.values()}))
    lines = [f"**Beyond routing** (blind → with Thea, `taskbench.py` {stamp})"]
    for kind, label in (("diagnose", "Name a failure from its symptom"), ("plan", "List the checks a change needs"),
                        ("hygiene", "Spot a line the build refuses (yes/no, so a coin flip scores 50%)")):
        parts = [f"{name.split(':', 1)[-1].capitalize()} {pct(m[kind]['blind'])} → {pct(m[kind]['thea'])}"
                 for name, m in sorted(models.items(), key=lambda kv: -_rank(kv[0].split(":", 1)[-1])) if kind in m]
        lines.append(f"- **{label}:** {'; '.join(parts)}.")
    return [*lines, "- *Not measured:* visual design, open-ended strategy, arithmetic — nothing declares a right answer.", ""]

def claude_lines(models: dict) -> list[str]:
    """Claude first, because Claude is the runtime this contract is written for first.

    ADDED AT 2.28.0: the A/B had eight models on four providers and not one was Claude, so every row
    was a claim about other models. Each Claude model gets its own line — never pooled with the field,
    where a strong Claude would carry weaker models unseen, or the reverse. The names are the CLI's
    aliases, which move to newer models; the stamp bounds which ones they were. With no Claude run
    recorded, the block says so rather than borrowing the pooled number.
    """
    from contextcost import tokens
    claude = {name.split(":", 1)[1]: m for name, m in models.items() if name.startswith("claude-cli:")}
    entry = f"- **Claude Code start-up:** reads only `CLAUDE.md`, {tokens((ROOT / 'CLAUDE.md').stat().st_size):,} tokens."
    if not claude:
        return ["**On Claude:** not measured — no `claude-cli` run is recorded.", entry]

    def pct(m: dict, arm: str) -> str:
        return f"{100 * m[arm]['correct'] / m[arm]['asked']:.0f}%" if m.get(arm, {}).get("asked") else "—"

    def saved(m: dict) -> str:
        a, b = (m.get(k, {}).get("tokens_per_question") for k in ("scoped", "whole_tree"))
        return f"reads {round(100 * (1 - a / b))}% fewer tokens" if a and b else "tokens unmetered"
    stamp = "v" + " / v".join(sorted({str(m.get("measured_at")) for m in claude.values()}))
    asked = max(m.get("questions", 0) for m in claude.values())
    return [f"**On Claude** ({asked} questions per model, `abtest.py` {stamp})",
            *(f"- **{name.capitalize()}:** {pct(m, 'scoped')} right with Thea, {pct(m, 'unassisted')} blind; {saved(m)}."
              for name, m in sorted(claude.items(), key=lambda kv: -_rank(kv[0]))),
            entry]


def _rank(alias: str) -> int:
    return {"opus": 3, "sonnet": 2, "haiku": 1}.get(alias, 0)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="abtest.py")
    parser.add_argument("--model", default="small",
                        help="comma-separated models the local router serves. MORE THAN ONE is "
                             "the point: a result from a single model is a fact about that model")
    parser.add_argument("--limit", type=int, default=6, help="questions; each costs three calls")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--all-packs", action="store_true", dest="every_pack",
                        help="one question per pack — the honest sample, because the task set "
                             "leans on languages a model already knows")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--provider", default="freeroute", help="a key of providers.PROVIDERS")
    parser.add_argument("--arms", default="unassisted,routed,whole_tree,scoped",
                        help="comma-separated arms; breadth runs may skip the costly ones on tight free tiers")
    parser.add_argument("--sample", type=int, default=0, help="stratified question sample; 0 = all")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-tokens", type=int, default=120, dest="max_tokens",
                        help="output cap; a reasoning model needs more or it answers empty")
    parser.add_argument("--record", action="store_true",
                        help="write benchmarks/ab-latest.json — the evidence the README's rows are generated from")
    parser.add_argument("--claude", action="store_true",
                        help="the Claude re-run, one command: every Claude alias the CLI serves, the "
                             "one-per-pack sample, the arms the README's Claude row reads. Run it on "
                             "each new Claude release with --record")
    args = parser.parse_args(argv)
    if args.claude:
        # THE SAME SAMPLE AS THE BREADTH RUNS (39 of the one-per-pack set, seed 7), so a Claude row and
        # a pooled row answer the same questions. The aliases move to new models; the stamp says when.
        args.provider, args.model, args.every_pack, args.limit = "claude-cli", "haiku,sonnet,opus", True, 200
        args.sample, args.arms, args.timeout = 39, "unassisted,scoped,whole_tree", max(args.timeout, 180)
    models = [m.strip() for m in str(args.model).split(",") if m.strip()]
    arm_names = tuple(a.strip() for a in str(args.arms).split(",") if a.strip())
    results = [run(m, args.limit, args.timeout, args.every_pack, args.provider, arm_names, args.sample, args.seed,
                   args.max_tokens)
               for m in models]
    if args.record:
        record(results)
    result = results[0]
    if args.json:
        print(json.dumps(results if len(results) > 1 else result, indent=2))
        return 1 if any(r.get("error") for r in results) else 0
    for extra in results[1:]:
        if extra.get("error"):
            print(f"- {extra['model'] if 'model' in extra else 'model'}: {extra['error']}")
            continue
        print(f"model {extra['model']} | {extra['questions']} questions | K={extra['k']}")
        for arm, row in extra["arms"].items():
            asked = row["asked"] or 1
            print(f"  {arm:<12} {row['correct']}/{row['asked']} correct "
                  f"({100 * row['correct'] / asked:>5.1f}%) | {row['tokens'] / asked:>6.1f} tok/question")
    if result.get("error"):
        print(f"- {result['error']}")
        print("REFUSED rather than reporting a partial sample as a whole one.")
        return 1
    print(f"model {result['model']} | {result['questions']} questions"
          f"{' (one per pack)' if args.every_pack else ''} | K={result['k']} | "
          f"chance {result['chance']} (one pack in {len(route_targets())})")
    for arm, row in result["arms"].items():
        asked = row["asked"] or 1
        print(f"  {arm:<12} {row['correct']}/{row['asked']} correct "
              f"({100 * row['correct'] / asked:>5.1f}%) | {row['tokens']:>6} prompt tokens "
              f"| {row['tokens'] / asked:>6.1f} per question")
    if unanswered(result):
        print(f"  INSTRUMENT: {unanswered(result)} empty answers, the output cap and not the model. "
              "NOT recorded; re-run with a higher --max-tokens.")
    routed, whole = result["arms"].get("routed"), result["arms"].get("whole_tree")
    if routed and whole and routed["correct"] == whole["correct"] and whole["tokens"]:
        print(f"  AT EQUAL ACCURACY, routing costs {100 * routed['tokens'] / whole['tokens']:.1f}% "
              "of reading every pack — that is the token claim, and it only holds while the two "
              "arms score the same")
    for miss in result["routed_misses"]:
        print(f"  routed MISS  {miss}")
    print("SCOPE: one model, one phrasing, a handful of questions. The prompt is part of the")
    print("       experiment, so this is a SAMPLE and not an edge; re-run it per model.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
