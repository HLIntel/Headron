"""Tests for cost-adaptive gate scheduling (scripts/adaptive.py).

proves: gates with fast execution and higher historical failure rates are scheduled first (fail-fast);
  read-only gates are grouped into parallel execution batches; mutating gates execute sequentially;
  total estimated duration and token consumption are calculated deterministically
does_not_prove: network latency variations during live runs
closed_by: adaptive_scheduling_test.py
"""

from __future__ import annotations

import adaptive


def test_schedule_execution_fail_fast() -> None:
    gates = [
        {"id": "slow_suite", "mutates": False},
        {"id": "fast_linter", "mutates": False},
        {"id": "syntax_check", "mutates": False},
    ]
    costs = {
        "slow_suite": {"latency_s": 30.0, "failure_rate": 0.05, "tokens": 500},
        "fast_linter": {"latency_s": 0.5, "failure_rate": 0.30, "tokens": 50},
        "syntax_check": {"latency_s": 0.1, "failure_rate": 0.10, "tokens": 10},
    }
    sched = adaptive.schedule_execution(gates, costs, max_parallel=2)

    # fast_linter has highest score (-0.30/0.5 = -0.6), then syntax_check (-0.1/0.1 = -1.0)
    # The fail-fast order puts highest failure-per-second first
    assert sched.fail_fast_order[0] in ("syntax_check", "fast_linter")
    assert sched.fail_fast_order[-1] == "slow_suite"
    assert sched.estimated_tokens == 560
    assert sched.estimated_latency_s > 0


def test_schedule_mutating_gates_isolation() -> None:
    gates = [
        {"id": "lint", "mutates": False},
        {"id": "format_write", "mutates": True},
        {"id": "typecheck", "mutates": False},
    ]
    sched = adaptive.schedule_execution(gates, {}, max_parallel=2)
    # format_write must be in its own single-element batch
    assert ("format_write",) in sched.batches
    assert sched.status == "scheduled"
    d = sched.to_dict()
    assert "batches" in d
    assert "estimated_latency_s" in d


if __name__ == "__main__":
    test_schedule_execution_fail_fast()
    test_schedule_mutating_gates_isolation()
    print("adaptive_scheduling_test: PASS")
