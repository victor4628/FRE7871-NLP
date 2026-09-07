# Additional analysis choices

The current report follows the ARK / 2021-2025 assignment. The brief explicitly
requires the six tables, quarterly figure with VIX, separate report types,
aggregate and within-company trends, Newey-West errors for aggregate trends, and
volatility regressions with and without a prior-volatility control.

The principal additional choices appearing in the report are:

| Location | Additional specification or analysis |
|---|---|
| Table 1 | Exclude explicitly identified shell-company reports and require at least 2,000 words. Count duplicate company reports once, using GOOGL for Alphabet. No minimum share-price threshold applies. |
| Table 2 and accompanying discussion | Report dictionary overlap and correlations between the two language measures. |
| Tables 5 and 6 | Include company size and compare four models: no controls, size only, prior volatility only, and both. Use the same sample in each comparison. |
| Tables 4-6 | Apply Holm adjustments to the specified groups of tests. Use company-clustered inference for repeated filings; the exact clustering and correction settings are methodological choices. |
| Table 5 and notebook | Check separate report types, added company/time/report-type effects, two-way clustering, an ARKK benchmark, and an active-only Negative word list. |
| Table 6 discussion | Calculate an approximate 80%-power minimum detectable return effect. The assignment calls for discussing precision but does not prescribe this calculation. |
| Supplementary figure | Plot median four-day excess returns across negative-word-proportion quintiles. This is separate from the required quarterly Figure 1. |

Other necessary implementation choices include the exact 63-trading-day
volatility windows, the [0,3] return window, the SEC acceptance-time event rule,
SPY excess returns, natural-log transformations, share-count valuation and split
alignment, four Newey-West lags, text parsing, sample-specific IDF and score
standardization. Some follow the paper or starter code; their exact settings
are not individually specified in the brief. See METHODOLOGY.md for definitions.

The primary outcome models do not include prior cumulative return, turnover,
industry effects or other hidden controls. Company/time/report-type effects
appear only in a separately labeled supplementary outcome specification.
Seasonal and company effects remain in the required trend analysis.

The report's appendix summarizes these choices. AI assistance and the development
history are documented separately in AI_USE.md.
