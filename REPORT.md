# Assignment 1 report

**Author:** Yuanpeng Chen

**NetID:** yc8027

**Repository:** https://github.com/victor4628/FRE7871-NLP

The completed six-page report is
[assignment1_report.pdf](output/pdf/assignment1_report.pdf). It contains all six
required tables, Figure 1, and numbered answers to Q1-Q6 from the September 7
instructor update.

The revised sample follows the exact instructor filters and contains 1,536
filings from 91 issuers. It applies the $3 day -1 price threshold, 60-day history
requirements, [-60,-6] pre-filing window, [+4,+63] post-filing window, and the
full required control and fixed-effect set. Table 5 compares the same sample
without and with prior volatility. Table 6 reports the controlled return test
and its minimum detectable effects.

The executed [assignment1.ipynb](assignment1.ipynb) preserves the calculations.
[METHODOLOGY.md](METHODOLOGY.md) defines the specification,
[ANALYSIS_CHOICES.md](ANALYSIS_CHOICES.md) lists the few remaining choices, and
[AI_USE.md](AI_USE.md) discloses assistance.

Regenerate the PDF with:

```powershell
& .venv/Scripts/python.exe scripts/08_build_report.py --author "Yuanpeng Chen" --netid yc8027
```
