"""Periodic capital budgeting, with declared timing and no inferred cash flows."""

from __future__ import annotations

import re
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from typing import Any

_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")


def number(raw: Any) -> Decimal:
    if not isinstance(raw, str) or len(raw) > 80 or not _NUMBER.fullmatch(raw):
        raise ValueError("amounts and rate must be bounded plain decimal strings")
    return Decimal(raw)


def _npv_bounds(amounts: list[Decimal], rate: Decimal, precision: int) -> list[list[Decimal]]:
    """Enclose each cumulative NPV with outward-rounded factors, products and sums."""
    factors = []
    for rounding in (ROUND_FLOOR, ROUND_CEILING):
        with localcontext(Context(prec=precision, rounding=rounding)):
            base, factor = 1 + rate, Decimal(1)
            row = []
            for _ in amounts:
                row.append(factor)
                factor /= base
            factors.append(row)
    bounds = []
    for side, rounding in enumerate((ROUND_FLOOR, ROUND_CEILING)):
        with localcontext(Context(prec=precision, rounding=rounding)):
            total = Decimal(0)
            row = []
            for i, amount in enumerate(amounts):
                index = side if amount >= 0 else 1 - side
                total += amount * factors[index][i]
                row.append(total)
            bounds.append(row)
    return bounds


def _sign(lower: Decimal, upper: Decimal, amounts: list[Decimal], rate: Decimal, allow_exact: bool) -> int:
    """Decide the sign only when bounds or a bounded exact zero establish it."""
    if lower > 0:
        return 1
    if upper < 0:
        return -1
    if lower == upper == 0:
        return 0
    if allow_exact:
        base = 1 + Fraction(rate)
        if sum((Fraction(amount) / base**i for i, amount in enumerate(amounts)), Fraction()) == 0:
            return 0
    raise ValueError("NPV sign is indeterminate at the available precision")


def capital(context: dict[str, Any]) -> tuple[dict[str, Any], tuple[str, ...]]:
    if set(context) != {"formula", "cash_flows", "rate", "currency", "period_unit", "source"}:
        raise ValueError("supply only the declared capital inputs; timing is fixed at period ends")
    flows, rate = context.get("cash_flows"), number(context.get("rate"))
    currency, period, source = (context.get(k) for k in ("currency", "period_unit", "source"))
    if not isinstance(flows, list) or not 2 <= len(flows) <= 1000:
        raise ValueError("cash_flows must contain the initial outflow and subsequent periods")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("currency must be a three-letter code")
    if period not in ("year", "quarter", "month") or rate <= -1:
        raise ValueError("declare a period unit and a rate greater than -1 per period")
    if not isinstance(source, str) or not source.strip() or len(source) > 512:
        raise ValueError("supply a source locator")
    amounts = [number(flow) for flow in flows]
    if amounts[0] >= 0:
        raise ValueError("the initial cash flow must be negative")
    precision = max(34, 2 * max(len(flow) for flow in flows + [context["rate"]]) + 4)
    bounds = _npv_bounds(amounts, rate, precision)
    allow_exact = len(amounts) <= 32 and max(len(flow) for flow in flows + [context["rate"]]) <= 32
    sign = _sign(bounds[0][-1], bounds[1][-1], amounts, rate, allow_exact)
    with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
        discounted = [amount / (1 + rate) ** i for i, amount in enumerate(amounts)]
        npv = sum(discounted, Decimal(0))
        if sign == 0:
            npv = Decimal(0)
        if (sign > 0 and npv <= 0) or (sign < 0 and npv >= 0):
            raise ValueError("rounded NPV disagrees with its sign bounds")
        out: dict[str, Any] = {
            "npv": str(npv),
            "profitability_index_net": str(Decimal(1) if sign == 0 else sum(discounted[1:], Decimal(0)) / -amounts[0]),
        }
        if any(amount < 0 for amount in amounts[1:]):
            out["discounted_payback"] = None
            out["payback_status"] = "unavailable_for_negative_future_cash_flows"
        else:
            balance = -amounts[0]
            out["discounted_payback"] = None
            out["payback_status"] = "not_recovered_in_horizon"
            for i, present in enumerate(discounted[1:], 1):
                current = _sign(bounds[0][i], bounds[1][i], amounts[: i + 1], rate, allow_exact)
                if current >= 0 and present > 0:
                    fraction = Decimal(1) if current == 0 else min(Decimal(1), max(Decimal(0), balance / present))
                    out["discounted_payback"] = str(Decimal(i - 1) + fraction)
                    out["payback_status"] = "interpolated_within_period"
                    break
                balance -= present
    out.update(
        {
            "currency": currency,
            "period_unit": period,
            "rate_per_period": str(rate),
            "precision": precision,
            "rounding": "half_even",
            "source_status": "caller_supplied_not_verified",
            "timing": "initial at zero; subsequent flows at equal period ends",
            "payback_assumption": "linear interpolation of discounted flow within recovery period",
        }
    )
    return out, (source,)
