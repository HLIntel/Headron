"""Compare caller-supplied records by declared key, unit, and period.

proves: matched values are subtracted only when their declared units and periods agree
does_not_prove: source authenticity, completeness, key identity, or economic comparability
closed_by: independent review of source records and their matching definitions
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Context, Decimal, localcontext
from typing import Any

from calculation import Calculation

_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_FIELDS = {"key", "value", "unit", "period", "source"}


def _records(raw: Any, side: str) -> dict[str, dict[str, str]]:
    if not isinstance(raw, list) or len(raw) > 500:
        raise ValueError(f"{side} must be a list of at most 500 records")
    rows: dict[str, dict[str, str]] = {}
    for row in raw:
        if not isinstance(row, Mapping) or set(row) != _FIELDS:
            raise ValueError(f"{side} records require key, value, unit, period, and source")
        for name in _FIELDS:
            value = row[name]
            limit = 512 if name == "source" else 80
            if not isinstance(value, str) or not value.strip() or len(value) > limit or value != value.strip():
                raise ValueError(f"{side} record {name} must be bounded nonblank text without surrounding whitespace")
        if not _NUMBER.fullmatch(row["value"]):
            raise ValueError(f"{side} values must be plain decimal strings")
        if row["key"] in rows:
            raise ValueError(f"{side} contains a duplicate key")
        rows[row["key"]] = dict(row)
    return rows


def reconcile(context: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Match exact keys; return differences and unmatched records without imputing values."""
    left, right = (_records(context.get(side), side) for side in ("left", "right"))
    matched = []
    with localcontext(Context(prec=160)):
        for key in sorted(left.keys() & right.keys()):
            a, b = left[key], right[key]
            if a["unit"] != b["unit"] or a["period"] != b["period"]:
                raise ValueError(f"{key}: declared unit and period must match")
            difference = Decimal(a["value"]) - Decimal(b["value"])
            matched.append(
                {
                    "key": key,
                    "left": a["value"],
                    "right": b["value"],
                    "left_source": a["source"],
                    "right_source": b["source"],
                    "difference": str(difference),
                    "status": "equal" if difference == 0 else "different",
                    "unit": a["unit"],
                    "period": a["period"],
                }
            )
    refs = tuple(row["source"] for records in (left, right) for row in records.values())
    return {
        "matched": matched,
        "left_only": sorted(left.keys() - right.keys()),
        "right_only": sorted(right.keys() - left.keys()),
        "left_count": len(left),
        "right_count": len(right),
        "source_status": "caller_supplied_not_verified",
        "scope": "exact key and declared metadata only; completeness and identity are not verified",
    }, refs


class Reconcile(Calculation):
    name = "data.reconcile"
    version = "1"
    timeout_s = 10.0

    operation = staticmethod(reconcile)
    next_step = "correct the records"
