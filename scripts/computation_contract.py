"""Machine-readable and enforced outer contracts for deterministic calculations.

proves: the same declarations drive discovery and outer request validation
does_not_prove: nested values, cross-field semantics, provenance or source authenticity
closed_by: operation-specific validators and computation_contract_test.py
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from calculation import Calculation
from compute_compose import _MAX_NODES

_SCHEMAS: dict[str, dict[str, Any]] = {
    "finance.evaluate": {
        "type": "object",
        "required": ["formula"],
        "properties": {"formula": {"type": ["string", "integer"]}},
    },
    "data.reconcile": {
        "type": "object",
        "required": ["left", "right"],
        "properties": {"left": {"type": "array"}, "right": {"type": "array"}},
    },
    "compute.compose": {
        "type": "object",
        "required": ["version", "nodes"],
        "additionalProperties": False,
        "properties": {
            "version": {"type": "string", "const": "1"},
            "nodes": {"type": "array", "minItems": 1, "maxItems": _MAX_NODES},
        },
    },
}
_TYPES: dict[str, Any] = {"string": str, "integer": int, "array": list}


def request_errors(program: str, request: Any) -> list[str]:
    """Validate only the advertised outer JSON shape; operation validators decide the rest."""
    schema = _SCHEMAS.get(program)
    if schema is None:
        return []
    if not isinstance(request, Mapping):
        return ["request must be an object"]
    errors = [f"missing {field}" for field in schema["required"] if field not in request]
    properties = schema["properties"]
    if schema.get("additionalProperties") is False and any(field not in properties for field in request):
        errors.append("unexpected field")
    for field, spec in properties.items():
        if field not in request:
            continue
        item = request[field]
        types = spec["type"] if isinstance(spec["type"], list) else [spec["type"]]
        if isinstance(item, bool) or not any(isinstance(item, _TYPES[kind]) for kind in types):
            errors.append(f"invalid type: {field}")
            continue
        if "const" in spec and item != spec["const"]:
            errors.append(f"invalid value: {field}")
        if isinstance(item, list) and not spec.get("minItems", 0) <= len(item) <= spec.get("maxItems", len(item)):
            errors.append(f"invalid length: {field}")
    return errors


def describe(context: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    if set(context) - {"program"}:
        raise ValueError("supply only an optional program")
    program = context.get("program")
    if program is not None and (not isinstance(program, str) or program not in _SCHEMAS):
        raise ValueError("unknown calculation program")
    selected = {program: _SCHEMAS[program]} if program else _SCHEMAS
    return {
        "version": "1",
        "request_schemas": deepcopy(selected),
        "scope": "outer request shape only; operation validators enforce nested values and semantics",
        "source_status": "caller_supplied_not_verified",
    }, ()


class ComputationContract(Calculation):
    name = "compute.contract"
    version = "1"
    timeout_s = 10.0

    operation = staticmethod(describe)
    next_step = "request a known calculation program or omit program to list contracts"
