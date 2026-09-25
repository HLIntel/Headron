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

from atlascore import ROOT, route_targets

ENDPOINT = "http://127.0.0.1:8799/v1/chat/completions"


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


def ask(model: str, prompt: str, timeout: int) -> tuple[str, int]:
    """(answer, prompt_tokens). The token count comes from the SERVER, never from an estimate."""
    body = json.dumps({"model": model, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 120}).encode()
    request = urllib.request.Request(ENDPOINT, data=body,  # noqa: S310 — a declared localhost port
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = json.load(response)
    usage = payload.get("usage") or {}
    return payload["choices"][0]["message"]["content"], int(usage.get("prompt_tokens") or 0)


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
        "route": "Answer with ONLY the name of the language pack that owns this file. One word, "
                 "no prose.",
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
    }


def run(model: str, limit: int, timeout: int, every_pack: bool = False) -> dict:
    rows = questions(limit, every_pack)
    arms: dict[str, dict] = {name: {"correct": 0, "tokens": 0, "asked": 0}
                             for name in ("unassisted", "routed", "whole_tree")}
    misses: list[str] = []
    for row in rows:
        for arm, prompt in prompts(row).items():
            try:
                answer, tokens = ask(model, prompt, timeout)
            except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
                # REFUSE RATHER THAN REPORT A SHORT SAMPLE AS A FULL ONE.
                return {"error": f"{type(exc).__name__} talking to {ENDPOINT}: {exc}"}
            arms[arm]["asked"] += 1
            arms[arm]["tokens"] += tokens
            hit = row["truth"].lower() in " ".join(answer.split()).lower()
            arms[arm]["correct"] += int(hit)
            if not hit and arm == "routed":
                misses.append(f"{row['task']}: wanted {row['truth']!r}, got {answer.strip()[:60]!r}")
    return {"model": model, "questions": len(rows), "k": len(rows) * len(arms),
            "arms": arms, "routed_misses": misses,
            "chance": round(1 / max(len(route_targets()), 1), 4)}


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
    args = parser.parse_args(argv)
    models = [m.strip() for m in str(args.model).split(",") if m.strip()]
    results = [run(m, args.limit, args.timeout, args.every_pack) for m in models]
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
    routed, whole = result["arms"]["routed"], result["arms"]["whole_tree"]
    if routed["correct"] == whole["correct"] and whole["tokens"]:
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
