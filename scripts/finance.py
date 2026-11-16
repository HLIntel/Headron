"""On-demand, read-only financial equations with explicit input semantics.

proves: supported calculations use declared decimal inputs and refuse incompatible units or periods
does_not_prove: that a supplied value, source, classification, tax assumption or decision is correct
closed_by: microprogram_test.py, which checks examples and plants incompatible inputs
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any

from calculation import Calculation

CATALOG = {
    "cost_of_debt.historical": "interest expense / average interest-bearing debt for the same period",
    "variance.absolute": "actual minus budget for the same measure, unit and period",
}
FORMULA_IDS = {
    101: "cost_of_debt.historical",
    102: "variance.absolute",
    103: "capital.periodic",
    104: "instrument.lookup",
    105: "concept.lookup",
    106: "source.lookup",
    107: "series.visual",
}
INPUTS = {
    101: ("inputs.interest_expense", "inputs.average_interest_bearing_debt"),
    102: ("inputs.actual", "inputs.budget"),
    103: ("cash_flows", "rate", "currency", "period_unit", "source"),
    104: (),
    105: (),
    106: (),
    107: ("values",),
}
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


def value(raw: Any, measure: str) -> tuple[Decimal, str, tuple[str, str], str]:
    """Read a bounded plain decimal and caller-supplied descriptive metadata."""
    if not isinstance(raw, Mapping) or raw.get("measure") != measure:
        raise ValueError(f"{measure}: supply the declared measure")
    number, unit, period, source = (raw.get(k) for k in ("value", "unit", "period", "source"))
    if not isinstance(number, str) or len(number) > 80 or not _DECIMAL.fullmatch(number):
        raise ValueError(f"{measure}: value must be a bounded plain decimal string")
    if not isinstance(unit, str) or not re.fullmatch(r"[A-Z]{3}", unit):
        raise ValueError(f"{measure}: unit must be a three-letter currency code")
    if not isinstance(period, Mapping) or set(period) != {"start", "end"}:
        raise ValueError(f"{measure}: supply start and end dates")
    start, end = period["start"], period["end"]
    try:
        if not isinstance(start, str) or not isinstance(end, str):
            raise ValueError
        if date.fromisoformat(start).isoformat() != start or date.fromisoformat(end).isoformat() != end or start > end:
            raise ValueError
    except ValueError:
        raise ValueError(f"{measure}: period must contain ordered ISO dates") from None
    if not isinstance(source, str) or not source.strip() or len(source) > 512:
        raise ValueError(f"{measure}: supply a source locator")
    return Decimal(number), unit, (start, end), source


def evaluate(context: Mapping[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    formula, inputs = context.get("formula"), context.get("inputs")
    if isinstance(formula, int) and not isinstance(formula, bool):
        formula = FORMULA_IDS.get(formula)
    if formula == "list":
        return {
            "formulas": {
                **CATALOG,
                "capital.periodic": "NPV, net profitability index and discounted payback",
                "instrument.lookup": "static reference universe by identifier, symbol or kind",
                "concept.lookup": "financial vocabulary, equations and assumptions",
                "source.lookup": "public research pages by topic or identifier",
                "series.visual": "compact offline visualization of supplied values",
            },
            "identifiers": FORMULA_IDS,
            "required_inputs": INPUTS,
            "lookup_query": "optional exact identifier, label, symbol or topic as applicable",
            "reference": "docs/FINANCE.md",
        }, ()
    if formula == "capital.periodic":
        from finance_capital import capital  # noqa: PLC0415

        return capital(dict(context))
    if formula == "instrument.lookup":
        from finance_catalog import catalog  # noqa: PLC0415

        return catalog(dict(context)), ()
    if formula == "concept.lookup":
        from finance_knowledge import lookup  # noqa: PLC0415

        return lookup(dict(context)), ()
    if formula in ("source.lookup", "series.visual"):
        from finance_knowledge import sources, visual  # noqa: PLC0415

        return (sources(dict(context)) if formula == "source.lookup" else visual(dict(context))), ()
    if formula not in CATALOG or not isinstance(inputs, Mapping):
        raise ValueError("choose a listed formula and supply its inputs")
    if formula == "cost_of_debt.historical":
        names = ("interest_expense", "average_interest_bearing_debt")
    else:
        names = ("actual", "budget")
    if set(inputs) != set(names):
        raise ValueError(f"{formula}: supply exactly {', '.join(names)}")
    left, right = (value(inputs[name], name) for name in names)
    if left[1:3] != right[1:3]:
        raise ValueError("inputs must have the same currency and period")
    if formula == "variance.absolute":
        metric = inputs["actual"].get("metric")
        if not isinstance(metric, str) or not metric.strip() or metric != inputs["budget"].get("metric"):
            raise ValueError("actual and budget must declare the same metric")
    precision = 34 if formula == "cost_of_debt.historical" else 160
    with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
        if formula == "cost_of_debt.historical":
            if left[0] < 0 or right[0] <= 0:
                raise ValueError("interest expense must be nonnegative and average debt positive")
            result, unit = left[0] / right[0], "ratio"
        else:
            result, unit = left[0] - right[0], left[1]
    return {
        "formula": formula,
        "equation": CATALOG[formula],
        "value": str(result),
        "unit": unit,
        "period": {"start": left[2][0], "end": left[2][1]},
        "precision": precision,
        "rounding": "half_even",
        "source_status": "caller_supplied_not_verified",
        "interpretation": "period rate; not annualized or a market borrowing rate"
        if unit == "ratio"
        else "actual minus budget; favorability is not inferred",
    }, (left[3], right[3])


class Finance(Calculation):
    name = "finance.evaluate"
    version = "1"
    timeout_s = 10.0

    operation = staticmethod(evaluate)
    next_step = "correct the inputs or request formula list"
