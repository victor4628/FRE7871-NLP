"""Regenerates notebooks/assignment1.ipynb from this file.

Instructor utility. Students do not need to run this.
"""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "assignment1.ipynb"

CELLS: list[tuple[str, str]] = [
    ("md", """# Assignment 1 — Loughran-McDonald sentiment on the ARK universe

FRE-GY 7871 A · NLP and the Investment Process · Fall 2026

**Name:**
**NetID:**
**GitHub repo:**

Work through the sections in order. Each one names the exhibit it produces. Keep
the narrative cells: your report is graded on the reasoning, and the reasoning
starts here.

Before you begin, run `pytest -q`. Three of the test modules should fail. By the
time you submit, none should."""),

    ("md", """## 0. Setup

Prerequisites, in order:

```bash
pip install -r requirements.txt
$env:SEC_USER_AGENT = "Your Name your.netid@nyu.edu"   # PowerShell
python scripts/00_get_lexicons.py
python scripts/01_build_universe.py
python scripts/02_download_filings.py      # ~25 minutes, run it once
python scripts/03_get_market_data.py
```"""),

    ("code", """import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd().parent))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import analysis, lexicons, market, panel, score
from src.config import (
    BENCHMARK, EVENT_WINDOW, INTERIM_DIR, OUTPUT_DIR, PRICE_DIR, SAMPLE_END,
    SAMPLE_START, UNIVERSE_DIR,
)

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 40)"""),

    ("md", """## 1. The word lists

Load both lists and check that you have reproduced the paper's central example
before you do anything else. Words like TAX, COSTS, CAPITAL, LIABILITY, FOREIGN
and VICE should be on the Harvard list and off the Loughran-McDonald list. If
they are not, your lists are wrong and nothing downstream will mean anything.

Report the size of each list, and note the deviation from the paper: LM built
H4N-Inf by hand and got 4,187 forms from 2,005 Harvard roots. Our rule-based
inflection gives a different number. Say what yours is."""),

    ("code", """word_lists = lexicons.load_all()
for name, words in sorted(word_lists.items()):
    print(f"{name:15s} {len(words):6,d}")

check = ["TAX", "COSTS", "CAPITAL", "LIABILITY", "FOREIGN", "VICE", "MINE",
         "LOSS", "RESTATED", "LITIGATION", "IMPAIRMENT"]
pd.DataFrame({
    "on H4N-Inf": [w in word_lists["H4N_Inf"] for w in check],
    "on Fin-Neg": [w in word_lists["Negative"] for w in check],
}, index=check)"""),

    ("md", """## 2. The corpus

`filings_meta.csv` is one row per filing. Tokenise each document's text and build
the word counts you will score. Keep counts as `collections.Counter` objects; you
need the full counts for Table 3, not just the category totals.

Note what you are looking at when you check `n_words`: 10-Ks in this universe run
long (risk factors), 10-Qs are much shorter. That difference alone will move every
proportional measure, which is why the 10-K/10-Q split in Section 10 matters."""),

    ("code", """meta = pd.read_csv(INTERIM_DIR / "filings_meta.csv", dtype={"cik": str},
                   parse_dates=["filing_date", "report_date", "acceptance_datetime"])
print(meta.shape)
meta.groupby("form")["n_words"].describe()[["count", "mean", "50%", "min", "max"]]"""),

    ("code", """# TODO: read each text file, tokenise, and attach a Counter of word counts.
# Hint: gzip.open(path, "rt", encoding="utf-8"), then src.parse.tokenize.
# This takes a few minutes over ~1,700 filings. Cache the result to disk."""),

    ("md", """## 3. Scoring — Section 3 of the assignment

Two measures per word list: the proportional share and the tf.idf score of
equation (1). `pytest tests/test_score.py` has to pass first."""),

    ("code", """# TODO: scored = score.score_corpus(docs, word_lists)"""),

    ("md", """## 4. Market data and the filing-period return

Day 0 is not the filing date. Implement `market.effective_event_day` and report
how many filings it moves by a day — that number belongs in your report."""),

    ("code", """prices = pd.read_csv(PRICE_DIR / "prices.csv", index_col=0, parse_dates=True)
volume = pd.read_csv(PRICE_DIR / "volume.csv", index_col=0, parse_dates=True)
shares = pd.read_csv(PRICE_DIR / "shares.csv")
calendar = market.trading_calendar(prices, BENCHMARK)
print(f"{len(calendar)} trading days, {calendar.min().date()} to {calendar.max().date()}")"""),

    ("code", """# TODO: day 0 for every filing, then the [0,+3] excess return against SPY.
# Report: how many filings move by one day under the after-16:00 rule?"""),

    ("md", """## 5. The panel and the filters — **Table 1**

Reproduce LM's Table I for your sample: every filter, in order, with the count
removed. This is the table a reader uses to decide whether to believe the rest."""),

    ("code", """# TODO: clean, waterfall = panel.apply_filters(...)
#       clean = panel.add_controls(...)
#       waterfall.to_frame()"""),

    ("md", """## 6. Summary statistics — **Table 2**

Mean, median and standard deviation of every word-list proportion, the event
return and the controls, split 10-K versus 10-Q. Compare your Fin-Neg mean to
LM's 1.39% for 10-Ks. If yours is far away, explain why before you move on —
different decade, different universe, different table-stripping rule."""),

    ("code", """# TODO: analysis.table_summary_statistics(clean)"""),

    ("md", """## 7. Composition of negative tone — **Table 3**

The thirty most frequent words on each negative list, with each word's share of
that list's total count. Produce it for H4N-Inf and Fin-Neg.

This is the exhibit that carries the paper's argument, and it is the one place
where a sample of 1,700 filings is as convincing as a sample of 50,000. Read your
own H4N-Inf column and write down what fraction of the "negative" word count
comes from words that are not negative in a filing."""),

    ("code", """# TODO: analysis.table_top_words(...) for H4N_Inf and for Negative"""),

    ("md", """## 8. Power — do this before Section 9

LM report t = -2.64 for Fin-Neg on 50,115 filings. You have far fewer. Compute
the t-statistic you should expect to see if their effect is real and present in
your sample, and write it down now.

Doing this before you look at your regression output is the entire point. It is
the difference between reporting a null result and rationalising one."""),

    ("code", """# TODO: analysis.power_check(lm_tstat=-2.64, lm_n=50115, your_n=len(clean))"""),

    ("md", """## 9. Filing-period returns by quintile — **Figure 1**

Median [0,+3] excess return by quintile of negative tone, one line per word list.
In the paper, Fin-Neg is monotonic and H4N-Inf is not. Say whether yours is, and
whether five bins over your sample can distinguish a monotonic pattern from noise."""),

    ("code", """# TODO: analysis.figure_quintile_returns(clean, ["prop_H4N_Inf", "prop_Negative"])"""),

    ("md", """## 10. Regressions — **Table 4**

Four columns: each word list under each weighting scheme, with controls and
quarter fixed effects, standard errors clustered by firm and by date."""),

    ("code", """# TODO: analysis.table_regressions(clean)"""),

    ("md", """## 11. Extension A — do 10-Qs behave like 10-Ks?

The paper is about annual reports. Split your panel and run Table 4 separately on
10-Ks and on 10-Qs. Three things to address:

- 10-Qs are shorter and far more templated. What does that do to the variance of
  a proportional tone measure?
- A 10-Q lands within days of an earnings release. Is a filing-date return even
  identified, or are you measuring the earnings reaction?
- Which of the two form types should carry more textual signal, and does yours?"""),

    ("code", """# TODO"""),

    ("md", """## 12. Extension B — what this sample cannot tell you

Your universe is the set of companies the six ARK funds hold **today**. Every
company ARK bought and sold between 2021 and 2025 is missing, and they were sold
for reasons correlated with returns. Answer, concretely:

1. Roughly how many names are missing, and how would you find out?
2. Which direction does the bias push the tone-return relation, and why?
3. What would a point-in-time universe cost to build here, and from what source?

A specific answer with a number beats a paragraph about survivorship in general."""),

    ("code", """# TODO"""),

    ("md", """## 13. What you found

Three or four sentences, written for a portfolio manager, not a referee. What is
the signal, what is it not, and what would have to be true for it to work at the
scale you tested it? A clean null result, honestly established, is a full-marks
answer here."""),
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
