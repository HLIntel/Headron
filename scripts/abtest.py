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
from pathlib import Path

import resilience
from atlascore import ROOT, route_targets


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


def ask(
    model: str, prompt: str, timeout: int, provider: str = "router", max_tokens: int = 120
) -> tuple[str, int | None]:
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
            rows.append(
                {
                    "task": route,
                    "target": f"languages/{route}/OPERATING.md",
                    "route": route,
                    "truth": truth,
                    "kind": "runner",
                }
            )
            rows.append(
                {
                    "task": f"{route}:route",
                    "target": f"languages/{route}/OPERATING.md",
                    "route": route,
                    "truth": route,
                    "kind": "route",
                }
            )
            # A THIRD KIND, ADDED AT 2.27.0 BECAUSE THE FORMATTER GATE BECAME ANSWERABLE. Two
            # kinds meant two prompt shapes, and a suite that asks two shapes measures two shapes.
            # This one also exercises the 43 role resolutions that closing `runner` opened, so the
            # coverage work and the accuracy measurement are not independent claims about the tree.
            style = _truth(route, "formatter")
            if style:
                rows.append(
                    {
                        "task": f"{route}:format",
                        "target": f"languages/{route}/OPERATING.md",
                        "route": route,
                        "truth": style,
                        "kind": "formatter",
                    }
                )
        return rows[:limit]
    for path in sorted((ROOT / "benchmarks" / "tasks").glob("*.json")):
        task = json.loads(path.read_text(encoding="utf-8"))
        route = task.get("expected_route")
        if not route:
            continue  # the no-route tasks test the router, not a model's recall
        truth = _truth(route)
        if not truth:
            continue
        rows.append({"task": task["task_id"], "target": task["target"], "route": route, "truth": truth})
    return rows[:limit]


def prompts(row: dict) -> dict[str, str]:
    return _prompts_for(row, row.get("kind", "runner"))


def _prompts_for(row: dict, kind: str) -> dict[str, str]:
    """The same question under three context regimes. Only the CONTEXT differs, never the ask."""
    # TWO QUESTION KINDS, because one measures recall of a command and the other measures ROUTING.
    # A suite that only ever asks the same shape of question measures that shape, and the arm that
    # wins is the one whose context happens to suit it.
    ask_line = (
        f"File: {row['target']}\n"
        + {
            "runner": "Answer with ONLY the exact shell command this project declares for running that "
            "file's tests. No prose, no explanation, no backticks.",
            "formatter": "Answer with ONLY the exact shell command this project declares for formatting "
            "that file. No prose, no explanation, no backticks.",
            # "ONE WORD" WAS A DEFECT IN THE QUESTION, found at 2.28.0: a nested pack id is `group/pack`,
            # and a model answering `pack` was OBEYING it. Fixed in the question, never by loosening the
            # scorer to accept a leaf, which would only make every model's number friendlier. It touched at
            # most one of 39 sampled questions per model; runs recorded before the fix carry the old wording.
            "route": "Answer with ONLY the id of the language pack that owns this file, exactly as the "
            "project writes it (it may contain a slash). No prose.",
        }[kind]
    )
    packs = ", ".join(sorted(route_targets()))
    manifest = _manifest(row["route"])
    routed = {"authority": manifest.get("authority") or {}, "runner": manifest.get("runner") or {}}
    # THE WHOLE-TREE ARM MUST CARRY WHAT THE QUESTION NEEDS, or it is not the brute-force arm, it
    # is a worse-informed one — and the token ratio would then be measured against a straw man.
    role = {"formatter": "formatter"}.get(kind, "test")
    whole = {
        target: {
            role: (_manifest(target).get("authority") or {}).get(role),
            "runner": (_manifest(target).get("runner") or {}).get(role),
        }
        for target in sorted(route_targets())
    }
    return {
        "unassisted": f"The project supports these language packs: {packs}.\n\n{ask_line}",
        "routed": (
            f"`atlas route` resolved this file to the `{row['route']}` pack, whose declared "
            f"tools are: {json.dumps(routed)}\n\n{ask_line}"
        ),
        "whole_tree": (f"Every pack's declared {role}: {json.dumps(whole)}\n\n{ask_line}"),
        # THE FOURTH ARM, ADDED AT 2.27.0 ON A MEASURED HYPOTHESIS: `routed` hands over the pack's
        # WHOLE manifest — every role — when a question needs ONE. This is what `gate_resolution`
        # returns for the gate asked about, and nothing else. If it scores with `routed` at the
        # cost of `unassisted`, routing's accuracy is nearly free in tokens.
        "scoped": (
            f"`atlas route` resolved this file to the `{row['route']}` pack; its declared "
            + (f"{role} command is: {_scoped(row['route'], kind)}" if kind != "route" else "route id is that pack name")
            + f"\n\n{ask_line}"
        ),
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

    where = (
        _sp.check_output(["git", "rev-parse", "--git-path", "atlas-test.lock"], cwd=ROOT, timeout=600).decode().strip()
    )
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
        picked += group[: max(1, round(n * len(group) / len(rows)))]
    return picked


def run(
    model: str,
    limit: int,
    timeout: int,
    every_pack: bool = False,
    provider: str = "router",
    arm_names: tuple[str, ...] = ("unassisted", "routed", "whole_tree", "scoped"),
    sample: int = 0,
    seed: int = 7,
    max_tokens: int = 120,
) -> dict:
    _held = _reader_lock()  # noqa: F841 — held for the whole run, released at exit
    rows = stratified(questions(limit, every_pack), sample, seed)
    arms: dict[str, dict] = {
        name: {"correct": 0, "tokens": 0, "asked": 0, "metered": 0, "unanswered": 0} for name in arm_names
    }
    misses: list[str] = []
    # PER ROUTE, NOT ONLY PER ARM. The aggregate says how much the atlas adds; it cannot say WHERE,
    # and "where" is the question that decides how much context a given model needs for a given
    # language. A model already strong on a route needs less from the atlas there — but only a cell
    # with enough questions behind it may be read that way, which is why n travels with every cell.
    by_route: dict[str, dict[str, dict[str, int]]] = {}
    total, done = len(rows) * len(arms), 0
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
            cell = by_route.setdefault(str(row["route"]), {}).setdefault(arm, {"correct": 0, "asked": 0})
            cell["asked"] += 1
            cell["correct"] += int(hit)
            # ONE FLUSHED LINE PER CALL ON STDERR: a 684-call run printed nothing for 40 minutes because
            # every report waited for the end, and a silent run cannot be told from a hung one.
            done += 1
            print(f"[abtest] {model} {done}/{total} {arm} {'hit' if hit else 'miss'}", file=sys.stderr, flush=True)
            if not hit and arm == "routed":
                misses.append(f"{row['task']}: wanted {row['truth']!r}, got {answer.strip()[:60]!r}")
    return {
        "model": model,
        "provider": provider,
        "questions": len(rows),
        "k": len(rows) * len(arms),
        "arms": arms,
        "by_route": by_route,
        "routed_misses": misses,
        "chance": round(1 / max(len(route_targets()), 1), 4),
    }


def wilson(correct: int, asked: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson score interval for a rate (Wilson 1927): a bare percentage hides how few questions
    carried it, and the normal interval collapses at 0% and 100%, where every with-Headron row sits."""
    if not asked:
        return 0.0, 1.0  # nothing asked bounds nothing
    p, z2 = correct / asked, z * z
    centre, half = (
        (p + z2 / (2 * asked)) / (1 + z2 / asked),
        z * ((p * (1 - p) + z2 / (4 * asked)) / asked) ** 0.5 / (1 + z2 / asked),
    )
    return max(0.0, centre - half), min(1.0, centre + half)


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
            "measured_at": version,
            "questions": r["questions"],
            **{
                arm: {
                    "correct": v["correct"],
                    "asked": v["asked"],
                    "tokens_per_question": round(v["tokens"] / v["metered"], 1) if v["metered"] else None,
                }
                for arm, v in r["arms"].items()
            },
            "by_route": r.get("by_route") or {},
        }
        evidence["chance_baseline"] = r["chance"]
    path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    append_history(path.with_name("ab-history.jsonl"), results, version)
    lock.close()


HISTORY_MAX_BYTES = 1 << 20  # ~5000 rows: years of measured runs; past it, archive the file by hand


def append_history(path: Path, results: list[dict], version: str) -> int:
    """APPEND one line per recorded model to the history, beside the merged latest file (B01).

    WHY. ab-latest.json keeps one cell per model, so a re-run on a new contract version OVERWROTE the
    run it should have been compared with: the README could say what the score is, never whether it
    moved. The same refusal as record(): a partial run leaves no line. Returns the lines written."""
    rows = [
        {
            "measured_at": version,
            "model": f"{r['provider']}:{r['model']}",
            "questions": r["questions"],
            "arms": {arm: {"correct": v["correct"], "asked": v["asked"]} for arm, v in r["arms"].items()},
        }
        for r in results
        if "arms" in r and not unanswered(r)
    ]
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    if (path.stat().st_size if path.exists() else 0) + len(text) > HISTORY_MAX_BYTES:
        # REFUSED, NEVER TRIMMED: history is the only record of a moved score; archive it, then re-run.
        print(f"history: refused — {path.name} would pass {HISTORY_MAX_BYTES} bytes; gzip it aside", file=sys.stderr)
        return 0
    with path.open("a", encoding="utf-8") as out:
        out.write(text)
    return len(rows)


def field_figures() -> dict:
    """field-latest.json: the owner's ledger, its headline held to a high-water mark (agents.HEADLINE)."""
    path = ROOT / "benchmarks" / "field-latest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def field_figure(field: str) -> int | str:
    """A field metric, or an explicit absence; a missing snapshot must never look current."""
    value = field_figures().get(field)
    return value if isinstance(value, int) else "not recorded"


def measured_block() -> str:
    """Render recorded measurements with their scope, without treating samples as guarantees."""
    f = measured_figures()
    lines = [
        "<!-- prettier-ignore -->",
        "| Instrument | Recorded result |",
        "| :--- | :--- |",
        f"| Enforcement | {f.get('enf_refused', 'not recorded')}/{f.get('enf_planted', 'not recorded')} breaks refused across {f.get('enf_langs', 'not recorded')} toolchains; **{f['planted']}** declared planted cases |",
        f"| Failure ledger | {f['failures']} shapes, {f['failures_sightings']} sightings; {f['failures_guarded']} in-tree guarded, {f['failures_host_only']} host-only |",
        f"| Field ledger | {field_figure('verify_runs')} verifications ({field_figure('verify_pass')} clean); {field_figure('refusals')} refusals; {field_figure('lands')} landings; {field_figure('lessons_served')} lessons; {field_figure('sessions_ended')} sessions |",
        f"| Routing experiment | {f['tok_fewer']}% fewer prompt tokens than whole-tree; {f['tok_blind']}% fewer than unassisted, across identified models |",
        f"| Language roles | {f['pairs']} pairs: {f['pairs_runnable']} runnable, {f['pairs_absent']} absent, {f['pairs_silent']} undeclared |",
        "",
        f"Entry context: ~{f['pre_tokens']:,} tokens. The {f['lazy_docs']} documents ({f['lazy_kib']} KiB) load on demand; install: {f['install_kib']} KiB, {f['deps_closure']} dependencies.",
        "[Field](benchmarks/field-latest.json): owner development, not customer usage; a historical chain is broken. [Routing data](benchmarks/ab-latest.json). These overlapping measures do not establish causality and cannot be added.",
    ]
    return "\n".join(lines)


def measured_figures() -> dict:
    """EVERY FIGURE measured_block prints, as data (3.54.0): the README renders from this dict and
    `.agent/facts.json` is this dict, so a site or dashboard reads keys, never a regex over prose."""
    from atlascore import atlas as _atlas  # noqa: PLC0415
    from atlasinv import declared_case_total, role_coverage  # noqa: PLC0415 — atlasinv imports this module
    from contextcost import footprint, lazy_bytes, measure, tokens

    ab = json.loads((ROOT / "benchmarks" / "ab-latest.json").read_text(encoding="utf-8"))
    models = ab["models"]

    # PROVENANCE CUT (3.56.0, owner-directed): rows keyed by a bare size-class alias
    # (code/cheap/small) carry no provider, no model name, and no snapshot — no third
    # party can reproduce them. They stay in ab-latest.json as audit trail, but every
    # pooled figure below counts only identified models.
    identified = {name: m for name, m in models.items() if ":" in name}

    def rate(arm: str) -> int:
        runs = [m[arm] for m in identified.values() if arm in m and m[arm]["asked"]]
        return round(100 * sum(r["correct"] for r in runs) / sum(r["asked"] for r in runs))

    def fewer(against: str) -> int:
        pairs = [
            (m["scoped"]["tokens_per_question"], m[against]["tokens_per_question"])
            for m in identified.values()
            if "scoped" in m
            and against in m
            and m["scoped"]["tokens_per_question"]
            and m[against]["tokens_per_question"]
        ]
        return round(100 * (1 - sum(a for a, _ in pairs) / sum(b for _, b in pairs))) if pairs else 0

    spread = sorted(100 * m["scoped"]["correct"] / m["scoped"]["asked"] for m in identified.values() if "scoped" in m)
    cover, weight = role_coverage(), footprint()
    lazy, docs = lazy_bytes()
    path = ROOT / "benchmarks" / "enforce-latest.json"
    e = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    fld = field_figures()
    return {
        "ab_models": len(identified),
        "ab_providers": len({name.split(":", 1)[0] for name in identified}),
        # TRIALS, NOT QUESTIONS (3.56.0): summing `asked` across arms counted each
        # question once per arm (3-4x). One trial = one model answering one question;
        # arms are treatments of the same trial, so dedupe with max per model.
        "ab_trials": sum(
            max([a["asked"] for a in m.values() if isinstance(a, dict) and "asked" in a] or [0])
            for m in identified.values()
        ),
        "ab_versions": sorted({str(m.get("measured_at", ab.get("measured_at"))) for m in identified.values()}),
        "ab_headron": rate("scoped"),
        "ab_blind": rate("unassisted"),
        "ab_low": round(spread[0]),
        "ab_high": round(spread[-1]),
        "ab_chance": round(100 * ab["chance_baseline"], 1),
        "tok_fewer": fewer("whole_tree"),
        "tok_blind": fewer("unassisted"),
        "pre_tokens": tokens(int(measure()["agent"]["bytes"])),
        "lazy_docs": docs,
        "lazy_kib": lazy // 1024,
        "pairs": cover["total"],
        "pair_checks": len(cover["by_role"]),
        "pairs_runnable": cover["runnable"],
        "pairs_absent": cover["absent"],
        "pairs_silent": cover["undeclared"],
        "planted": declared_case_total(),
        **(
            {
                "enf_refused": e["refused"],
                "enf_planted": e["planted"],
                "enf_langs": len(e["languages"]),
                "enf_untested": e["not_trialled"],
            }
            if e
            else {}
        ),
        **ledger_figures(),
        "failures": len(_atlas().get("agent_failure_modes") or {}),
        "field_refusals": fld.get("refusals"),
        "field_refusal_shapes": fld.get("refusal_shapes"),
        "field_refires": fld.get("refires"),
        "field_verify_runs": fld.get("verify_runs"),
        "field_verify_pass": fld.get("verify_pass"),
        "field_verify_fail": fld.get("verify_fail"),
        "field_lands": fld.get("lands"),
        "field_lands_armed": fld.get("lands_armed"),
        "field_lessons": fld.get("lessons_shown"),
        "field_lessons_served": fld.get("lessons_served"),
        "field_sessions": fld.get("sessions_ended"),
        "field_headline": fld.get("headline"),
        "controls": list(((_atlas().get("agent_policy") or {}).get("controls") or {})),
        "install_kib": weight["bytes"] // 1024,
        "install_modules": weight["modules"],
        "deps": weight["dependencies"],
        "deps_closure": weight["declared"].get("resolved_closure"),
    }


def ledger_figures() -> dict:
    """The failure ledger, counted from atlas.yaml: a sighting is typed once, as its row's own number."""
    from atlascore import atlas as _atlas  # noqa: PLC0415

    rows = list((_atlas().get("agent_failure_modes") or {}).values())
    seen = [int(r.get("sightings") or 1) for r in rows]
    return {
        "failures_sightings": sum(seen),
        "failures_recurred": sum(n > 1 for n in seen),
        "failures_guarded": sum(bool(r.get("enforced_by")) for r in rows),
        # A ROW IS GUARDED OR HOST-ONLY, NEVER NEITHER: atlasinv refuses a row with no enforcer and no reason.
        # The host-only count is printed beside the guarded one so the unguarded share is never hidden in a sum.
        "failures_host_only": sum(not r.get("enforced_by") for r in rows),
        "failures_recurring_host_only": sum(
            not r.get("enforced_by") and int(r.get("sightings") or 1) >= 2 for r in rows
        ),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="abtest.py")
    parser.add_argument(
        "--model",
        default="small",
        help="comma-separated models the local router serves. MORE THAN ONE is "
        "the point: a result from a single model is a fact about that model",
    )
    parser.add_argument("--limit", type=int, default=6, help="questions; each costs three calls")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument(
        "--all-packs",
        action="store_true",
        dest="every_pack",
        help="one question per pack — the honest sample, because the task set leans on languages a model already knows",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--provider", default="router", help="a key of providers.PROVIDERS")
    parser.add_argument(
        "--arms",
        default="unassisted,routed,whole_tree,scoped",
        help="comma-separated arms; breadth runs may skip the costly ones on tight free tiers",
    )
    parser.add_argument("--sample", type=int, default=0, help="stratified question sample; 0 = all")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=120,
        dest="max_tokens",
        help="output cap; a reasoning model needs more or it answers empty",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="write benchmarks/ab-latest.json — the evidence the README's rows are generated from",
    )
    parser.add_argument(
        "--claude",
        action="store_true",
        help="the Claude re-run, one command: every Claude alias the CLI serves, the "
        "one-per-pack sample, the arms the README's Claude row reads. Run it on "
        "each new Claude release with --record",
    )
    parser.add_argument("--live", action="store_true", help="call the vendor and record answers; offline otherwise")
    args = parser.parse_args(argv)
    import providers

    providers.set_live(args.live)
    if args.claude:
        # THE SAME SAMPLE AS THE BREADTH RUNS (39 of the one-per-pack set, seed 7), so a Claude row and
        # a pooled row answer the same questions. The aliases move to new models; the stamp says when.
        args.provider, args.model, args.every_pack, args.limit = "claude-cli", "haiku,sonnet,opus", True, 200
        # An explicit --sample widens it (76 = the whole one-per-pack set); the pooled rows stay at 39.
        args.sample, args.arms, args.timeout = args.sample or 39, "unassisted,scoped,whole_tree", max(args.timeout, 180)
    models = [m.strip() for m in str(args.model).split(",") if m.strip()]
    arm_names = tuple(a.strip() for a in str(args.arms).split(",") if a.strip())
    results = [
        run(
            m,
            args.limit,
            args.timeout,
            args.every_pack,
            args.provider,
            arm_names,
            args.sample,
            args.seed,
            args.max_tokens,
        )
        for m in models
    ]
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
            print(
                f"  {arm:<12} {row['correct']}/{row['asked']} correct "
                f"({100 * row['correct'] / asked:>5.1f}%) | {row['tokens'] / asked:>6.1f} tok/question"
            )
    if result.get("error"):
        print(f"- {result['error']}")
        print("REFUSED rather than reporting a partial sample as a whole one.")
        return 1
    # PER-ROUTE, PRINTED EVERY RUN, WITH ITS FLOOR. A run that produced no breakdown says so rather
    # than printing nothing, because an absent cell and a low one are the same silence otherwise.
    print(route_capability_report({"models": {r["model"]: r for r in [*results, result] if "by_route" in r}}))
    print(
        f"model {result['model']} | {result['questions']} questions"
        f"{' (one per pack)' if args.every_pack else ''} | K={result['k']} | "
        f"chance {result['chance']} (one pack in {len(route_targets())})"
    )
    for arm, row in result["arms"].items():
        asked = row["asked"] or 1
        print(
            f"  {arm:<12} {row['correct']}/{row['asked']} correct "
            f"({100 * row['correct'] / asked:>5.1f}%) | {row['tokens']:>6} prompt tokens "
            f"| {row['tokens'] / asked:>6.1f} per question"
        )
    if unanswered(result):
        print(
            f"  INSTRUMENT: {unanswered(result)} empty answers, the output cap and not the model. "
            "NOT recorded; re-run with a higher --max-tokens."
        )
    routed, whole = result["arms"].get("routed"), result["arms"].get("whole_tree")
    if routed and whole and routed["correct"] == whole["correct"] and whole["tokens"]:
        print(
            f"  AT EQUAL ACCURACY, routing costs {100 * routed['tokens'] / whole['tokens']:.1f}% "
            "of reading every pack — that is the token claim, and it only holds while the two "
            "arms score the same"
        )
    for miss in result["routed_misses"]:
        print(f"  routed MISS  {miss}")
    print("SCOPE: one model, one phrasing, a handful of questions. The prompt is part of the")
    print("       experiment, so this is a SAMPLE and not an edge; re-run it per model.")
    return 0


ROUTE_CELL_FLOOR = 8  # atlas.yaml/asymmetries and the overfitting discipline: under this, the grid IS the finding


def route_capability(evidence: dict, arm: str = "unassisted") -> list[dict]:
    """Per (model, route) scores from a recorded run, with n beside every cell and a verdict field.

    WHY n TRAVELS WITH THE CELL, ALWAYS. 95 questions over 36 routes is about three per cell. Three
    samples produce a 0%, a 33%, a 67% or a 100% and nothing else, so a table of them reads like a
    capability ranking and is an artifact of the partition. Every cell is labelled SAMPLE below the
    floor, and only a cell at or above it may be called a capability — which is the difference
    between measuring a model and sorting noise.

    WHAT IT IS FOR. A model already strong on a route needs less from the atlas there, and trimming
    context on that basis is only honest against a measured cell. An ABSENT cell is NOT a low one.
    """
    rows = []
    for model, record in sorted((evidence.get("models") or {}).items()):
        for route, arms in sorted((record.get("by_route") or {}).items()):
            cell = (arms or {}).get(arm) or {}
            asked = int(cell.get("asked") or 0)
            if not asked:
                continue
            rows.append(
                {
                    "model": model,
                    "route": route,
                    "arm": arm,
                    "correct": int(cell.get("correct") or 0),
                    "asked": asked,
                    "verdict": "capability" if asked >= ROUTE_CELL_FLOOR else "SAMPLE",
                }
            )
    return rows


def route_capability_report(evidence: dict) -> str:
    rows = route_capability(evidence)
    if not rows:
        return (
            "per-route capability: NOT MEASURED — no recorded run carries a by_route breakdown. "
            "Re-run `abtest.py --record` to produce one; an absent cell is not a low score."
        )
    solid = [r for r in rows if r["verdict"] == "capability"]
    return (
        f"per-route capability: {len(rows)} cell(s) across "
        f"{len({r['model'] for r in rows})} model(s) and {len({r['route'] for r in rows})} route(s); "
        f"{len(solid)} at or above the {ROUTE_CELL_FLOOR}-question floor, "
        f"{len(rows) - len(solid)} are SAMPLE and may not be read as capability"
    )


# LAST LINE, NOT MID-FILE: placed above route_capability_report it ran main() before that def
# existed, so every multi-model text run crashed AFTER --record had written.
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
