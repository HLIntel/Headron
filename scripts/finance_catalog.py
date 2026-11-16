"""Static instrument identifiers; no prices, trading venue or live ranking is implied."""

from __future__ import annotations

from typing import Any

# Identifiers are stable within this catalog; index symbols are conventional aliases, not feed identifiers.
_ROWS = (
    (1, "equity", "NVDA"),
    (2, "equity", "MSFT"),
    (3, "equity", "AAPL"),
    (4, "equity", "GOOGL"),
    (5, "equity", "AMZN"),
    (6, "equity", "META"),
    (7, "equity", "AVGO"),
    (8, "equity", "TSLA"),
    (9, "equity", "BRK.B"),
    (10, "equity", "JPM"),
    (11, "fx_pair", "EUR/USD"),
    (12, "fx_pair", "USD/JPY"),
    (13, "fx_pair", "GBP/USD"),
    (14, "fx_pair", "USD/CHF"),
    (15, "fx_pair", "AUD/USD"),
    (16, "fx_pair", "USD/CAD"),
    (17, "fx_pair", "NZD/USD"),
    (18, "fx_pair", "EUR/GBP"),
    (19, "fx_pair", "EUR/JPY"),
    (20, "fx_pair", "GBP/JPY"),
    (21, "index", "FTSE 100"),
    (22, "index", "DAX 40"),
    (23, "index", "CAC 40"),
    (24, "index", "Nikkei 225"),
    (25, "index", "CSI 300"),
    (26, "index", "Hang Seng"),
    (27, "index", "NIFTY 50"),
    (28, "index", "KOSPI"),
    (29, "index", "S&P/ASX 200"),
    (30, "index", "Ibovespa"),
    (31, "benchmark", "S&P 500"),
    (32, "benchmark", "Nasdaq-100"),
    (33, "benchmark", "EURO STOXX 50"),
    (34, "benchmark", "DXY"),
    (35, "benchmark", "US 10Y Treasury yield"),
    (36, "benchmark", "Brent crude"),
    (37, "benchmark", "XAU/USD"),
    (38, "benchmark", "BTC/USD"),
)


def catalog(context: dict[str, Any]) -> dict[str, Any]:
    rows = [{"id": i, "symbol": symbol, "kind": kind} for i, kind, symbol in _ROWS]
    query = context.get("query")
    if query is not None:
        if not isinstance(query, (str, int)) or isinstance(query, bool) or not str(query).strip():
            raise ValueError("query must be an identifier, symbol or kind")
        term = str(query).strip().casefold()
        rows = [row for row in rows if term in (str(row["id"]), row["symbol"].casefold(), row["kind"])]
        if not rows:
            raise ValueError("instrument not found")
    return {
        "instruments": rows,
        "status": "static_reference_not_market_data",
        "symbol_scope": "aliases require venue and provider confirmation",
    }
