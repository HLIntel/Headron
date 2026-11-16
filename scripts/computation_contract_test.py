"""Contract discovery, structural refusals and declaration isolation."""

from __future__ import annotations

import json

from computation_contract import describe, request_errors


def run_cases() -> None:
    output, refs = describe({})
    assert not refs
    assert json.loads(json.dumps(output)) == output
    assert set(output["request_schemas"]) == {"finance.evaluate", "data.reconcile", "compute.compose"}
    samples = (
        ("finance.evaluate", {"formula": "list"}, True),
        ("finance.evaluate", {"formula": 101}, True),
        ("finance.evaluate", {"formula": True}, False),
        ("finance.evaluate", {}, False),
        ("data.reconcile", {"left": [], "right": []}, True),
        ("data.reconcile", {"left": [], "right": {}}, False),
        ("compute.compose", {"version": "1", "nodes": [{}]}, True),
        ("compute.compose", {"version": "2", "nodes": [{}]}, False),
        ("compute.compose", {"version": "1", "nodes": []}, False),
        ("compute.compose", {"version": "1", "nodes": [{}] * 33}, False),
        ("compute.compose", {"version": "1", "nodes": [{}], "extra": 1}, False),
    )
    for name, request, accepted in samples:
        assert (not request_errors(name, request)) == accepted, (name, request)
    output["request_schemas"]["compute.compose"]["properties"]["version"]["const"] = "2"
    assert not request_errors("compute.compose", {"version": "1", "nodes": [{}]})
    assert describe({"program": "finance.evaluate"})[0]["request_schemas"].keys() == {"finance.evaluate"}
    for invalid in ({"program": []}, {"program": "missing"}, {"extra": 1}):
        try:
            describe(invalid)
        except ValueError:
            continue
        raise AssertionError("invalid contract request accepted")
