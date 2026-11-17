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
import taskbench
from abtest import _reader_lock
from atlascore import atlas


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
        "overall": {"blind_correct": 0, "headron_correct": 0, "total": 0, "blind_tokens": 0, "headron_tokens": 0},
    }
    for q in questions:
        kind = q["kind"]
        k_entry = summary["kinds"].setdefault(
            kind,
            {
                "blind": {"correct": 0, "asked": 0, "tokens": 0, "latency_s": 0.0},
                "headron": {"correct": 0, "asked": 0, "tokens": 0, "latency_s": 0.0},
            },
        )
        for arm in ("blind", "headron"):
            t0 = time.monotonic()
            ans, tok = providers.complete(provider, model, q[arm], timeout, max_tokens)
            elapsed = time.monotonic() - t0
            tok_count = tok or 0
            v = taskbench.score(q, ans) if ans.strip() else None
            is_correct = bool(v)
            cell = k_entry[arm]
            cell["asked"] += 1
            cell["correct"] += int(is_correct)
            cell["tokens"] += tok_count
            cell["latency_s"] += elapsed
            summary["overall"][f"{arm}_correct"] += int(is_correct)
            summary["overall"][f"{arm}_tokens"] += tok_count
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
        "total": len(questions),
        "tokens": 0,
        "latency_s": 0.0,
    }
    for q in questions:
        t0 = time.monotonic()
        lead_ans, lead_tok = providers.complete(lead_provider, lead_model, q["headron"], timeout, max_tokens)
        review_prompt = (
            f"{q['headron']}\n\nA teammate drafted this answer:\n{lead_ans}\n"
            "Review the draft against the rules above. Output the verified final answer only."
        )
        peer_ans, peer_tok = providers.complete(peer_provider, peer_model, review_prompt, timeout, max_tokens)
        elapsed = time.monotonic() - t0
        v = taskbench.score(q, peer_ans) if peer_ans.strip() else None
        results["correct"] += int(bool(v))
        results["tokens"] += (lead_tok or 0) + (peer_tok or 0)
        results["latency_s"] += elapsed
    return results


def format_matrix_markdown(benchmarks: list[dict[str, Any]], cooperative: dict[str, Any] | None = None) -> str:
    """Render a clean Markdown comparative matrix table."""
    lines = [
        "| Model / Pipeline | Blind Acc | Headron Acc | Acc Lift | Tokens (Blind/Headron) | Avg Latency |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for b in benchmarks:
        ov = b["overall"]
        tot = ov["total"] or 1
        b_acc = (ov["blind_correct"] / tot) * 100
        h_acc = (ov["headron_correct"] / tot) * 100
        lift = h_acc - b_acc
        b_tok = ov["blind_tokens"] // tot
        h_tok = ov["headron_tokens"] // tot
        latencies = [c["latency_s"] / max(c["asked"], 1) for k in b["kinds"].values() for c in k.values()]
        avg_lat = sum(latencies) / max(len(latencies), 1)
        name = f"`{b['provider']}:{b['model']}`"
        lines.append(f"| {name} | {b_acc:.1f}% | {h_acc:.1f}% | +{lift:.1f}% | {b_tok} / {h_tok} | {avg_lat:.2f}s |")
    if cooperative:
        tot_c = cooperative["total"] or 1
        c_acc = (cooperative["correct"] / tot_c) * 100
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
    parser.add_argument("--kinds", default="hygiene,plan", help="comma-separated kinds: hygiene,plan,diagnose")
    parser.add_argument("--sample-diagnose", type=int, default=5, help="max diagnose questions to include")
    parser.add_argument("--peer", default="", help="optional reviewer provider:model for cooperative ensemble")
    parser.add_argument("--live", action="store_true", help="invoke live model endpoints")
    parser.add_argument("--timeout", type=int, default=60, help="request timeout seconds")
    parser.add_argument("--json-out", default="", help="path to write output JSON")
    args = parser.parse_args(argv)

    providers.set_live(args.live)
    model_pairs = [parse_model_spec(s) for s in args.models.split(",") if s.strip()]
    peer_pair = parse_model_spec(args.peer) if args.peer.strip() else None
    kinds_list = [k.strip() for k in args.kinds.split(",") if k.strip()]

    matrix = run_matrix(model_pairs, kinds_list, args.sample_diagnose, peer_pair, args.timeout)
    table = format_matrix_markdown(matrix["models"], matrix.get("cooperative"))
    print("\n# Headron Multi-Model Benchmark Matrix\n")
    print(table)
    print()

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
        print(f"Recorded benchmark matrix to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
