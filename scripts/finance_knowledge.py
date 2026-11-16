"""On-demand finance vocabulary; definitions are not project inputs."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

# IDs are permanent; add new IDs rather than reusing existing identifiers.
_ROWS = (
    (201, "npv", "capital", "sum cash_flow[t] / (1 + rate)^t", "Align timing, currency and risk."),
    (202, "irr", "capital", "rate r where NPV(r) = 0", "Nonconventional cash flows can have multiple roots or none."),
    (
        203,
        "profitability_index",
        "capital",
        "present value of future net flows / initial outflow",
        "Net-flow and gross-benefit conventions differ.",
    ),
    (
        204,
        "discounted_payback",
        "capital",
        "time until cumulative discounted inflows recover initial outflow",
        "A cutoff ignores later flows; interpolation needs an assumption.",
    ),
    (
        205,
        "operating_cash_flow",
        "capital",
        "(revenue - cash_costs) * (1 - tax_rate) + depreciation * tax_rate",
        "Assumes immediately usable tax shield and consistent marginal tax rate.",
    ),
    (
        206,
        "working_capital",
        "accounting",
        "current assets - current liabilities",
        "Project cash flow includes minus incremental change; recovery is an assumption.",
    ),
    (
        207,
        "after_tax_salvage",
        "capital",
        "sale proceeds - (sale proceeds - tax basis) * tax_rate",
        "Simplified single-rate model; tax treatment and use of losses can differ.",
    ),
    (
        208,
        "depreciation",
        "accounting",
        "systematic allocation of depreciable asset cost",
        "Noncash expense; tax and book depreciation can differ.",
    ),
    (
        209,
        "opportunity_cost",
        "capital",
        "benefit forgone from best alternative use",
        "Include incremental opportunity costs; exclude sunk costs.",
    ),
    (
        210,
        "free_cash_flow",
        "accounting",
        "operating cash flow - capital expenditures",
        "A common measure; distinguish free cash flow to equity and disclose adjustments.",
    ),
    (
        211,
        "nopat",
        "accounting",
        "EBIT * (1 - tax_rate)",
        "Simplified operating tax assumption; excludes reinvestment.",
    ),
    (
        212,
        "earnings_per_share",
        "accounting",
        "income attributable to common shareholders / weighted-average common shares",
        "Basic and diluted EPS require different adjustments.",
    ),
    (
        213,
        "return_on_equity",
        "accounting",
        "common shareholders' net income / average common equity",
        "Align periods; negative equity complicates interpretation.",
    ),
    (
        214,
        "free_cash_flow_margin",
        "accounting",
        "free cash flow / revenue",
        "Use consistent periods and define free cash flow.",
    ),
    (
        215,
        "real_rate",
        "rates",
        "(1 + nominal_rate) / (1 + inflation_rate) - 1",
        "Match periods; simple subtraction is an approximation.",
    ),
    (
        216,
        "yield_curve",
        "rates",
        "relationship between yield and maturity for comparable instruments",
        "Inversion depends on the selected maturities.",
    ),
    (
        217,
        "expectations_theory",
        "rates",
        "long rates reflect expected future short rates under model assumptions",
        "Term premiums can make forward rates differ from expected short rates.",
    ),
    (
        218,
        "liquidity_preference",
        "rates",
        "investors may require compensation for holding longer maturities",
        "Long yields are not guaranteed to exceed short yields.",
    ),
    (
        219,
        "option_moneyness",
        "options",
        "call: underlying above strike; put: underlying below strike",
        "Intrinsic value does not establish position profit.",
    ),
    (
        220,
        "option_delta",
        "options",
        "option value sensitivity to a small underlying-price change",
        "Delta changes with price, time, volatility and model assumptions.",
    ),
    (
        221,
        "exponential_moving_average",
        "markets",
        "EMA[t] = alpha * price[t] + (1 - alpha) * EMA[t-1]",
        "Specify initialization, period and price series.",
    ),
    (
        222,
        "bond_price",
        "bonds",
        "present value of coupons plus present value of principal",
        "Specify yield convention, frequency, settlement and accrued interest.",
    ),
    (
        223,
        "risk_premium",
        "rates",
        "additional required return for a specified risk",
        "Risk components are model dependent and can overlap.",
    ),
    (
        224,
        "statements",
        "accounting",
        "income statement, balance sheet, cash-flow statement",
        "Cross-check periods, accounting policies, units and disclosures.",
    ),
    (
        225,
        "federal_funds",
        "rates",
        "overnight interbank borrowing rate",
        "Policy target range and effective rate are distinct.",
    ),
    (
        226,
        "sofr",
        "rates",
        "secured overnight Treasury repo financing benchmark",
        "Not the federal funds rate or a Treasury yield.",
    ),
    (
        227,
        "libor",
        "rates",
        "legacy interbank offered benchmark",
        "Transitioned away; contract fallbacks and currencies differ.",
    ),
    (
        228,
        "retained_earnings",
        "accounting",
        "cumulative earnings less distributions and adjustments",
        "Equity accounting balance, not cash held.",
    ),
    (
        229,
        "stock_split",
        "equity",
        "shares and per-share amounts adjust with the split ratio",
        "A split alone does not create enterprise value.",
    ),
    (
        230,
        "treasury_stock",
        "equity",
        "issuer shares repurchased and held by the issuer",
        "Repurchases affect cash and share counts; EPS effects depend on circumstances.",
    ),
    (
        231,
        "dividend_yield",
        "equity",
        "annualized dividend per share / share price",
        "Payments can change; yield does not guarantee total return.",
    ),
    (
        232,
        "equity",
        "instruments",
        "ownership interest with residual economic rights",
        "Rights and seniority vary by security.",
    ),
    (
        233,
        "etf",
        "instruments",
        "fund shares traded on an exchange",
        "Holdings, fees, tracking and market price can differ.",
    ),
    (
        234,
        "adr",
        "instruments",
        "depositary receipt representing foreign shares",
        "Currency, issuer, depositary and market risks differ.",
    ),
    (
        235,
        "futures",
        "instruments",
        "standardized exchange-traded contract for future settlement",
        "Leverage and margin can magnify losses; contracts differ.",
    ),
    (
        236,
        "crypto_asset",
        "instruments",
        "digital asset using distributed or cryptographic infrastructure",
        "Price, custody, legal status and liquidity vary.",
    ),
    (
        237,
        "stablecoin",
        "digital",
        "token designed to maintain a reference value",
        "Peg, reserves, redemption, custody and issuer can fail.",
    ),
    (
        238,
        "tokenized_treasury",
        "digital",
        "token associated with Treasury exposure",
        "Inspect legal rights, underlying ownership, redemption and custody.",
    ),
    (
        239,
        "tokenized_security",
        "digital",
        "security represented using a token or ledger",
        "Tokenization alone does not determine settlement finality or remove securities obligations.",
    ),
    (
        240,
        "wallet",
        "digital",
        "software or hardware managing cryptographic credentials",
        "Control of keys is not proof of identity, ownership or legal custody.",
    ),
    (
        241,
        "opening_range_breakout",
        "patterns",
        "hypothesis: price breaks a defined opening range",
        "Specify venue, timezone, volume, costs and failed-break criteria; paper test.",
    ),
    (
        242,
        "vwap_mean_reversion",
        "patterns",
        "hypothesis: price returns toward volume-weighted average price",
        "Trends may persist; define session, anchor and deviation; paper test.",
    ),
    (
        243,
        "ema_pullback",
        "patterns",
        "hypothesis: pullback within a moving-average trend",
        "Define initialization, timeframe, confirmation and invalidation; paper test.",
    ),
    (
        244,
        "news_retest",
        "patterns",
        "hypothesis: post-release breakout level is retested",
        "Release times vary; spreads and slippage can change sharply; paper test.",
    ),
    (
        245,
        "fair_value_gap",
        "patterns",
        "hypothesis: a multi-candle price imbalance is revisited",
        "Definitions and session windows vary; validate out of sample; paper test.",
    ),
    (
        246,
        "order_block",
        "patterns",
        "hypothesis: a prior price zone acts as support or resistance",
        "Zone and confirmation definitions are subjective; paper test.",
    ),
    (
        247,
        "macro_bottleneck",
        "research",
        "constraint linking demand, capacity, inputs and potential beneficiaries",
        "Crowding requires measured ownership, positioning or valuation data.",
    ),
    (
        248,
        "cash_conversion",
        "accounting",
        "operating cash flow or defined free cash flow relative to revenue",
        "Compare periods and working-capital effects; definitions vary.",
    ),
    (
        249,
        "filings",
        "research",
        "issuer disclosures including annual, quarterly and current reports",
        "Check issuer, reporting period, amendments and accounting notes.",
    ),
)


def lookup(context: dict[str, Any]) -> dict[str, Any]:
    query = context.get("query")
    if query is not None and (not isinstance(query, (str, int)) or isinstance(query, bool) or not str(query).strip()):
        raise ValueError("query must be a concept identifier, label or tag")
    term = str(query).strip().casefold() if query is not None else None
    rows = [
        {"id": ident, "label": label, "tag": tag, "equation": equation, "context": note}
        for ident, label, tag, equation, note in _ROWS
        if term is None or term in (str(ident), label, tag)
    ]
    if not rows:
        raise ValueError("concept not found")
    return {"concepts": rows, "status": "reference_not_a_calculation"}


_SOURCES = (
    (301, "filings", "https://www.sec.gov/search-filings"),
    (302, "rates", "https://www.newyorkfed.org/markets/reference-rates"),
    (303, "treasury", "https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics"),
    (304, "policy", "https://www.federalreserve.gov/economy-at-a-glance-policy-rate.htm"),
    (305, "economics", "https://fred.stlouisfed.org/"),
    (306, "inflation", "https://www.bls.gov/cpi/"),
    (307, "economics", "https://www.bea.gov/data"),
    (308, "global", "https://www.imf.org/en/Data"),
    (309, "sectors", "https://finance.yahoo.com/sectors/"),
    (310, "markets", "https://www.google.com/finance/markets/"),
    (
        311,
        "digital",
        "https://www.investor.gov/introduction-investing/investing-basics/investment-products/tokenized-securities",
    ),
    (312, "rates", "https://www.newyorkfed.org/rruc/libor-transition-background"),
)


def sources(context: dict[str, Any]) -> dict[str, Any]:
    query = context.get("query")
    if query is not None and (not isinstance(query, (str, int)) or isinstance(query, bool) or not str(query).strip()):
        raise ValueError("query must be a source identifier or topic")
    term = str(query).strip().casefold() if query is not None else None
    rows = [
        {"id": i, "topic": topic, "url": url} for i, topic, url in _SOURCES if term is None or term in (str(i), topic)
    ]
    if not rows:
        raise ValueError("source not found")
    return {"sources": rows, "status": "links_only_not_retrieved"}


def visual(context: dict[str, Any]) -> dict[str, Any]:
    import re  # noqa: PLC0415

    raw = context.get("values")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 120:
        raise ValueError("values must be a nonempty list with at most 120 decimal strings")
    if any(
        not isinstance(x, str) or len(x) > 40 or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", x) for x in raw
    ):
        raise ValueError("values must be bounded plain decimal strings")
    values = [Decimal(x) for x in raw]
    low, high = min(values), max(values)
    scale = " .:-=+*#%@"
    marks = "".join(scale[int((x - low) * 9 / (high - low))] if high != low else "=" for x in values)
    return {"chart": marks, "min": str(low), "max": str(high), "status": "caller_values_not_verified"}
