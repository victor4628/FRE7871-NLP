# Assignment 1 report

**Author:** Victor Chen

**NetID:** yc8027

**Repository:** https://github.com/victor4628/FRE7871-NLP

The completed six-page report is
[assignment1_report.pdf](output/pdf/assignment1_report.pdf). It contains all six
required tables, Figure 1, and numbered answers to Q1-Q6 from the September 7
instructor update.

The report now follows the instructor's sections exactly: 1. What I did;
2. Data construction; 3. Word lists; 4. Method; 5. What the measures are made of;
6. Trends, 2021-2025; 7. Uncertainty, volatility and returns; 8. 10-K versus 10-Q;
9. Limitations; 10. What I would do next. Q1/Q2 appear in section 5, Q3 in section 6,
Q4/Q6 in section 7, and Q5 in section 8, following the section placement in the
instructor template. Body text and answers use 10.5-point black type.

The PayPal text comparison and event outcomes are reproduced by
`scripts/10_report_evidence.py`, which is also executed in the notebook. Run it
before rebuilding the PDF when working directly from the cached analysis outputs.

The revised sample follows the exact instructor filters and contains 1,536
filings from 91 issuers. It applies the $3 day -1 price threshold, 60-day history
requirements, [-60,-6] pre-filing window, [+4,+63] post-filing window, and the
full required control and fixed-effect set. Table 5A compares the same full
sample without and with prior volatility; Table 5B estimates those specifications
separately for 10-K and 10-Q filings. Table 6 reports the controlled return test
and its minimum detectable effects.

The executed [assignment1.ipynb](assignment1.ipynb) preserves the calculations.
[METHODOLOGY.md](METHODOLOGY.md) defines the specification,
[ANALYSIS_CHOICES.md](ANALYSIS_CHOICES.md) lists the few remaining choices, and
[AI_USE.md](AI_USE.md) discloses assistance.

Regenerate the PDF with:

```powershell
& .venv/Scripts/python.exe scripts/08_build_report.py --author "Victor Chen" --netid yc8027
```
