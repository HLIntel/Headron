#!/usr/bin/env python3
"""Multi-model cross-evaluation benchmark: Headron lift, tokens, and multi-model collaboration.

proves: accuracy, token efficiency, latency, and cooperative multi-model lift across providers
does_not_prove: unassisted reasoning outside declared ground truths
closed_by: scripts/multimodel_bench_test.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, cast

import providers
import resilience
import taskbench
from abtest import _reader_lock
from atlascore import atlas, text_of


def select_questions(kinds: list[str], sample_diagnose: int | None = None) -> list[dict[str, Any]]:
    """Filter and sample questions by kind and diagnose subset."""
    all_qs = taskbench.questions()
    selected: list[dict[str, Any]] = []
    diag_count = 0
    for q in all_qs:
        k = q["kind"]
        if k not in kinds:
            continue
        if k == "diagnose" and sample_diagnose is not None:
            if diag_count >= sample_diagnose:
                continue
            diag_count += 1
        selected.append(q)
    return selected


def benchmark_single(
    provider: str, model: str, questions: list[dict[str, Any]], timeout: int = 60, max_tokens: int = 300
) -> dict[str, Any]:
    """Run blind and Headron-assisted benchmark passes for a single model."""
    summary: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "kinds": {},
        "questions": {},
        "overall": {
            "blind_correct": 0,
            "headron_correct": 0,
            "blind_not_run": 0,
            "headron_not_run": 0,
            "total": 0,
            "blind_tokens": 0,
            "headron_tokens": 0,
            # an ANSWERED call whose server reported no usage: its tokens are UNMEASURED, never 0
            "blind_tokens_unmeasured": 0,
            "headron_tokens_unmeasured": 0,
        },
    }
    for q in questions:
        kind = q["kind"]
        k_entry = summary["kinds"].setdefault(
            kind,
            {
                arm: {"correct": 0, "asked": 0, "not_run": 0, "tokens": 0, "tokens_unmeasured": 0, "latency_s": 0.0}
                for arm in ("blind", "headron")
            },
        )
        for arm in ("blind", "headron"):
            t0 = time.monotonic()
            try:
                ans, tok = providers.complete(provider, model, q[arm], timeout, max_tokens)
            except (OSError, ValueError, KeyError, resilience.BreakerOpen) as err:
                # BreakerOpen is a RuntimeError: uncaught, one dead lane ended the whole run unrecorded
                cls = "breaker_open" if isinstance(err, resilience.BreakerOpen) else resilience.classify(error=err)
                errors = summary.setdefault("errors", {})
                errors[cls] = errors.get(cls, 0) + 1
                # the FIRST message per class: a class alone named no cause (19 kilo lanes read `terminal`)
                summary.setdefault("error_samples", {}).setdefault(cls, providers.error_text(err))
                ans, tok = "", 0
            elapsed = time.monotonic() - t0
            # A NON-ANSWER IS NOT A WRONG ANSWER (`a_non_answer_scored_as_wrong`). A transport error, an
            # empty reply or a decline the scorer cannot read is NOT RUN: it leaves the denominator.
            v = taskbench.score(q, ans) if ans.strip() else None
            verdict = "not_run" if v is None else "correct" if v else "wrong"
            summary["questions"].setdefault(q["task"], {})[arm] = verdict
            cell = k_entry[arm]
            cell["asked"] += 1
            cell["not_run"] += int(verdict == "not_run")
            cell["correct"] += int(verdict == "correct")
            unmeasured = int(verdict != "not_run" and tok is None)
            cell["tokens"] += tok or 0
            cell["tokens_unmeasured"] += unmeasured
            cell["latency_s"] += elapsed
            summary["overall"][f"{arm}_correct"] += int(verdict == "correct")
            summary["overall"][f"{arm}_not_run"] += int(verdict == "not_run")
            summary["overall"][f"{arm}_tokens"] += tok or 0
            summary["overall"][f"{arm}_tokens_unmeasured"] += unmeasured
        summary["overall"]["total"] += 1
    return summary


def benchmark_cooperative(
    lead_provider: str,
    lead_model: str,
    peer_provider: str,
    peer_model: str,
    questions: list[dict[str, Any]],
    timeout: int = 60,
    max_tokens: int = 300,
) -> dict[str, Any]:
    """Evaluate multi-model collaboration: lead model drafts, peer reviewer audits."""
    results: dict[str, Any] = {
        "lead": f"{lead_provider}:{lead_model}",
        "peer": f"{peer_provider}:{peer_model}",
        "correct": 0,
        "not_run": 0,
        "total": len(questions),
        "tokens": 0,
        "tokens_unmeasured": 0,
        "latency_s": 0.0,
    }
    for q in questions:
        t0 = time.monotonic()
        try:
            lead_ans, lead_tok = providers.complete(lead_provider, lead_model, q["headron"], timeout, max_tokens)
            review_prompt = (
                f"{q['headron']}\n\nA teammate drafted this answer:\n{lead_ans}\n"
                "Review the draft against the rules above. Output the verified final answer only."
            )
            peer_ans, peer_tok = providers.complete(peer_provider, peer_model, review_prompt, timeout, max_tokens)
        except (OSError, ValueError, KeyError, resilience.BreakerOpen) as err:
            cls = "breaker_open" if isinstance(err, resilience.BreakerOpen) else resilience.classify(error=err)
            errors = results.setdefault("errors", {})
            errors[cls] = errors.get(cls, 0) + 1
            results.setdefault("error_samples", {}).setdefault(cls, providers.error_text(err))
            lead_ans, lead_tok = "", 0
            peer_ans, peer_tok = "", 0
        elapsed = time.monotonic() - t0
        v = taskbench.score(q, peer_ans) if peer_ans.strip() else None
        results["correct"] += int(v is True)
        results["not_run"] += int(v is None)  # a non-answer leaves the denominator, never scores wrong
        results["tokens"] += (lead_tok or 0) + (peer_tok or 0)
        results["tokens_unmeasured"] += int(v is not None and (lead_tok is None or peer_tok is None))
        results["latency_s"] += elapsed
    return results


def wilson(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval for a pass rate. Two lanes whose intervals overlap are a TIE, not a ranking."""
    if n == 0:
        return (0.0, 1.0)
    p = correct / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return (round(max(centre - half, 0.0), 3), round(min(centre + half, 1.0), 3))


def discrimination(benchmarks: list[dict[str, Any]], arm: str = "blind") -> dict[str, list[str]]:
    """Split tasks into flat_pass, flat_fail and discriminating over the lanes that ANSWERED each one.

    A TASK EVERY LANE PASSES, OR EVERY LANE FAILS, RANKS NOBODY. MEASURED in the first freebench run:
    FIX_ratelimit scored 0.0 in every lane and the context round .938 in every lane, so both moved
    each lane by the same amount and read as a result. Such a task is reported and left out of the score.
    A task fewer than two lanes answered cannot discriminate either, and is `unmeasured`."""
    out: dict[str, list[str]] = {"flat_pass": [], "flat_fail": [], "discriminating": [], "unmeasured": []}
    tasks = sorted({t for b in benchmarks for t in b.get("questions", {})})
    for task in tasks:
        verdicts = [b["questions"][task][arm] for b in benchmarks if task in b.get("questions", {})]
        answered = [v for v in verdicts if v != "not_run"]
        if len(answered) < 2:
            out["unmeasured"].append(task)
        elif all(v == "correct" for v in answered):
            out["flat_pass"].append(task)
        elif all(v == "wrong" for v in answered):
            out["flat_fail"].append(task)
        else:
            out["discriminating"].append(task)
    return out


def screen_ranking(benchmarks: list[dict[str, Any]], arm: str = "blind") -> list[dict[str, Any]]:
    """Each lane scored on the discriminating tasks only, with its Wilson interval, best first."""
    keep = set(discrimination(benchmarks, arm)["discriminating"])
    rows = []
    for b in benchmarks:
        verdicts = [b["questions"][t][arm] for t in keep if t in b.get("questions", {})]
        answered = [v for v in verdicts if v != "not_run"]
        correct = sum(v == "correct" for v in answered)
        rows.append(
            {
                "lane": f"{b['provider']}:{b['model']}",
                "correct": correct,
                "answered": len(answered),
                "not_run": len(verdicts) - len(answered),
                "ci95": wilson(correct, len(answered)),
            }
        )
    return sorted(rows, key=lambda r: (-r["ci95"][0], -r["correct"]))


def format_matrix_markdown(benchmarks: list[dict[str, Any]], cooperative: dict[str, Any] | None = None) -> str:
    """Render a clean Markdown comparative matrix table."""
    lines = [
        "| Model / Pipeline | Blind Acc | Headron Acc | Acc Lift | Tokens (Blind/Headron) | Avg Latency |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for b in benchmarks:
        ov = b["overall"]
        tot = ov["total"] or 1
        # NOTHING ANSWERED IS "not run", never 0.0%; a usage-less answer makes the tokens "unmeasured", never 0
        cells: dict[str, tuple[str, float | None, str]] = {}
        for arm in ("blind", "headron"):
            answered = ov["total"] - ov.get(f"{arm}_not_run", 0)
            acc = ov[f"{arm}_correct"] / answered * 100 if answered else None
            tok = "unmeasured" if ov.get(f"{arm}_tokens_unmeasured") else str(ov[f"{arm}_tokens"] // tot)
            cells[arm] = ("not run" if acc is None else f"{acc:.1f}%", acc, tok)
        b_cell, b_acc, b_tok = cells["blind"]
        h_cell, h_acc, h_tok = cells["headron"]
        lift = "—" if b_acc is None or h_acc is None else f"{h_acc - b_acc:+.1f}%"
        latencies = [c["latency_s"] / max(c["asked"], 1) for k in b["kinds"].values() for c in k.values()]
        avg_lat = sum(latencies) / max(len(latencies), 1)
        name = f"`{b['provider']}:{b['model']}`"
        lines.append(f"| {name} | {b_cell} | {h_cell} | {lift} | {b_tok} / {h_tok} | {avg_lat:.2f}s |")
    if cooperative:
        tot_c = cooperative["total"] or 1
        c_acc = cooperative["correct"] / max(cooperative["total"] - cooperative.get("not_run", 0), 1) * 100
        c_tok = cooperative["tokens"] // tot_c
        c_lat = cooperative["latency_s"] / tot_c
        c_name = f"`cooperative:{cooperative['lead']}+{cooperative['peer']}`"
        lines.append(f"| {c_name} | — | {c_acc:.1f}% | **Ensemble** | {c_tok} tok | {c_lat:.2f}s |")
    return "\n".join(lines)


def run_matrix(
    models: list[tuple[str, str]],
    kinds: list[str],
    sample_diagnose: int | None = None,
    peer: tuple[str, str] | None = None,
    timeout: int = 60,
    excluded: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Execute matrix benchmark across declared models with optional peer collaboration."""
    _held = _reader_lock()  # noqa: F841
    qs = select_questions(kinds, sample_diagnose)
    benchmarks = [benchmark_single(prov, mod, qs, timeout=timeout) for prov, mod in models]
    coop = None
    if peer and len(models) >= 1:
        lead_prov, lead_mod = models[0]
        peer_prov, peer_mod = peer
        coop = benchmark_cooperative(lead_prov, lead_mod, peer_prov, peer_mod, qs, timeout=timeout)
    return {
        "version": str(atlas().get("version")),
        "question_count": len(qs),
        "kinds": kinds,
        "models": benchmarks,
        "cooperative": coop,
        "discrimination": discrimination(benchmarks),
        "ranking": screen_ranking(benchmarks),
        "excluded": excluded or [],
    }


def parse_model_spec(spec: str) -> tuple[str, str]:
    """Parse 'provider:model' or default to 'router:model'."""
    if ":" in spec:
        p, m = spec.split(":", 1)
        return p.strip(), m.strip()
    return "router", spec.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=cast(str, __doc__).split("\n", 1)[0])
    parser.add_argument("--models", default="router:small,router:code", help="comma-separated provider:model pairs")
    parser.add_argument("--auto", action="store_true", help="auto-discover available providers")
    parser.add_argument(
        "--models-from", default="", help="a `providers.py --census` JSON: every lane that answered AS ITSELF"
    )
    parser.add_argument("--kinds", default="hygiene,plan", help="comma-separated kinds: hygiene,plan,diagnose")
    parser.add_argument("--sample-diagnose", type=int, default=5, help="max diagnose questions to include")
    parser.add_argument("--peer", default="", help="optional reviewer provider:model for cooperative ensemble")
    parser.add_argument("--live", action="store_true", help="invoke live model endpoints")
    parser.add_argument("--timeout", type=int, default=60, help="request timeout seconds")
    parser.add_argument("--json-out", default="", help="path to write output JSON")
    args = parser.parse_args(argv)

    providers.set_live(args.live)
    excluded: list[dict[str, str]] = []
    if args.models_from:
        model_pairs, excluded = providers.census_lanes(json.loads(text_of(Path(args.models_from))))
    elif args.auto:
        active = providers.available_providers()
        print(f"Auto-discovered active providers: {', '.join(active)}")
        # Default models for active providers
        specs: list[str] = []
        if "router" in active:
            specs.extend(["router:small", "router:code"])
        if "kilo" in active:
            specs.append("kilo:small")
        if "google-ai-studio" in active:
            specs.append("google-ai-studio:gemini-2.0-flash")
        model_pairs = [parse_model_spec(s) for s in specs] if specs else [parse_model_spec("router:small")]
    else:
        model_pairs = [parse_model_spec(s) for s in args.models.split(",") if s.strip()]
    peer_pair = parse_model_spec(args.peer) if args.peer.strip() else None
    kinds_list = [k.strip() for k in args.kinds.split(",") if k.strip()]

    matrix = run_matrix(model_pairs, kinds_list, args.sample_diagnose, peer_pair, args.timeout, excluded)
    table = format_matrix_markdown(matrix["models"], matrix.get("cooperative"))
    print("\n# Headron Multi-Model Benchmark Matrix\n")
    print(table)
    print()
    flat = matrix["discrimination"]
    print(
        f"discriminating {len(flat['discriminating'])} · flat pass {len(flat['flat_pass'])} · "
        f"flat fail {len(flat['flat_fail'])} · unmeasured {len(flat['unmeasured'])} (flat tasks are left out)"
    )
    for r in matrix["ranking"]:
        print(f"  {r['lane']:<60} {r['correct']}/{r['answered']}  ci95 {r['ci95']}  not run {r['not_run']}")

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
        print(f"Recorded benchmark matrix to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
