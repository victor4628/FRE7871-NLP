# Analysis specification

The initial specification was set before inspecting regression estimates. At the
student's subsequent request, the $3 minimum-price screen was removed and all
results were recomputed. This amendment was not selected for significance.
This is a retrospective filing event study, not an out-of-sample trading backtest.

## Sample and text

Use the instructor's frozen ARK holdings and filings dated 2021-2025. Resolve
issuers by CIK. For Alphabet retain GOOGL consistently, and remove the duplicate
GOOG records; this fixed convention does not select a class on its later return.
Keep unique, parseable 10-K/10-Q filings with at least 2,000 tokens and a valid
acceptance timestamp. Do not require future survival or a balanced panel.
Exclude reports explicitly identifying the issuer as a shell company at the
filing date (including pre-merger SPAC reports); retain and flag unknown shell
status rather than guessing. This avoids assigning a later operating company's
tone to its earlier shell. Record the exact loss in Table 1.

Preserve visible inline-XBRL text, remove hidden headers/resources, scripts and
styles, and remove tables when digits exceed 15% of non-space characters. The
starter parser deletes visible inline-XBRL containers too; the analysis parser
unwraps them instead. Primary documents are used, not separately filed exhibits.
Use the starter tokenizer (uppercase, minimum two characters, retaining internal
apostrophes/hyphens). Save both old and new word counts for a parsing audit.

Use the assignment's nonzero-flag lists: 2,355 Negative and 297 Uncertainty words.
Disclose the ten removed Negative entries; excluding them is a declared sensitivity.
For each corpus, compute proportions as category occurrences / all tokens and
equation (1) weights with a_j = total tokens / distinct tokens. Sum weights over
each category, using natural logs. A zero-frequency word contributes zero. IDF is
estimated on the exact filings in each regression specification, including each
form-specific or other restricted sensitivity sample; comparison pairs use the
same sample. Do not stem or remove stopwords.

## Markets and timing

Day 0 is the first XNYS session whose close is strictly later than the SEC UTC
acceptance timestamp. Thus pre-open/intraday filings use the same day; at-close,
after-close, weekend and holiday filings move forward. Use the actual calendar,
including early closes. Daily close-to-close data do not isolate an intraday
reaction perfectly; no tradability claim is made for an intraday filing.

Four-day excess return is stock buy-and-hold return over [0,3] minus SPY's
buy-and-hold return, in percentage points. ARKK is the benchmark sensitivity.
Volatility is the sample SD of daily stock returns times sqrt(252): pre-filing
[-63,-1], post-filing [4,66] (63 trading sessions after the filing return window).
Require all daily returns in the relevant window. Returns are never forward-filled.

Controls are pre-filing buy-and-hold return, log pre-filing annual volatility,
log issuer market-value proxy and log turnover. Recover common shares from the
same filing's cover-page XBRL, summing common classes only when no consolidated
total exists. Otherwise accept a dated, same-accession, instantaneous common-share
fact. Do not use weighted-average EPS shares for the primary analysis. Do not
fill from future reports. Market value uses the selected security's nominal price
at day -1 times contemporaneous issuer common shares; using one class's price is
a disclosed approximation for multi-class issuers. Undo Yahoo's subsequent split
adjustments with its split history; adjust shares for splits between their as-of
date and the pricing date. Turnover averages daily volume / contemporaneous shares
over [-63,-1], with split units aligned. Retain low-priced stocks: there is no
minimum-price cutoff. Positive, observed size/turnover remain necessary to take
their logarithms. No winsorization is applied in the main models.

## Exhibits and inference

Tables 2-3 and Figure 1 use the full text sample. Average multiple same-company,
same-form filings within each filing quarter, then equally weight companies.
Figure 1 has separate 10-K/10-Q lines for both categories and both weighting
schemes, with quarterly mean VIX on a second axis.

Table 4 reports each category/weight/form separately. Standardize the dependent
tone measure within form. The aggregate regression includes time (quarters since
2021Q1) and quarter-of-year effects; show OLS and Bartlett Newey-West t statistics,
with four lags and finite-sample correction. The main trend inference is the
company-quarter panel with company and quarter-of-year effects, firm-clustered
standard errors and cluster-count t degrees of freedom. Report both and do not
interpret the aggregate trend as causal.

Table 5 regresses log post-filing volatility on standardized Uncertainty, size,
turnover, pre-return, form, two-digit SIC and calendar-quarter effects. Run paired
models without and with log pre-volatility on identical complete-case samples.
Table 6 regresses four-day excess return on standardized Negative with the same
controls plus log pre-volatility. These are within-sample conditional associations.
Firm-clustered errors are primary. Report coefficient, SE, t, p, CI, observations
and cluster counts. For return-test power, report the approximate 80%-power
minimum detectable effect (t critical + 0.842) * clustered SE per one-SD tone.
This is a design precision diagnostic, not observed/post-hoc power.

Declared sensitivities: 10-K/10-Q-specific volatility/return models; firm effects
instead of industry effects; two-way firm/calendar-quarter clustering (20 time
clusters is a limitation); ARKK excess-return benchmark; active-only Negative
list. All estimated specifications are retained in output tables. Holm-adjust
the four primary within-firm trend p values (two categories x two forms) within
each weighting scheme, and the four controlled pooled outcome p values as a
separate family. Do not select a model based on significance.

## Data attrition

Keep text-only filings in descriptive/trend work even when market controls are
missing. Volatility and return regressions have separate sequential sample
waterfalls. Re-estimate IDF for each. Record every exclusion and the difference
between security records, distinct issuers and unique filings. The fixed 2026
holdings selection has survivorship/selection bias; historical share counts and
correct event dates do not remove it.
