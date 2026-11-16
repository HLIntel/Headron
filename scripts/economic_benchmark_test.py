"""Tests for economic_benchmark.py.

proves: economic metric calculations (quality, time, tokens, cost) and output formatting
does_not_prove: real-time model API pricing fluctuations
closed_by: scripts/economic_benchmark_test.py
"""

from __future__ import annotations

from pathlib import Path

from economic_benchmark import compute_economic_metrics, format_summary_table

ROOT = Path(__file__).resolve().parent.parent


def test_compute_metrics_realistic() -> None:
    records = {
        "agent": {
            "tasks": {
                "t1": {
                    "blind": {"solved": True, "gates_clean": True, "seconds": 20.0, "tokens": 2000, "cost_usd": 0.10},
                    "headron": {"solved": True, "gates_clean": True, "seconds": 25.0, "tokens": 2200, "cost_usd": 0.11},
                },
                "t2": {
                    "blind": {"solved": True, "gates_clean": False, "seconds": 30.0, "tokens": 3000, "cost_usd": 0.15},
                    "headron": {"solved": True, "gates_clean": True, "seconds": 35.0, "tokens": 3200, "cost_usd": 0.16},
                },
            }
        },
        "ab": {"models": {"m1": {"routed": {"tokens_per_question": 200.0}, "scoped": {"tokens_per_question": 100.0}}}},
    }

    metrics = compute_economic_metrics(records, ci_cycle_s=100.0, ci_runner_usd=0.05)
    blind = metrics["arms"]["blind"]
    headron = metrics["arms"]["headron"]

    assert blind["solved_rate"] == 1.0
    assert blind["clean_gates_rate"] == 0.5
    assert blind["rework_rate"] == 0.5
    assert headron["clean_gates_rate"] == 1.0
    assert headron["rework_rate"] == 0.0

    # Effective time checks
    assert blind["direct_seconds"] == 25.0
    # effective = 25 + 0.5 * (25 + 100) = 87.5
    assert blind["effective_seconds"] == 87.5
    assert headron["effective_seconds"] == 30.0

    # Context routing
    assert metrics["context_routing"]["context_token_savings_pct"] == 50.0

    table = format_summary_table(metrics)
    assert "HEADRON ECONOMIC BENCHMARK" in table
    assert "Task Solve Rate" in table


def test_empty_records_safe() -> None:
    metrics = compute_economic_metrics({})
    assert metrics["schema"] == 1
    assert "arms" in metrics
    assert metrics["arms"]["blind"]["solved_rate"] == 0.0


def run_cases() -> None:
    test_compute_metrics_realistic()
    print("  ok    economic benchmark realistic calculation")
    test_empty_records_safe()
    print("  ok    economic benchmark handles empty records safely")


if __name__ == "__main__":
    run_cases()
    print("PASS  economic_benchmark_test")
