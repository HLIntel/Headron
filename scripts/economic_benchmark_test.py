"""Tests for economic_benchmark.py: every figure comes from a hashed record, and nothing recorded answers unmeasured.

proves: rates and modelled effective figures over paired tasks; routing savings against the UNASSISTED arm, not
  `routed`; an arm with no clean run is never priced below one retry; an unpaired or errored task is left out;
  no record gives status unmeasured, arms None and no fixed claim in the table; each source is hashed
does_not_prove: real-time model API pricing, or that the recorded runs are representative
closed_by: scripts/economic_benchmark_test.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from economic_benchmark import compute_economic_metrics, format_summary_table, load_benchmark_records

ROOT = Path(__file__).resolve().parent.parent


def _run(solved: bool, clean: bool, seconds: float, tokens: int, cost: float) -> dict:
    return {"solved": solved, "gates_clean": clean, "seconds": seconds, "tokens": tokens, "cost_usd": cost}


TASKS = {
    "t1": {"blind": _run(True, True, 20.0, 2000, 0.10), "headron": _run(True, True, 25.0, 2200, 0.11)},
    "t2": {"blind": _run(True, False, 30.0, 3000, 0.15), "headron": _run(True, True, 35.0, 3200, 0.16)},
}
AB = {
    "models": {
        "m1": {
            "unassisted": {"tokens_per_question": 200.0},
            "routed": {"tokens_per_question": 999.0},
            "scoped": {"tokens_per_question": 100.0},
        },
        "m2": {"unassisted": {"tokens_per_question": 100.0}, "scoped": {"tokens_per_question": 80.0}},
        "m3": {"routed": {"tokens_per_question": 50.0}, "scoped": {"tokens_per_question": 10.0}},
    }
}


def test_compute_metrics_realistic() -> None:
    metrics = compute_economic_metrics({"agent": {"tasks": TASKS}, "ab": AB}, ci_cycle_s=100.0, ci_runner_usd=0.05)
    blind, headron = metrics["arms"]["blind"], metrics["arms"]["headron"]
    assert metrics["status"] == "measured" and metrics["paired_tasks"] == 2
    assert (blind["solved_rate"], blind["clean_gates_rate"], blind["rework_rate"]) == (1.0, 0.5, 0.5)
    assert (headron["clean_gates_rate"], headron["rework_rate"]) == (1.0, 0.0)
    assert blind["direct_seconds"] == 25.0 and blind["effective_seconds"] == 87.5
    assert headron["effective_seconds"] == 30.0
    assert blind["effective_cost_usd"] == round(0.125 + 0.5 * (0.125 + 0.05), 4)
    routing = metrics["context_routing"]
    assert routing["baseline"] == "unassisted" and routing["models"] == 2, routing  # m3 has no unassisted cell
    assert routing["per_model_savings_pct"] == {"m1": 50.0, "m2": 20.0}, routing  # never against `routed`
    assert routing["median_savings_pct"] == 35.0
    assert metrics["assumptions"]["ci_cycle_s"] == 100.0
    table = format_summary_table(metrics)
    assert "2 paired tasks" in table and "35.0% fewer" in table and "ASSUMED" in table, table


def test_no_clean_run_is_not_cheapest() -> None:
    tasks = {"t": {"blind": _run(False, False, 10.0, 100, 1.0), "headron": _run(True, True, 10.0, 100, 1.0)}}
    arms = compute_economic_metrics({"agent": {"tasks": tasks}}, ci_runner_usd=0.5)["arms"]
    assert arms["blind"]["effective_cost_usd"] == 2.5, arms["blind"]  # one retry + CI, not the bare 1.0
    assert arms["blind"]["effective_cost_usd"] > arms["headron"]["effective_cost_usd"]


def test_unpaired_and_errored_tasks_left_out() -> None:
    tasks = {
        **TASKS,
        "only_blind": {"blind": _run(True, True, 1.0, 1, 0.01)},
        "errored": {
            "blind": _run(False, False, 1.0, 1, 0.01),
            "headron": {**_run(False, False, 1.0, 1, 0.01), "agent_error": True},
        },
    }
    metrics = compute_economic_metrics({"agent": {"tasks": tasks}})
    assert metrics["paired_tasks"] == 2 and metrics["arms"]["blind"]["total_tasks"] == 2, metrics["arms"]


def test_zero_baseline_says_unmeasured() -> None:
    # A baseline arm that recorded no tokens, time or cost leaves its deltas None; the table must say so, not crash.
    tasks = {"t": {"blind": _run(True, True, 0.0, 0, 0.0), "headron": _run(True, True, 0.0, 0, 0.0)}}
    metrics = compute_economic_metrics({"agent": {"tasks": tasks}}, ci_cycle_s=0.0, ci_runner_usd=0.0)
    assert metrics["advantages"]["direct_token_change_pct"] is None, metrics["advantages"]
    table = format_summary_table(metrics)
    assert "unmeasured (zero baseline)" in table and "None" not in table, table


def test_empty_records_unmeasured() -> None:
    metrics = compute_economic_metrics({})
    assert (metrics["status"], metrics["arms"], metrics["advantages"], metrics["context_routing"]) == (
        "unmeasured",
        None,
        None,
        None,
    ), metrics
    table = format_summary_table(metrics)
    assert table.startswith("UNMEASURED") and "%" not in table, table


def test_sources_are_hashed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bench = Path(tmp) / "benchmarks"
        bench.mkdir()
        assert load_benchmark_records(Path(tmp))["sources"]["agent"]["sha256"] is None
        (bench / "agent-latest.json").write_text(json.dumps({"tasks": TASKS, "measured_at": "1.0"}), encoding="utf-8")
        first = load_benchmark_records(Path(tmp))["sources"]["agent"]
        (bench / "agent-latest.json").write_text(json.dumps({"tasks": {}}), encoding="utf-8")
        second = load_benchmark_records(Path(tmp))["sources"]["agent"]
    assert first["sha256"] and first["sha256"] != second["sha256"] and first["measured_at"] == "1.0"


def run_cases() -> None:
    for case in (
        test_compute_metrics_realistic,
        test_no_clean_run_is_not_cheapest,
        test_unpaired_and_errored_tasks_left_out,
        test_empty_records_unmeasured,
        test_sources_are_hashed,
        test_zero_baseline_says_unmeasured,
    ):
        case()
        print(f"  ok    {case.__name__}")


if __name__ == "__main__":
    run_cases()
    print("PASS  economic_benchmark_test")
