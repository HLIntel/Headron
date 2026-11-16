# Finance equations

`finance.evaluate` is a callable local microprogram for financial calculations and reference lookup. It accepts declared inputs and returns the equation, decimal result, unit, period, and caller-supplied evidence references. It does not retrieve statements, hold accounts, connect to a brokerage, or verify a source.

Discover the available formulas:

```sh
headron mind --micro finance.evaluate '{"formula":"list"}' --json
```

An agent connected to the repository's read-only MCP server can call its generic `headron` tool with the same arguments:

```json
{"argv":["mind","--micro","finance.evaluate","{\"formula\":105,\"query\":202}","--json"]}
```

The server must have the updated repository installed and permit the `mind` verb. The hosted Mind API has its own endpoint contract; this repository change does not deploy or add a finance endpoint there. A chat without a connected runtime can read this document and source records, but cannot execute these calculations by linking the repository alone.

For a reusable analysis plan, `headron process quantitative_analysis --json` lists the profile, expected artifacts and proof requirements. These are planned checks; selecting the profile does not validate inputs or sources.

The [computation handoff](COMPUTATION.md) sets out the cross-domain contract, composition and evidence work that could extend these operations.

The listing also returns stable numeric formula identifiers. Supply an identifier as the JSON `formula` value to call the same operation.

Each input declares `measure`, `value`, `unit`, `period`, and `source`. Values are plain decimal strings; the unit is a three-letter currency code. The period has inclusive `start` and `end` ISO dates. A source is a caller-supplied locator, not proof that the number or classification is correct. Arithmetic uses decimal precision and half-even rounding; the response states both.

Historical cost of debt divides interest expense by average interest-bearing debt for the same currency and period. The result is a period ratio, not an annualized or prospective borrowing rate. The caller must establish that the interest and debt definitions are comparable and that the supplied average is appropriate.

```sh
headron mind --micro finance.evaluate "$(cat input.json)" --json
```

The input file supplies `formula`, `inputs`, and the declared fields described above.

Absolute variance subtracts budget from actual. Both inputs also declare an identical `metric` such as `revenue`; a positive result is not automatically favorable. Missing, ambiguous, incompatible, or invalid inputs are refused. A matching label is a caller assertion and does not establish economic comparability.

Additional accounting, bond, transaction, and valuation formulas need their own explicit assumptions, units, independent examples, and refusal cases before inclusion. This surface does not give investment, tax, or accounting advice.

## Capital budgeting

`capital.periodic` takes `cash_flows` as decimal strings, including the initial outflow at period zero, `rate` as a decimal per period, `period_unit` as `year`, `quarter` or `month`, `currency`, and `source`. Later flows occur at equal period ends; undeclared fields and alternative timing are refused. It returns net present value, the present value of net future cash flows divided by the initial outflow, and discounted payback when future cash flows are nonnegative. Payback interpolates linearly within the recovery period; it is unavailable for negative future cash flows and reports when recovery is outside the supplied horizon.

```sh
headron mind --micro finance.evaluate '{"formula":"capital.periodic","cash_flows":["-100","60","60"],"rate":"0","currency":"USD","period_unit":"year","source":"forecast"}' --json
```

Cash flows should be incremental and consistently after tax when the discount rate requires it. Opportunity costs, effects on other business lines, working-capital changes, and terminal proceeds may matter; sunk costs do not change with the decision. Depreciation is noncash, but its tax effect depends on the applicable tax rules and the ability to use the deduction. A working-capital increase generally uses cash, and recovery depends on the project assumptions. Financing cash flows must be consistent with the valuation approach to avoid double counting. The engine does not infer any of these values.

Discounting and division can round. The returned precision scales with input length. Outward-rounded bounds must establish the NPV sign; a result whose sign remains uncertain is refused. The calculation remains sensitive to the supplied assumptions and does not validate them.

IRR solves for a rate at which NPV is zero. Negative NPV at one selected rate does not make IRR meaningless; unconventional cash flows can have multiple roots or none. An IRR solver is not implemented. Project selection also depends on constraints, uncertainty and alternatives; a formula alone is not an instruction to invest. See [capital budgeting methods](https://openstax.org/books/principles-finance/pages/16-summary) and [choosing projects](https://openstax.org/books/principles-finance-2e/pages/16-5-choosing-between-projects).

## Reconciliation

`data.reconcile` compares two caller-supplied lists of records. Each record declares `key`, decimal-string `value`, `unit`, `period`, and `source`. Exact matching keys require identical units and periods; duplicate keys and incompatible records are refused. Results include differences and unmatched keys. Labels and sources are caller assertions; matching does not prove identity, source authenticity, or completeness. This operation also applies to inventory and other numerical records.

```sh
headron mind --micro data.reconcile '{"left":[{"key":"sales","value":"12.30","unit":"USD","period":"annual","source":"ledger"}],"right":[{"key":"sales","value":"10.20","unit":"USD","period":"annual","source":"statement"}]}' --json
```

## Instrument discovery

`instrument.lookup` returns the static reference universe supplied for equities, currency pairs, international indices and additional benchmarks. A caller can omit `query` for all rows, or supply the stable numeric `id`, exact symbol, or kind (`equity`, `fx_pair`, `index`, `benchmark`). These identifiers are catalog identifiers, not exchange identifiers. Symbols and names can vary by venue and data provider; the catalog contains no prices, calendars, freshness, listings or rankings. For currency pairs, the first currency is the base and the second is the quote currency; see the [SEC currency-pair explanation](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/foreign).

```sh
headron mind --micro finance.evaluate '{"formula":"instrument.lookup","query":11}' --json
```

## Vocabulary

`concept.lookup` returns short reference records with numeric identifiers, labels, topic tags, equations and assumptions. Query by identifier, exact label or topic tag; omit the query to list the concepts. These records describe concepts and do not calculate or validate project values.

```sh
headron mind --micro finance.evaluate '{"formula":105,"query":"capital"}' --json
```

The `patterns` tag describes research hypotheses, including opening ranges, moving-average pullbacks and price gaps. These are not verified signals. Define the instrument, venue, session, timezone, execution costs, position sizing and invalidation before any paper evaluation. Historical performance requires independent, out-of-sample evidence; a pattern does not guarantee a return. News releases and market sessions do not all share the same time.

For macroeconomic research, trace a proposed constraint through demand, capacity, suppliers, customers, financing and measurable cash flows. Compare valuation and available ownership or positioning data before describing a layer as crowded. Manufacturing, energy, defense, semiconductors, supply chains, tariffs, regulation, reserve currencies and digital payment infrastructure are research themes, not forecasts.

## Research paths

`source.lookup` returns public page pointers by numeric identifier or topic. It opens no connection and retrieves no data. Check access, freshness, licensing, issuer identity and definitions at the destination; provider symbols and listings can differ. Official filings and original releases are primary evidence; sector and market pages are discovery aids.

```sh
headron mind --micro finance.evaluate '{"formula":106,"query":"rates"}' --json
```

The federal funds target is distinct from the effective overnight rate, SOFR and Treasury yields. The [New York Fed](https://www.newyorkfed.org/markets/reference-rates) describes its reference rates and the [Treasury](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics) publishes yield statistics. LIBOR is a legacy reference; contract fallbacks and reference-rate choices depend on the instrument.

Digital representations can support transfers or claims, but a token does not establish custody, settlement finality, legal ownership or a stable value. Inspect rights, counterparties, redemption and operational risks; see [tokenized securities](https://www.investor.gov/introduction-investing/investing-basics/investment-products/tokenized-securities).

## Series view

`series.visual` turns caller-supplied decimal strings into an offline text chart, scaled from the smallest to the largest value. Input ordering supplies the horizontal axis; the caller must supply the dates, unit, provenance and any missing observations separately. A flat series uses a constant mark. It does not fetch or validate prices.

```sh
headron mind --micro finance.evaluate '{"formula":107,"values":["1","2","3"]}' --json
```
