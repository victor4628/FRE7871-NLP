# Analysis specification

This file records the implementation behind the six required exhibits. The
submitted PDF gives the shorter interpretation and answers Q1-Q6.

## Sample and text

Start from the instructor's frozen 124-security ARK snapshot and EDGAR 10-K and
10-Q filings dated 2021-2025. Resolve issuers by CIK and count an issuer filing
once; retain GOOGL for duplicate Alphabet records. Apply the updated filters in
order:

1. parsed, non-amended 10-K/10-Q;
2. at least 2,000 words for a 10-K or 1,000 for a 10-Q;
3. earliest filing per issuer and calendar quarter;
4. usable day 0 and day -1 nominal share price of at least $3;
5. at least 60 daily stock returns before and after day 0; and
6. complete filing-date share count, required controls and outcomes.

Visible inline-XBRL text is retained. Hidden resources, scripts and styles are
removed, as are tables whose digits exceed 15% of non-space characters. Use the
starter uppercase tokenizer without stemming or stopword removal. The updated
assignment does not call for a shell-company exclusion, so none is applied.

Use the 2,355-word LM Negative list and 297-word Uncertainty list. A proportional
score is list-word occurrences divided by all tokens. Equation (1) is

`w_ij = [(1 + ln(tf_ij)) / (1 + ln(a_j))] ln(N / df_i)` for `tf_ij > 0`,

and zero otherwise, with `a_j` equal to total tokens divided by distinct tokens.
Category TF-IDF is the sum of its term weights. IDF is recomputed on the exact
corpus for every pooled or form-specific model. The repository self-check gives
0.8480, 0.2885 and 0.5026 for the three instructor examples.

## Timing and market variables

Convert the SEC acceptance timestamp from UTC to Eastern. Day 0 is the first
exchange session on or after the later of the filing date and the acceptance
date shifted forward one calendar day when acceptance occurs at or after 16:00
Eastern.

The event return is the stock buy-and-hold return over [0,+3] minus the SPY
buy-and-hold return, measured from the day -1 close and reported in percentage
points. Pre-filing variables use [-60,-6]. Prior excess return subtracts SPY;
prior volatility is the annualized sample standard deviation of daily stock
returns; dollar volume is mean daily nominal price times volume. Subsequent
volatility uses [+4,+63]. Returns are never filled.

Log size is day -1 nominal price times the common-share count printed on the
same filing. Consolidated common shares are preferred; otherwise common classes
are summed. Weighted-average EPS shares and later filings are not used. Yahoo
split history aligns historical price and share units.

## Models and inference

Figure 1 first averages within issuer, form and filing quarter, then weights
issuers equally. Table 4 is run separately for 10-K and 10-Q and for both
weighting schemes. Aggregate trends include quarter-of-year effects and report
ordinary and four-lag Newey-West t-statistics. Preferred trends add issuer
effects and use issuer-clustered standard errors. Proportional slopes are
percentage points per year; TF-IDF slopes are term-weight units per year.

Table 5 regresses log subsequent volatility on standardized Uncertainty. Both
columns include log size, log average dollar volume, prior SPY excess return, a
10-K indicator, issuer effects and calendar-quarter effects; the second adds log
prior volatility. Table 5 is also run separately by form. Table 6 regresses the
four-day excess return on standardized Negative with the full control and fixed
effect set. Outcome standard errors cluster by issuer. The ARKK return benchmark
is the only additional outcome specification.

The return table reports an approximate 80%-power minimum detectable effect as
`(cluster-t critical + 0.842) × clustered SE`. This is a precision diagnostic,
not observed power. All estimates are retrospective associations.
