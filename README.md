# Assignment 1: Uncertainty and Sentiment Analysis of Quarterly and Annual Financial Reports

FRE-GY 7871 A · NLP and the Investment Process · Fall 2026
Out: Session 1 (5 Sep 2026) · Due: 9:00 AM, Session 2 (12 Sep 2026)

**This repository gets you the data. Everything after that is yours to write.**

The full assignment brief is on Brightspace and it is the specification. This file
only covers running the pipeline.

---

## What this gives you

Four scripts that put a clean dataset on your disk:

| Script | Output | Time |
|---|---|---|
| `00_get_lexicons.py` | The Loughran-McDonald Master Dictionary, in `data/lexicons/` | ~15 s |
| `01_build_universe.py` | The 124 ARK holdings resolved to SEC filers, in `data/universe/universe.csv` | ~1 min |
| `02_download_filings.py` | ~1,700 filings as extracted text, plus `data/interim/filings_meta.csv` | ~25 min |
| `03_get_market_data.py` | Daily prices, volume, VIX and per-filing share counts, in `data/prices/` | ~3 min |

The modules they lean on, which you can read and use as they are:

| Module | What it does |
|---|---|
| `src/edgar.py` | Rate-limited, cached EDGAR client. Returns point-in-time filing metadata, including the acceptance timestamp you need for day 0. |
| `src/parse.py` | Filing HTML to word counts. Strips inline-XBRL scaffolding and mostly-numeric tables. |
| `src/lexicons.py` | Loads Fin-Neg and Fin-Unc out of the master dictionary. |
| `src/market.py` | Downloads daily prices and volume. Nothing else. |
| `src/config.py` | The sample definition: funds, window, forms, paths. |

## What you write

Everything else, in your own notebook, from the specification in the brief:

- the two tone measures, proportional and tf.idf
- the trading calendar, the day-0 rule, and the filing-period excess return
- realised volatility before and after each filing
- the sample filters, the controls, and the waterfall in Table 1
- all seven exhibits and the regressions behind them

There is no notebook template and there are no tests in this repository. Structure
your own notebook around the exhibits in the brief, in that order.

---

## Setup

```bash
git clone <your fork of this repo>
cd assignment1
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

Tell the SEC who you are. They rate-limit and block unidentified traffic, and it is
their server:

```bash
$env:SEC_USER_AGENT = "Your Name your.netid@nyu.edu"     # PowerShell
export SEC_USER_AGENT="Your Name your.netid@nyu.edu"     # bash
```

Then, in order:

```bash
python scripts/00_get_lexicons.py
python scripts/01_build_universe.py
python scripts/02_download_filings.py --limit 3   # check your setup first
python scripts/02_download_filings.py             # the real run, ~25 min
python scripts/03_get_market_data.py
```

Add `--drop-html` to `02` if you are short on disk: it deletes the raw filings after
extracting the text, at the cost of re-downloading if you change the parser.

Nothing under `data/` is committed except the frozen ARK holdings snapshot.
Everything else there is reproducible from these four scripts, which is the point.

## Reading the data you end up with

```python
import gzip
import pandas as pd
from src.lexicons import load_all
from src.parse import tokenize

meta = pd.read_csv("data/interim/filings_meta.csv",
                   parse_dates=["filing_date", "acceptance_datetime"])
word_lists = load_all()          # "Negative" and "Uncertainty" are the two you need

with gzip.open(meta.loc[0, "text_path"], "rt", encoding="utf-8") as fh:
    tokens = tokenize(fh.read())
```

`filings_meta.csv` has one row per filing: ticker, cik, form, filing_date,
report_date, **acceptance_datetime**, accession, n_words, n_distinct, text_path.

## Submitting

1. **GitHub.** Push your work here, public or with a viewable link. It must contain
   your notebook with output saved, your code, `AI_USE.md`, and no data files.
2. **Brightspace.** Upload your report as a PDF and paste the repo URL.

## Things that will cost you marks

- Using today's share count with a 2021 price. The count printed on each filing is in
  `data/prices/shares.csv`; use that one.
- Treating the EDGAR filing date as tradable without checking `acceptance_datetime`.
- Computing tf.idf statistics on one corpus and running regressions on another.
- Plotting a quarterly tone average without separating 10-Ks from 10-Qs. The annual
  sawtooth you will see is a calendar artefact, not a trend.
- An aggregate trend test with plain OLS standard errors.
- Reporting the volatility regression without the pre-filing volatility control.
- Reporting a filter you applied without listing it in Table 1.
- A conclusion the standard errors do not support, in either direction.
