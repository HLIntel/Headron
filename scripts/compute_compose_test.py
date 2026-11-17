"""Known answers and refusal cases for composed financial computations."""

from __future__ import annotations

import decimal
from copy import deepcopy
from datetime import date

import receipt
from compute_compose import Compose


def _variance(name: str, actual: str, budget: str) -> dict:
    period = {"start": date.fromordinal(1).isoformat(), "end": date.fromordinal(2).isoformat()}
    return {
        "id": name,
        "op": "finance.variance",
        "inputs": {
            "actual": {
                "measure": "actual",
                "value": actual,
                "unit": "USD",
                "period": period,
                "source": f"{name}:actual",
                "metric": "revenue",
            },
            "budget": {
                "measure": "budget",
                "value": budget,
                "unit": "USD",
                "period": period,
                "source": f"{name}:budget",
                "metric": "revenue",
            },
        },
    }


def _graph() -> dict:
    return {
        "version": "1",
        "nodes": [
            {
                "id": "compare",
                "op": "data.reconcile",
                "left": [{"key": "revenue", "ref": "a"}],
                "right": [{"key": "revenue", "ref": "b"}],
            },
            _variance("b", "130", "110"),
            _variance("a", "115", "100"),
        ],
    }


def test_known_answer_and_provenance() -> None:
    result = Compose().run(_graph())
    assert result.status == "ok"
    assert result.output["order"] == ["a", "b", "compare"]
    matched = result.output["nodes"]["compare"]["matched"][0]
    assert matched["difference"] == "-5"
    assert matched["left_sources"] == ["a:actual", "a:budget"]
    assert matched["right_sources"] == ["b:actual", "b:budget"]
    assert "left_source" not in matched and "right_source" not in matched
    assert result.evidence_refs == ("a:actual", "a:budget", "b:actual", "b:budget")


def test_matched_metadata_must_agree() -> None:
    values = {
        "unit": "EUR",
        "period": {"start": date.fromordinal(3).isoformat(), "end": date.fromordinal(4).isoformat()},
        "metric": "cost",
    }
    for field, value in values.items():
        graph = _graph()
        for record in graph["nodes"][1]["inputs"].values():
            record[field] = value
        result = Compose().run(graph)
        assert result.status == "refused"
        assert result.output is None


def _invalid_graphs() -> list[dict]:
    graphs = [_graph() for _ in range(8)]
    graphs[0]["version"] = "2"
    graphs[1]["nodes"].append(deepcopy(graphs[1]["nodes"][-1]))
    graphs[2]["nodes"][1]["op"] = ["finance.variance"]
    graphs[3]["nodes"][0]["left"][0]["ref"] = "missing"
    graphs[4]["nodes"][0]["left"][0]["ref"] = "compare"
    graphs[5]["nodes"][0]["left"].append(deepcopy(graphs[5]["nodes"][0]["left"][0]))
    graphs[6]["nodes"][1]["inputs"]["actual"]["value"] = "NaN"
    graphs[7]["nodes"].extend(_variance(f"n{i}", "1", "0") for i in range(32))
    return graphs


def test_invalid_graph_refused() -> None:
    for graph in _invalid_graphs():
        result = Compose().run(graph)
        assert result.status == "refused"
        assert result.output is None


def test_unmatched_keys_do_not_invent_a_comparison() -> None:
    graph = _graph()
    graph["nodes"][0]["right"][0]["key"] = "other"
    result = Compose().run(graph)
    output = result.output["nodes"]["compare"]
    assert result.status == "ok"
    assert output["matched"] == []
    assert output["left_only"] == ["revenue"]
    assert output["right_only"] == ["other"]
    assert output["left_only_sources"] == {"revenue": ["a:actual", "a:budget"]}
    assert output["right_only_sources"] == {"other": ["b:actual", "b:budget"]}


def test_unhashable_operation_is_refused() -> None:
    for op in ([], {}):
        graph = _graph()
        graph["nodes"][1]["op"] = op
        result = Compose().run(graph)
        assert result.status == "refused"
        assert result.output is None


def test_variance_above_reconcile_limit_is_refused() -> None:
    graph = _graph()
    graph["nodes"][2] = _variance("a", "9" * 80, "-1")
    result = Compose().run(graph)
    assert result.status == "refused"
    assert result.output is None


def test_output_reproducible_with_explicit_units() -> None:
    """Same graph, same bytes: twice, and under a caller's coarse decimal context; every number a string with a unit."""
    graph = _graph()
    graph["nodes"][2] = _variance("a", "1234567.891", "0.003")  # needs 10 digits; a 2-digit context would round it
    out = Compose().run(graph).output
    assert out["nodes"]["a"]["value"] == "1234567.888", out["nodes"]["a"]
    first = receipt.digest(out)
    assert receipt.digest(Compose().run(deepcopy(graph)).output) == first
    with decimal.localcontext() as ctx:
        ctx.prec, ctx.rounding = 2, decimal.ROUND_DOWN
        assert receipt.digest(Compose().run(deepcopy(graph)).output) == first, "a caller's decimal context leaked in"
    for node in Compose().run(_graph()).output["nodes"].values():
        for row in [node, *node.get("matched", [])]:
            assert not any(isinstance(v, float) for v in row.values()), row
            assert row.get("type") == "reconciliation" or row.get("unit"), row


def run_cases() -> None:
    test_known_answer_and_provenance()
    test_output_reproducible_with_explicit_units()
    test_matched_metadata_must_agree()
    test_invalid_graph_refused()
    test_unmatched_keys_do_not_invent_a_comparison()
    test_unhashable_operation_is_refused()
    test_variance_above_reconcile_limit_is_refused()
