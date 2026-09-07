# Assignment requirements and additional analysis choices

The authority for what is required is the one-page Fall 2026 assignment brief,
`FRE-GY-7871A_Assignment_1.pdf`. This statement separates its explicit requirements
from implementation decisions and additional work. Some implementation decisions
follow the reference paper or instructor starter code; they are not presented as
new requirements imposed by the brief. Code and report were produced with Codex
assistance, as disclosed in `AI_USE.md`.

## Explicitly required by the current assignment

- Use the six ARK funds' 124-security starting universe and 2021-2025 filings;
  make an actual EDGAR download attempt and report exclusions.
- Keep financial negative language and uncertainty separate; use the two LM lists
  (2,355 and 297 words), word proportions, and equation (1) TF-IDF weights.
- Produce Tables 1-6 and Figure 1: sample counts, form-specific descriptive
  statistics, top 30 words and their shares of each list, quarterly scores and VIX,
  aggregate and within-company trends, volatility and return regressions.
- Separate annual and quarterly reports when analyzing trends; address company
  composition, use Newey-West errors for the aggregate trend test, and lead with
  the within-company test.
- Compare post-filing volatility with and without a prior-volatility control;
  analyze the four-day filing-period return with controls. Explain evidence and
  statistical precision separately for the different tests.
- Deliver code, an executed notebook, AI_USE.md and a viewable GitHub link, plus
  a short PDF report. Do not upload downloaded data.

## Implementation decisions not specified exactly in the brief

1. **Company identity and sample filters.** Match SEC company identifiers (CIKs),
   remove duplicate company reports, and retain GOOGL rather than GOOG for
   Alphabet's return series. Require a usable SEC acceptance timestamp and at
   least 2,000 extracted words; neither screen removes a report in the current
   sample. Exclude reports explicitly marked as shell-company reports: 58 are
   removed. Unknown shell status is retained and flagged, although none remain
   after the parser corrections. Do not require a balanced panel or future
   survival; keep text-eligible reports when market data are incomplete.

2. **Text processing.** Use primary filing documents rather than separate
   exhibits; preserve visible inline-XBRL text; remove hidden resources, scripts,
   styles and tables with more than 15% digits among non-space characters. Retain
   the starter's uppercase tokenizer, minimum two-character tokens and internal
   apostrophes/hyphens, without stemming or stopword removal. Record old/new word
   counts. Correct legacy checkboxes and ordinary-share cover wording.

3. **Scoring implementation.** Retain the instructor's nonzero category flags,
   including ten retired Negative entries, to match the specified list size.
   Implement equation (1) using natural logs, zero weight for absent words,
   average term frequency equal to total/distinct tokens, and sums of category
   weights. These implement the required paper method, rather than an extra
   scoring method. The document corpus used to estimate IDF is the exact sample
   of each regression or restricted check. The four control comparisons share
   one corpus and one score standardization. Full-sample IDF is retrospective,
   not an out-of-sample forecast. Standardize scores to one standard deviation
   for regression comparisons; show proportions as percentages in tables.

4. **Event timing and returns.** Use SEC acceptance time as a disclosure-time
   proxy. Day 0 is the first New York exchange session closing strictly after
   acceptance, including early closes: pre-open/intraday submissions use that
   day; at-close/after-close/holiday/weekend submissions move forward. This timing
   treatment was also explicitly discussed with the student. Use daily adjusted
   prices from the starter's Yahoo source, compound stock returns over days
   [0,3], and subtract compounded SPY returns. Daily returns include some
   pre-release movement for intraday submissions; this is not a tradable strategy.

5. **Volatility and complete observations.** Interpret a quarter as 63 trading
   days. Prior volatility uses [-63,-1]; subsequent volatility uses [4,66], after
   the four-day return window. Compute sample daily-return standard deviation
   (divisor n-1), annualize by sqrt(252), and use its natural logarithm in models.
   Require all relevant returns and positive volatility; do not fill missing
   prices or returns. These exact windows, annualization and log choices are not
   given in the brief. Stock/SPY/ARKK event returns must be available for the
   common return sample. ARKK is an extra comparison, and requiring it does not
   remove additional reports in this run.

6. **Company size and model comparison - student requested.** Size is log market
   value: the preceding closing price times dated shares outstanding. It accounts
   for company scale potentially related to language and market outcomes; the
   brief does not specifically name size. Recover shares from the same filing's
   cover or same-accession instantaneous facts, using dates no more than 120 days
   before filing. Sum share classes only when no consolidated total exists;
   approximate their value using the selected class's price. Avoid EPS weighted
   average shares and future reports. Reverse Yahoo's later split normalization
   and align shares to the pricing date. Compare no controls, size only, prior
   volatility only, and both, with an intercept in all models and no other primary
   regressors or fixed effects. Hold the sample constant even for models omitting
   a control. Thus 63 preceding returns are required for comparison consistency,
   although the no-control and size-only equations do not themselves need them.

7. **Quarterly aggregation and trend implementation.** Group by filing quarter,
   not fiscal reporting quarter. Average within company/form/quarter, then weight
   companies equally; use quarterly mean VIX. Estimate separate linear trends for
   each category, weight and form, with quarter-of-year effects. The within-company
   test uses company effects and at least two observed quarters per company.
   Standardize the outcome within its form-specific sample. Use four Newey-West
   lags, Bartlett weights and finite-sample corrections. Newey-West itself and
   within-company analysis are required; these exact settings are our choices.

8. **Statistical reporting.** Use ordinary least squares with company-clustered
   standard errors and cluster-based t inference, rather than treating repeated
   reports as independent. Print standard errors, p-values and sample counts;
   save confidence intervals, t statistics, adjusted R-squared and all coefficients
   in the notebook outputs. Remove algebraically redundant fixed-effect columns
   without dropping the score/time coefficient.

## Additional analyses and checks, not expressly required

- **Holm multiple-testing adjustment.** Adjust four within-company category/form
  trend tests separately for each weighting scheme. Separately adjust the four
  pooled tests with both controls: two uncertainty weights for volatility and two
  negative-language weights for returns. Other control columns have unadjusted
  p-values; an unreported adjusted value is not evidence of insignificance.
- **Robustness checks using both controls.** Separate annual/quarterly outcome
  regressions; add company, calendar-quarter and report-type effects; cluster by
  company and calendar quarter; use ARKK instead of SPY; exclude retired Negative
  words. Re-estimate IDF for each restricted sample. Keep all estimated checks,
  including insignificant results, and disclose negative nuisance variances in
  two-way covariance estimates and the small number of time clusters.
- **Numerical precision calculation.** Approximate an 80%-power minimum detectable
  return effect with (cluster-t critical value + 0.842) times its standard error.
  The brief requires a discussion of precision, but not this particular formula.
- **Further descriptive checks.** Calculate list overlap and score correlations,
  old/new parser token totals, cover-share source counts, shifted event dates,
  five-year company coverage, and top-30 cumulative word shares. Discuss the
  supplied 2026 snapshot's selection bias. The historical-holdings extension and
  held-out forecasting evaluation are proposals only, not completed analyses.
- **Student-requested supplementary chart.** Group the return sample into pooled
  negative-word-proportion quintiles and plot median four-day excess returns;
  save group counts, ranges and mean returns too. This is descriptive and has no
  regression controls. It is supplementary, not the required Figure 1.
- **Reproduction and quality checks.** Added the acquisition audit, supplementary
  split-history download, cover recovery, cached text matrix, regression scripts,
  notebook/report builders, ten numerical/timing tests, sample/corpus and regressor
  checks, locked dependencies, Chinese running instructions and PDF page review.
  The instructor's frozen holdings file is retained as starter provenance; other
  downloaded data stay excluded from Git. These support the required deliverables.

## Earlier choices withdrawn - not used in the current results

- The optional $3 stock-price screen was removed at the student's request. All
  80 filings previously excluded only by that screen are retained. No price
  threshold or winsorization is used.
- Prior cumulative return and average turnover were initially added as controls;
  their calculations and regression use have been removed. The original download
  still contains volume, but average turnover is not part of the current analysis.
- Industry, report-type and calendar-quarter effects were removed from the four
  primary outcome models. Company/time/report-type effects remain only in the
  explicitly labeled extra check. Seasonal/company effects in Table 4 remain
  part of implementing the required trend analysis.
- The older S&P 500 / 2018-2022 / WRDS plan was superseded. Current results follow
  the ARK / 2021-2025 brief and do not use WRDS data.

The four-model design and removal of the price cutoff were requested after the
initial results. They are disclosed as later amendments, not falsely presented
as a preregistered design. No additional hypothesis tests are claimed solely from
the supplementary chart.
