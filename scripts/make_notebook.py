"""Regenerates notebooks/assignment1.ipynb from this file.

Instructor utility. Students do not need to run this.
"""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "assignment1.ipynb"

SETUP = """```bash
pip install -r requirements.txt
$env:SEC_USER_AGENT = "Your Name your.netid@nyu.edu"   # PowerShell
python scripts/00_get_lexicons.py
python scripts/01_build_universe.py
python scripts/02_download_filings.py      # ~25 minutes, run it once
python scripts/03_get_market_data.py
```"""

CELLS: list[tuple[str, str]] = [
    ("md", """# Assignment 1: Uncertainty and Sentiment Analysis of Quarterly and Annual Financial Reports

FRE-GY 7871 A · NLP and the Investment Process · Fall 2026

**Name:**
**NetID:**
**GitHub repo:**

Work through the sections in order. Each names the exhibit it produces. Keep the
narrative cells: your report is graded on the reasoning, and the reasoning starts
here.

Before you begin, run `pytest -q`. Fourteen tests should fail. By the time you
submit, none should."""),

    ("md", "## 0. Setup\n\n" + SETUP),

    ("code", """import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import analysis, lexicons, market, panel, score
from src.config import (
    BENCHMARK, EVENT_WINDOW, INTERIM_DIR, OUTPUT_DIR, POSTEVENT_WINDOW,
    PREEVENT_WINDOW, PRICE_DIR, SAMPLE_END, SAMPLE_START, UNIVERSE_DIR, VIX_TICKER,
)

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 40)"""),

    ("md", """## 1. The two word lists

You are measuring **two different things**, and they stay separate throughout.

- **Sentiment.** How bad the news is. `Negative` (Fin-Neg), 2,355 words.
- **Uncertainty.** How sure management is. `Uncertainty` (Fin-Unc), 297 words:
  *approximate, contingency, depend, fluctuate, indefinite, uncertain,
  variability*.

"Results may fluctuate depending on factors beyond our control" contains no bad
news at all. It is a refusal to make a claim. Negative language is about the
level of the distribution; uncertain language is about its width.

Both come from one file, the Loughran-McDonald Master Dictionary. You do not need
the Harvard General Inquirer for this assignment."""),

    ("code", """word_lists = lexicons.load_all()
for name, words in sorted(word_lists.items()):
    print(f"{name:15s} {len(words):6,d}")

fin_neg = word_lists["Negative"]
fin_unc = word_lists["Uncertainty"]
print(f"\\noverlap between Fin-Neg and Fin-Unc: {len(fin_neg & fin_unc)} words")
print(sorted(fin_neg & fin_unc)[:15])"""),

    ("md", """## 2. The corpus

`filings_meta.csv` is one row per filing. Tokenise each document and build word
counts. Keep them as `collections.Counter`; Table 3 needs the full counts, not
just the category totals.

Watch `n_words` by form. 10-Ks in this universe run long because of risk factors;
10-Qs are much shorter. That gap drives a calendar sawtooth in any pooled time
series, which is the first thing Section 7 has to deal with."""),

    ("code", """meta = pd.read_csv(INTERIM_DIR / "filings_meta.csv", dtype={"cik": str},
                   parse_dates=["filing_date", "report_date", "acceptance_datetime"])
print(meta.shape)
meta.groupby("form")["n_words"].describe()[["count", "mean", "50%", "min", "max"]]"""),

    ("code", """# TODO: read each text file, tokenise, attach a Counter of word counts.
# Hint: gzip.open(path, "rt", encoding="utf-8"), then src.parse.tokenize.
# A few minutes over ~1,700 filings. Cache the result to disk."""),

    ("md", """## 3. Scoring

Two measures for each list: the proportional share, and the tf.idf score of
equation (1) in the paper. `pytest tests/test_score.py` has to pass first.

Weighting matters more for uncertainty than for sentiment. Words like *may* and
*approximately* appear in nearly every filing, so they carry almost no
cross-sectional information whatever they mean. That is what the
inverse-document-frequency term exists for."""),

    ("code", """# TODO: scored = score.score_corpus(docs, word_lists)"""),

    ("md", """## 4. Panel, filters and market data: **Table 1**

Reproduce LM's Table I: every filter in order, with the count removed. Start from
all 124 companies in the six funds, not from the survivors.

Day 0 is not the filing date. Implement `market.effective_event_day` and report
how many filings it moves."""),

    ("code", """prices = pd.read_csv(PRICE_DIR / "prices.csv", index_col=0, parse_dates=True)
volume = pd.read_csv(PRICE_DIR / "volume.csv", index_col=0, parse_dates=True)
shares = pd.read_csv(PRICE_DIR / "shares.csv")
calendar = market.trading_calendar(prices, BENCHMARK)
vix = prices[VIX_TICKER].dropna() if VIX_TICKER in prices.columns else None
print(f"{len(calendar)} trading days, {calendar.min().date()} to {calendar.max().date()}")"""),

    ("code", """# TODO: day 0, the [0,+3] excess return, and the two volatility measures:
#   pre_vol   realised vol over days [-60,-6]
#   post_vol  realised vol over days [+4,+63]
# Then: clean, waterfall = panel.apply_filters(...)
#       clean = panel.add_controls(...)"""),

    ("md", """## 5. Summary statistics: **Table 2**

Fin-Neg and Fin-Unc, both weightings, plus returns, volatility and controls, split
10-K versus 10-Q. Compare to LM's 10-K figures: Fin-Neg 1.39%, Fin-Unc 1.20%.

Report the correlation between the two tone measures. How much they overlap
decides how much of the rest of this notebook is two results rather than one."""),

    ("code", """# TODO: analysis.table_summary_statistics(clean)"""),

    ("md", """## 6. What the measures are made of: **Table 3**

The thirty most frequent words on each list, with each word's share of that list's
total count. Two panels, Fin-Neg and Fin-Unc.

Read this before trusting anything later. If the top five words are half the
count, you are running a five-word model, not a 2,355-word one. And ask of the
uncertainty list whether its common words are management hedging or the standing
furniture of a risk-factor section copied forward unchanged.

You need the answer in Section 8, where it decides between two competing readings
of whatever trend you find."""),

    ("code", """# TODO: analysis.table_top_words(...) for Negative and for Uncertainty"""),

    ("md", """## 7. Trends over time: **Figure 1**

**This is the centre of the assignment.** Aggregate to calendar quarters and plot
mean Fin-Neg and mean Fin-Unc across 2021-2025, with quarterly average VIX on a
second axis.

Two composition problems will wreck the chart if you ignore them:

1. **Form mix.** 10-Ks are longer and far heavier in risk-factor language, and
   they cluster in Q1. A pooled quarterly mean therefore carries a large annual
   sawtooth that is pure calendar artefact. Plot the two form types separately, or
   residualise on a form dummy first.
2. **Firm mix.** Different firms file in different quarters and differ enormously
   in baseline tone. Show the chart again using only firms present throughout, or
   demeaned within firm.

Describe the chart after both corrections, not before."""),

    ("code", """# TODO: analysis.figure_tone_over_time(clean, vix=vix)"""),

    ("md", """## 8. Is the trend real: **Table 4**

Three specifications for each measure.

**(a) Aggregate.** Quarterly mean tone on a linear time index. Twenty
observations. **Newey-West standard errors, four lags, are mandatory.** A
persistent series regressed on a trend gives badly inflated OLS t-statistics, and
with n = 20 you will walk straight into it. Report the OLS and Newey-West
t-statistics side by side so the gap is visible.

**(b) Within firm.** Filing-level tone on the time index, with firm and form fixed
effects, clustered by firm and date. Lead with this one. It asks whether the same
company writes more hedged filings than it used to, which is a question about
language rather than about who happened to file.

**(c) Split.** Run (b) separately on 10-Ks and 10-Qs.

Report the implied change per year in percentage points, not just the coefficient.

Then the graded part. 2021 to 2025 contains a pandemic tail, an inflation shock, a
rate cycle and an AI capital boom. If uncertainty language rises, is that managers
describing a more uncertain world, or lawyers adding boilerplate that never comes
back out? Point to the evidence in **your own Table 3** that separates those two
stories."""),

    ("code", """# TODO: analysis.table_trend_tests(clean)"""),

    ("md", """## 9. Does uncertainty predict volatility: **Table 5** and **Figure 2**

Dependent variable: annualised realised volatility of excess returns over days
[+4,+63], so the event window is excluded.

Run it **twice, once without `pre_vol` and once with it**. Without the control you
will get a large significant coefficient on Fin-Unc and it will be worthless:
volatile companies write hedged filings, and you will have rediscovered that. With
it you are asking whether the language predicts a *change* in volatility. The gap
between the two numbers is the result.

Figure 2 is the same point as a picture: post-filing volatility by uncertainty
quintile, with pre-filing volatility as a second line. Only the gap between the
lines is a text signal."""),

    ("code", """# TODO: analysis.table_volatility_regressions(clean)
#       analysis.figure_quintile_volatility(clean)"""),

    ("md", """## 10. The cross-sectional return test: **Table 6**

The LM Table IV analogue, and deliberately last. Day [0,+3] excess return on tone,
four columns, controls and quarter fixed effects, errors clustered by firm and by
date.

Run `analysis.power_check` **before** you look at the output."""),

    ("code", """# TODO: analysis.power_check(lm_tstat=-2.64, lm_n=50115, your_n=len(clean))
#       analysis.table_return_regressions(clean)"""),

    ("md", """## 11. Which of your results do you believe?

These tests are not equally powered and they do not fail in the same direction.
Write a paragraph placing each one:

- **Table 6**, four-day returns: underpowered. Small sample, small effect, and
  four-day returns are almost all idiosyncratic noise.
- **Table 4(b)**, within-firm trend: well powered. Firm fixed effects remove the
  dominant variance component and leave a systematic drift.
- **Table 5**, volatility: well powered. Volatility is persistent and predictable
  in a way returns are not.
- **Table 4(a)**, aggregate trend: the *opposite* problem. Twenty observations of
  a persistent series will hand you a large t-statistic whether or not anything is
  happening.

Significance here is entirely achievable, and *where* it appears matters more than
whether it appears. Do not write a blanket "the sample was too small", and do not
write a blanket "we found significance". Go test by test."""),

    ("code", """# TODO"""),

    ("md", """## 12. Do 10-Qs behave like 10-Ks?

Split the panel and re-run Tables 4 and 5 by form type. Address:

- 10-Qs are shorter and more templated. What does that do to the variance of a
  proportional tone measure?
- A 10-Q lands within days of an earnings release. Is the filing-date reaction
  even separately identified?
- Which form type should carry more textual signal, and does yours?"""),

    ("code", """# TODO"""),

    ("md", """## 13. What this sample cannot tell you

Your universe is the companies the six ARK funds hold **today**. Everything ARK
bought and sold between 2021 and 2025 is missing, and it was sold for reasons
correlated with returns.

For the trend work there is a sharper version of this problem, and it is the one
to write about. Survivors are the names that did *not* blow up. If failing
companies write more uncertain filings before they fail, and they have been
removed from your sample, your uncertainty trend is measuring the wrong
population. Say which direction that biases Figure 1, and how you would check it.

1. Roughly how many names are missing, and how would you find out?
2. Which direction does the bias push each of your results?
3. What would a point-in-time universe cost to build, and from what source?"""),

    ("code", """# TODO"""),

    ("md", """## 14. What you found

Three or four sentences for a portfolio manager, not a referee. Cover sentiment
and uncertainty separately: what each did over the period, whether either predicts
anything, and what would have to be true for it to be usable."""),
]


def main() -> int:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src)
        for kind, src in CELLS
    ]
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3", "language": "python", "name": "python3",
    }
    nb.metadata["language_info"] = {"name": "python", "version": "3.11"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, OUT)
    print(f"wrote {OUT} ({len(nb.cells)} cells)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
