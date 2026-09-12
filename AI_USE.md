# AI use disclosure

**Tool used:** OpenAI Codex.

The September 8 unit revision keeps both proportional and TF-IDF measures in the
main tables. It rescales outcome coefficients and standard errors from the
internally standardized regressors to effects per 1 percentage-point increase
in the language proportion or per 1 TF-IDF unit. This changes presentation only; fitted values, t-statistics
and p-values are unchanged.

The September 8 revision reorganizes the report into the instructor's ten sections,
enlarges the black body text, explains all variables and continuous score scaling,
and replaces an unsupported boilerplate interpretation with a reproducible PayPal
sentence comparison. Codex checked the raw visible text and added the case's
four-day excess return and pre/post volatility. The model specification and
estimated results are unchanged in this revision.

The final editorial review converted conversational change-history language in
the report and notebook into formal descriptions of the implemented methods.
Development history remains in this disclosure. Codex verified the increase in
the uncertainty coefficient after adding size using the omitted-variable
coefficient identity on the common sample; this explanation does not change the
regression specification or results.

On September 7 the TA updated the instructor repository with the exact Q1-Q6,
sample filters, event windows, controls and TF-IDF self-check. Codex fetched that
revision, revised the analysis to match it, reran all results, and rewrote the
notebook and six-page report around the numbered questions.

**Scope of assistance:** Codex read and compared the assignment brief and reference
paper, imported the instructor's repository, configured the environment, ran the
downloads, and generated the added analysis code, numerical tests, executed
notebook, methodology and running instructions, and English report. It assisted
with sample rules, equation (1), event timing, control construction, regressions,
interpretation, and PDF layout verification. The instructor supplied the original
acquisition scripts and modules; those are not original student or AI work.
Additions include the analysis and report scripts, including scripts 04-08 and 10,
and src/analysis_data.py and src/analysis_models.py.

**Student contribution and authorship:** The student supplied the current brief,
reference material and SEC contact identity, authorized the work, and discussed
data access, the sample and methodological choices. The additional implementation
and report prose were generated with Codex assistance. This disclosure does not
claim that the student independently wrote that code or independently verified
every numerical result. Subsequent independent revisions should be described
accurately rather than attributed retroactively.

An exploratory revision temporarily omitted the $3 minimum-price screen and
recomputed the samples, regressions, notebook and report. This was a post-results
sample change rather than a rule fixed before the analysis; the supplementary
quintile chart was likewise developed after the initial results.

A subsequent exploratory design used four models for each outcome and weighting
scheme: no controls, size only, prior volatility only, and both. Codex implemented
those on common samples, temporarily removed the prior-return and turnover controls
and primary fixed effects, and kept an issuer/time-effects specification as a
separate sensitivity.

The September 7 TA update superseded those exploratory specifications. The current
submission applies the required $3 cutoff, form-specific word
thresholds, earliest company-quarter filing rule, 60-day history rule,
[-60,-6]/[+4,+63] volatility windows, and the full required controls and fixed
effects. The older four-model design and shell-company exclusion are not used in
the current results.

A later presentation review clarified reader-facing score and statistical labels,
added a table guide and disclosure appendix, and produced ANALYSIS_CHOICES.md to
distinguish requirements, implementation choices, extra checks and withdrawn
methods. This documentation revision does not change model estimates.

**Errors and issues corrected during AI-assisted work:** The initial plan used
the superseded S&P 500 / 2018-2022 assignment and was replaced by the current ARK
/ 2021-2025 brief. Security records were initially confused with distinct issuers
and reports: GOOG and GOOGL duplicate 20 Alphabet reports. The starter parser
removed visible inline-XBRL text, which the analysis parser now preserves.
Weighted-average EPS shares were unsuitable for the primary size control; shares
were recovered from the same filing's cover or instantaneous facts instead.
Cover-text extraction needed corrections for common-class descriptions that omit
the word "shares" and text with a split word "common". The analysis also handles
retired negative-dictionary entries, Yahoo split-adjustment units, early exchange
closes, and redundant fixed-effect columns explicitly.

A later review found that the parser missed dated "ordinary shares" on a
predecessor filing's cover and legacy shell checkboxes using x and an empty-box
font character. Both were corrected and cached cover metadata was refreshed.
Codex also corrected an explanatory counting error: BMNR accounts for 16 missing
pre-history filings, not the 17 previously stated in conversation.

**Verification performed by Codex:** The acquisition audit, eleven numerical and
timing tests, and the complete notebook were run locally. All report pages
were rendered and visually inspected. Report values are read from computed
tables. The current pipeline retains the required form-specific volatility models
and an ARKK benchmark check, including insignificant results. This is a
retrospective analysis; its full-corpus scores and
2026-selected universe do not support an out-of-sample trading claim.
