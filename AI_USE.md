# AI use disclosure

**Tool used:** OpenAI Codex.

**Scope of assistance:** Codex read and compared the assignment brief and reference
paper, imported the instructor's repository, configured the environment, ran the
downloads, and generated the added analysis code, numerical tests, executed
notebook, methodology and running instructions, and English report. It assisted
with sample rules, equation (1), event timing, control construction, regressions,
interpretation, and PDF layout verification. The instructor supplied the original
acquisition scripts and modules; those are not original student or AI work.
Additions include scripts 04-08 and src/analysis_data.py and src/analysis_models.py.

**Student contribution and authorship:** The student supplied the current brief,
reference material and SEC contact identity, authorized the work, and discussed
data access, the sample and methodological choices. The additional implementation
and report prose were generated with Codex assistance. This disclosure does not
claim that the student independently wrote that code or independently verified
every numerical result. Subsequent independent revisions should be described
accurately rather than attributed retroactively.

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

**Verification performed by Codex:** The acquisition audit, nine numerical and
timing tests, and the complete notebook were run locally. All six report pages
were rendered and visually inspected. Report values are read from computed
tables. All estimated sensitivities are retained, including insignificant
results and the disappearance of the pooled uncertainty association with issuer
fixed effects. This is a retrospective analysis; its full-corpus scores and
2026-selected universe do not support an out-of-sample trading claim.
