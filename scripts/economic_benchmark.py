#!/usr/bin/env python3
"""Economic benchmark: Headron-assisted vs unassisted agents, from the recorded runs only.

WHY. The first version printed a fixed summary ("100% first-pass hygiene ... 40.6% ... 18.7%") whatever the
records said, measured routing savings against the `routed` arm instead of the unassisted one, fell back to
hard-coded token counts when no A/B was recorded, and priced an arm with no clean run as its bare direct cost
(so the worst arm looked cheapest). Every number now comes from a named, hashed record; what is assumed (the CI
cycle) is labelled assumed; what was not recorded answers None and the CLI exits 2.

proves: per arm, over tasks recorded in BOTH arms, the solve, clean-gate and rework rates, direct seconds, tokens
  and cost; the modelled effective time, tokens and cost under one retry per unclean task; the median per-model
  scoped-vs-unassisted token saving from the A/B; the sha256 of every record read
does_not_prove: significance (n is small and is printed), future prices, or the CI cycle cost (an assumption)
closed_by: scripts/economic_benchmark_test.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Any

from atlascore import ROOT, text_of

# ASSUMED, not measured: one CI cycle a rework costs. Shown in every output under `assumptions`.
DEFAULT_CI_CYCLE_SECONDS = 300.0
DEFAULT_CI_RUNNER_COST_USD = 0.05
ARMS = ("blind", "headron")
SOURCES = {"agent": "agent-latest.json", "ab": "ab-latest.json", "enforce": "enforce-latest.json"}


def load_benchmark_records(root: Path = ROOT) -> dict[str, Any]:
    """Each recorded benchmark, {} when absent, and under `sources` the path and sha256 of what was read."""
    records: dict[str, Any] = {"sources": {}}
    for key, name in SOURCES.items():
        path = root / "benchmarks" / name
        body = path.read_bytes() if path.is_file() else None
        records[key] = json.loads(text_of(path)) if body is not None else {}
        records["sources"][key] = {
            "path": f"benchmarks/{name}",
            "sha256": hashlib.sha256(body).hexdigest() if body is not None else None,
            "measured_at": records[key].get("measured_at"),
        }
    return records


def paired_tasks(tasks: dict[str, Any]) -> dict[str, Any]:
    """Tasks recorded in both arms with no agent error: an arm missing a task is not a failure it scored."""
    return {
        name: task
        for name, task in tasks.items()
        if all(isinstance(task.get(arm), dict) and not task[arm].get("agent_error") for arm in ARMS)
    }


def arm_summary(tasks: dict[str, Any], arm: str, ci_cycle_s: float, ci_runner_usd: float) -> dict[str, Any]:
    """One arm over the paired tasks. Effective = direct + rework_rate * (one more attempt + one CI cycle)."""
    n = len(tasks)
    rows = [task[arm] for task in tasks.values()]
    solved = sum(bool(r.get("solved")) for r in rows)
    clean = sum(bool(r.get("gates_clean")) for r in rows)
    rework = 1.0 - clean / n
    avg_s = sum(float(r.get("seconds") or 0.0) for r in rows) / n
    avg_tok = sum(int(r.get("tokens") or 0) for r in rows) / n
    avg_cost = sum(float(r.get("cost_usd") or 0.0) for r in rows) / n
    return {
        "solved_count": solved,
        "total_tasks": n,
        "solved_rate": round(solved / n, 4),
        "clean_gates_count": clean,
        "clean_gates_rate": round(clean / n, 4),
        "rework_rate": round(rework, 4),
        "direct_seconds": round(avg_s, 2),
        "effective_seconds": round(avg_s + rework * (avg_s + ci_cycle_s), 2),
        "direct_tokens": round(avg_tok, 1),
        "effective_tokens": round(avg_tok * (1.0 + rework), 1),
        "direct_cost_usd": round(avg_cost, 4),
        "effective_cost_usd": round(avg_cost + rework * (avg_cost + ci_runner_usd), 4),
    }


def routing_savings(ab: dict[str, Any]) -> dict[str, Any] | None:
    """Scoped vs UNASSISTED tokens per question, per model that recorded both; the median across them. None if none."""
    per_model = {}
    for model, cell in (ab.get("models") or {}).items():
        base = (cell.get("unassisted") or {}).get("tokens_per_question")
        scoped = (cell.get("scoped") or {}).get("tokens_per_question")
        if base and scoped is not None:
            per_model[model] = round((1.0 - float(scoped) / float(base)) * 100, 1)
    if not per_model:
        return None
    return {
        "baseline": "unassisted",
        "models": len(per_model),
        "median_savings_pct": round(statistics.median(per_model.values()), 1),
        "per_model_savings_pct": per_model,
    }


def compute_economic_metrics(
    records: dict[str, Any],
    ci_cycle_s: float = DEFAULT_CI_CYCLE_SECONDS,
    ci_runner_usd: float = DEFAULT_CI_RUNNER_COST_USD,
) -> dict[str, Any]:
    """Both arms over paired tasks, routing savings, and the deltas; None wherever nothing was recorded."""
    tasks = paired_tasks((records.get("agent") or {}).get("tasks") or {})
    arms = {arm: arm_summary(tasks, arm, ci_cycle_s, ci_runner_usd) for arm in ARMS} if tasks else None
    advantages = None
    if arms:
        blind, headron = arms["blind"], arms["headron"]
        advantages = {
            "first_pass_hygiene_gain_pct": round((headron["clean_gates_rate"] - blind["clean_gates_rate"]) * 100, 1),
            "direct_token_change_pct": round((headron["direct_tokens"] / blind["direct_tokens"] - 1.0) * 100, 1)
            if blind["direct_tokens"]
            else None,
            "effective_time_to_green_ratio": round(blind["effective_seconds"] / headron["effective_seconds"], 2)
            if headron["effective_seconds"]
            else None,
            "effective_token_savings_pct": round(
                (1.0 - headron["effective_tokens"] / blind["effective_tokens"]) * 100, 1
            )
            if blind["effective_tokens"]
            else None,
            "effective_cost_savings_pct": round(
                (1.0 - headron["effective_cost_usd"] / blind["effective_cost_usd"]) * 100, 1
            )
            if blind["effective_cost_usd"]
            else None,
        }
    return {
        "schema": 2,
        "command": "economic_benchmark",
        "status": "measured" if arms else "unmeasured",
        "paired_tasks": len(tasks),
        "arms": arms,
        "context_routing": routing_savings(records.get("ab") or {}),
        "advantages": advantages,
        "assumptions": {
            "ci_cycle_s": ci_cycle_s,
            "ci_runner_usd": ci_runner_usd,
            "why": "assumed, not measured: effective = direct + rework_rate * (one more attempt + one CI cycle)",
        },
        "sources": records.get("sources") or {},
    }


def format_summary_table(metrics: dict[str, Any]) -> str:
    """The comparison as text, every figure from `metrics`; says so when nothing was recorded."""
    if not metrics["arms"]:
        return "UNMEASURED: no task is recorded in both arms of benchmarks/agent-latest.json; nothing to compare"
    blind, headron, adv = metrics["arms"]["blind"], metrics["arms"]["headron"], metrics["advantages"]
    n = metrics["paired_tasks"]

    def row(label: str, key: str, fmt: str, note: str = "") -> str:
        return f"{label:<26} {format(blind[key], fmt):<20} {format(headron[key], fmt):<20} {note}"

    lines = [
        "=" * 78,
        f"HEADRON ECONOMIC BENCHMARK: ASSISTED VS UNASSISTED ({n} paired task{'s' if n != 1 else ''})",
        "=" * 78,
        f"{'Dimension':<26} {'Unassisted':<20} {'Headron':<20} Delta",
        "-" * 78,
        row("Solved", "solved_count", "d", f"of {n}"),
        row("Clean gates", "clean_gates_count", "d", f"{adv['first_pass_hygiene_gain_pct']:+.1f} pts"),
        row("Direct seconds", "direct_seconds", ".1f"),
        row("Direct tokens", "direct_tokens", ".0f", f"{adv['direct_token_change_pct']:+.1f}%"),
        row("Direct cost USD", "direct_cost_usd", ".4f"),
        row("Effective seconds*", "effective_seconds", ".1f", f"{adv['effective_time_to_green_ratio']}x"),
        row("Effective tokens*", "effective_tokens", ".0f", f"{adv['effective_token_savings_pct']}% saved"),
        row("Effective cost USD*", "effective_cost_usd", ".4f", f"{adv['effective_cost_savings_pct']}% saved"),
    ]
    if routing := metrics["context_routing"]:
        lines.append(
            f"Context tokens/question: scoped vs unassisted, median over {routing['models']} models: "
            f"{routing['median_savings_pct']}% fewer"
        )
    lines += [
        "-" * 78,
        f"* modelled: one retry per unclean task plus an ASSUMED CI cycle of {metrics['assumptions']['ci_cycle_s']:g}s.",
        f"  n = {n}: a one-task difference moves a rate by {100 / n:.0f} points; no significance is claimed.",
        "=" * 78,
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Exit 0 when both arms were recorded, 2 when nothing was (no comparison is printed as one)."""
    parser = argparse.ArgumentParser(
        prog="economic_benchmark.py",
        description="Compare Headron-assisted and unassisted agents from the recorded benchmark runs.",
    )
    parser.add_argument("--json", action="store_true", help="emit the comparison as a JSON record")
    args = parser.parse_args(argv)
    metrics = compute_economic_metrics(load_benchmark_records(ROOT))
    print(json.dumps(metrics, indent=2) if args.json else format_summary_table(metrics))
    return 0 if metrics["arms"] else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
