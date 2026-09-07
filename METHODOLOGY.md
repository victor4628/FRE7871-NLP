# Analysis specification

See [ANALYSIS_CHOICES.md](ANALYSIS_CHOICES.md) for a requirement-by-requirement
summary of implementation decisions and additional analyses.

This retrospective filing event study compares four outcome specifications:
no controls, size only, prior volatility only, and both. The sample imposes no
minimum share-price threshold. The estimates describe within-sample associations,
not out-of-sample trading performance.

## Sample and text

Use the instructor's frozen ARK holdings and filings dated 2021-2025. Resolve
issuers by CIK. For Alphabet retain GOOGL consistently, and remove the duplicate
GOOG records; this fixed convention does not select a class on its later return.
Keep unique, parseable 10-K/10-Q filings with at least 2,000 tokens and a valid
acceptance timestamp. Do not require future survival or a balanced panel.
Exclude reports explicitly identifying the issuer as a shell company at the
filing date (including pre-merger SPAC reports); retain and flag unknown shell
status rather than guessing. This avoids assigning a later operating company's
language score to its earlier shell. Record the exact loss in Table 1.

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

The two outcome controls are log pre-filing annual volatility and log issuer
market-value proxy. Size accounts for company scale, which may relate to both
language and market outcomes; it is a research choice rather than an explicitly
required variable. Prior return and turnover are not calculated or included.
Recover common shares from the
same filing's cover-page XBRL, summing common classes only when no consolidated
total exists. Otherwise accept a dated, same-accession, instantaneous common-share
fact. Do not use weighted-average EPS shares for the primary analysis. Do not
fill from future reports. Market value uses the selected security's nominal price
at day -1 times contemporaneous issuer common shares; using one class's price is
a disclosed approximation for multi-class issuers. Undo Yahoo's subsequent split
adjustments with its split history; adjust shares for splits between their as-of
date and the pricing date. Retain low-priced stocks: there is no minimum-price
cutoff. Positive observed size and volatility are needed for logarithms.
No winsorization is applied in the main models.

## Exhibits and inference

Tables 2-3 and Figure 1 use the full text sample. Average multiple same-company,
same-form filings within each filing quarter, then equally weight companies.
Figure 1 has separate 10-K/10-Q lines for both categories and both weighting
schemes, with quarterly mean VIX on a second axis.

Table 4 reports each category/weight/form separately. Standardize the dependent
language score measure within form. The aggregate regression includes time (quarters since
2021Q1) and quarter-of-year effects; show OLS and Bartlett Newey-West t statistics,
with four lags and finite-sample correction. The main trend inference is the
company-quarter panel with company and quarter-of-year effects, firm-clustered
standard errors and cluster-count t degrees of freedom. Report both and do not
interpret the aggregate trend as causal.

Table 5 regresses log post-filing volatility on standardized Uncertainty.
Table 6 regresses four-day excess return on standardized Negative. For each
weighting scheme and outcome, show four models: language score plus intercept only; add
log size; add log prior volatility instead; add both. The primary four models
contain no other regressors or fixed effects. Clustered standard errors affect
inference, not which explanatory variables enter the regression.

Use an identical complete-case sample, score standardization and IDF corpus for
all four models within each outcome, even when a model omits an available control.
Thus the baseline model also requires 63 preceding returns for comparability,
although its equation does not need them. Preceding returns calculate prior
volatility; four-day event returns and the 63-day post-event volatility window
are separate outcomes. These are within-sample conditional associations.
Firm-clustered errors are primary. Report coefficient, SE, t, p, CI, observations
and cluster counts. For return-test power, report the approximate 80%-power
minimum detectable effect (t critical + 0.842) * clustered SE per one-SD language score.
This is a design precision diagnostic, not observed/post-hoc power.

Sensitivities use the model with both controls: 10-K/10-Q-specific models;
add issuer, calendar-quarter and form effects; two-way firm/calendar-quarter clustering (20 time
clusters is a limitation); ARKK excess-return benchmark; active-only Negative
list. All estimated specifications are retained in output tables. Holm-adjust
the four primary within-firm trend p values (two categories x two forms) within
each weighting scheme, and the four pooled outcome p values with both controls as a
separate family. Do not select a model based on significance.

## Data attrition

Keep text-only filings in descriptive/trend work even when market controls are
missing. Volatility and return regressions have separate sequential sample
waterfalls. Re-estimate IDF for each. Record every exclusion and the difference
between security records, distinct issuers and unique filings. The fixed 2026
holdings selection has survivorship/selection bias; historical share counts and
correct event dates do not remove it.
