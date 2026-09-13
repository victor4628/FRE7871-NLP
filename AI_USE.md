# AI use disclosure

**Tools used:** OpenAI Codex.

**What I used them for:** I used Codex to help write and debug the analysis code,
run the regressions and tests, and prepare the notebook, exhibits, and report. I
also used it to implement the five language-ranked portfolios, filing-time
rebalancing, turnover and transaction-cost calculations, benchmark comparisons,
and the Q1-minus-Q5 long-short portfolios.

**What I wrote myself:** I read the assignment and TA updates and made the final
choices about the sample, controls, units, portfolio timing, and interpretation. I
decided that 10-K and 10-Q scores should be compared through historical form and
filing-quarter percentiles, checked the filing release timing for look-ahead bias,
and chose how transaction costs should enter the benchmark comparison. I reviewed
all of the code and every table and figure. I also interpreted the portfolio
results: the five groups look fairly ordered, but the long-short paths show
reversals and only suggest, rather than establish, rotation or seasonality.

**Anything the model got wrong that I had to correct:** Some outputs used unclear
“Tone” and “A/B” labels, and an early portfolio design did not make 10-K and 10-Q
scores sufficiently comparable. The first benchmark chart also included an
unneeded Negative line and did not deduct trading costs from Uncertainty Q1. I
caught these issues, clarified the design, checked the revised logic, and had the
analysis rerun.
