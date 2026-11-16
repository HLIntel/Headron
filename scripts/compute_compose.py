"""Bounded computation graph for variance comparisons.

The request is ``{"version": "1", "nodes": [...]}``. A ``finance.variance``
node has ``id``, ``op`` and ``inputs`` containing finance's actual/budget records.
A ``data.reconcile`` node has ``id``, ``op``, ``left`` and ``right``; each side
is a list of ``{"key": str, "ref": variance_node_id}`` records. Nodes may be
submitted in any order. Matched keys must have identical unit, period and metric.

proves: graph shape and metadata are validated before results are returned
does_not_prove: source authenticity, economic comparability, completeness or suitability
closed_by: compute_compose_test.py and independent review of source data and assumptions
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from calculation import Calculation
from domain_reconcile import reconcile
from finance import evaluate, value

_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,31}\Z")
_RECORD = {"measure", "value", "unit", "period", "source", "metric"}
_OPERATIONS = {"finance.variance", "data.reconcile"}
_MAX_NODES = 32
_MAX_ROWS = 128


def _variance(node: Mapping[str, Any]) -> dict[str, Any]:
    inputs = node.get("inputs")
    if not isinstance(inputs, Mapping) or set(inputs) != {"actual", "budget"}:
        raise ValueError("variance requires actual and budget records")
    actual, budget = (inputs[name] for name in ("actual", "budget"))
    if any(not isinstance(row, Mapping) or set(row) != _RECORD for row in (actual, budget)):
        raise ValueError("variance records require measure, value, unit, period, source and metric")
    left, right = value(actual, "actual"), value(budget, "budget")
    metric = actual["metric"]
    if not isinstance(metric, str) or not metric.strip() or len(metric) > 80 or metric != budget["metric"]:
        raise ValueError("variance metrics must be matching nonblank bounded strings")
    if left[1:3] != right[1:3]:
        raise ValueError("variance units and periods must match")
    return {"unit": left[1], "period": dict(actual["period"]), "metric": metric, "sources": [left[3], right[3]]}


def _sides(node: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    sides: dict[str, dict[str, str]] = {}
    for side in ("left", "right"):
        rows = node.get(side)
        if not isinstance(rows, list) or len(rows) > _MAX_ROWS:
            raise ValueError(f"{side} must be a bounded list")
        records: dict[str, str] = {}
        for row in rows:
            if not isinstance(row, Mapping) or set(row) != {"key", "ref"}:
                raise ValueError("reconciliation rows require key and ref")
            key, ref = row["key"], row["ref"]
            if not isinstance(key, str) or not key.strip() or key != key.strip() or len(key) > 80:
                raise ValueError("reconciliation keys must be bounded nonblank strings")
            if not isinstance(ref, str) or not _ID.fullmatch(ref) or key in records:
                raise ValueError("reconciliation refs must be identifiers and keys must be unique per side")
            records[key] = ref
        sides[side] = records
    return sides


def _plan(context: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str], dict[str, dict[str, Any]]]:
    if set(context) != {"version", "nodes"} or context.get("version") != "1":
        raise ValueError("supply graph version 1 and nodes")
    raw = context.get("nodes")
    if not isinstance(raw, list) or not 1 <= len(raw) <= _MAX_NODES:
        raise ValueError("nodes must be a nonempty bounded list")
    nodes: dict[str, dict[str, Any]] = {}
    for node in raw:
        if not isinstance(node, Mapping):
            raise ValueError("each node must be an object")
        name, op = node.get("id"), node.get("op")
        if not isinstance(name, str) or not _ID.fullmatch(name) or name in nodes:
            raise ValueError("node ids must be unique bounded identifiers")
        if not isinstance(op, str) or op not in _OPERATIONS:
            raise ValueError("unknown operation")
        fields = {"id", "op", "inputs"} if op == "finance.variance" else {"id", "op", "left", "right"}
        if set(node) != fields:
            raise ValueError(f"{name}: unexpected or missing node fields")
        nodes[name] = dict(node)
    meta = {name: _variance(node) for name, node in nodes.items() if node["op"] == "finance.variance"}
    sides = {name: _sides(node) for name, node in nodes.items() if node["op"] == "data.reconcile"}
    for name, pair in sides.items():
        for ref in (*pair["left"].values(), *pair["right"].values()):
            if ref not in nodes:
                raise ValueError(f"{name}: unknown reference {ref}")
            if ref not in meta:
                raise ValueError(f"{name}: reference must point to a variance node; cycles are refused")
            preview, _ = evaluate({"formula": "variance.absolute", "inputs": nodes[ref]["inputs"]})
            if len(format(Decimal(preview["value"]), "f")) > 80:
                raise ValueError(f"{name}: variance {ref} exceeds reconciliation decimal limit")
        for key in pair["left"].keys() & pair["right"].keys():
            a, b = (meta[pair[side][key]] for side in ("left", "right"))
            if any(a[field] != b[field] for field in ("unit", "period", "metric")):
                raise ValueError(f"{name}: {key} has incompatible unit, period or metric")
    # The only allowed edges point to source nodes, making this order a topological order.
    order = sorted(meta) + sorted(sides)
    return nodes, order, meta


def compose(context: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    nodes, order, meta = _plan(context)
    results: dict[str, dict[str, Any]] = {}
    refs: list[str] = []
    for name in order:
        node = nodes[name]
        if node["op"] == "finance.variance":
            output, evidence = evaluate({"formula": "variance.absolute", "inputs": node["inputs"]})
            refs.extend(evidence)
            results[name] = {"type": "decimal", "value": output["value"], **meta[name]}
            continue
        sides = _sides(node)
        records: dict[str, list[dict[str, str]]] = {"left": [], "right": []}
        for side, entries in sides.items():
            for key, ref in sorted(entries.items()):
                record, period = results[ref], results[ref]["period"]
                records[side].append(
                    {
                        "key": key,
                        "value": format(Decimal(record["value"]), "f"),
                        "unit": record["unit"],
                        "period": period["start"] + "/" + period["end"],
                        "source": "node:" + ref,
                    }
                )
        comparison, _ = reconcile(records)
        for match in comparison["matched"]:
            left_ref = sides["left"][match["key"]]
            right_ref = sides["right"][match["key"]]
            match["left_sources"] = results[left_ref]["sources"]
            match["right_sources"] = results[right_ref]["sources"]
            del match["left_source"], match["right_source"]
        for side in ("left", "right"):
            comparison[f"{side}_only_sources"] = {
                key: results[sides[side][key]]["sources"] for key in comparison[f"{side}_only"]
            }
        results[name] = {"type": "reconciliation", **comparison}
    return {
        "version": "1",
        "order": order,
        "nodes": results,
        "source_status": "caller_supplied_not_verified",
        "scope": "allowlisted variance and reconciliation; assumptions and sources remain caller assertions",
    }, tuple(refs)


class Compose(Calculation):
    name = "compute.compose"
    version = "1"
    timeout_s = 10.0

    operation = staticmethod(compose)
    next_step = "correct the graph, references or input metadata"
