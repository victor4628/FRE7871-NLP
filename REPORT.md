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
negative language increases under both weighting schemes. Tables 5 and 6 each
compare no controls, size only, prior volatility only, and both. Company size is
an optional research control, justified explicitly in the PDF. Controlling for
existing volatility reduces the pooled uncertainty coefficients; adding issuer,
calendar-quarter and form effects removes that positive association. Negative-language
coefficients in the four-day excess-return regressions are negative but
imprecise. These findings do not establish an out-of-sample forecasting strategy.

The sample retains low-priced stocks. Share counts and shell-company indicators
are extracted from the corresponding filing covers. The return and volatility
samples contain 1,592 and 1,591 filings.
The primary outcome models contain no other regressors or fixed effects. Prior
return and turnover are no longer calculated. Each four-model comparison keeps
the sample and language score standardization constant, including for the no-control model.

Regenerate the PDF from the computed tables using:

```powershell
& .venv/Scripts/python.exe scripts/08_build_report.py --author "Yuanpeng Chen" --netid yc8027
```

The PDF is the Brightspace report deliverable. Generated data and intermediate
tables are excluded from Git; the notebook preserves the reported outputs.

[ANALYSIS_CHOICES.md](ANALYSIS_CHOICES.md) records implementation choices and
additional analyses without lengthening the submitted report.
The PDF uses named language scores and explained statistical labels rather than
the generic term "tone".
