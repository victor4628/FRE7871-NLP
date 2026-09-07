# Assignment 1 report

**Author:** Yuanpeng Chen
**NetID:** yc8027
**Repository:** https://github.com/victor4628/FRE7871-NLP

The completed six-page English report is
[assignment1_report.pdf](output/pdf/assignment1_report.pdf). It contains the
sample waterfall, parsing and timing decisions, equation (1), six tables,
Figure 1, inference and robustness checks, test-specific conclusions, and
limitations of the frozen holdings sample. See [assignment1.ipynb](assignment1.ipynb)
for the executed analysis and [AI_USE.md](AI_USE.md) for authorship disclosure.

The text sample contains 1,624 unique reports from 91 issuers. Annual-report
negative language increases under both weighting schemes. Controlling for
existing volatility reduces the pooled uncertainty coefficients by 48.0% and
56.3%; issuer fixed effects remove that positive association. Negative-language
coefficients in the four-day excess-return regressions are negative but
imprecise. These findings do not establish an out-of-sample forecasting strategy.

The updated results retain low-priced stocks, as requested by the student. The
share and shell-status parser also recognizes ordinary-share wording and legacy
checkboxes. The return and volatility samples contain 1,592 and 1,591 filings.

Regenerate the PDF from the computed tables using:

```powershell
& .venv/Scripts/python.exe scripts/08_build_report.py --author "Yuanpeng Chen" --netid yc8027
```

The PDF is the Brightspace report deliverable. Generated data and intermediate
tables are excluded from Git; the notebook preserves the reported outputs.
