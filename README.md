# Assignment 1: Uncertainty and Sentiment Analysis of Quarterly and Annual Financial Reports

## Completed analysis

Start with [the executed notebook](assignment1.ipynb), containing six tables,
Figure 1, all regression sensitivities and saved test output, and the
[English report](output/pdf/assignment1_report.pdf).
[METHODOLOGY.md](METHODOLOGY.md) documents the specification;
[AI_USE.md](AI_USE.md) discloses assistance and authorship.

[ANALYSIS_CHOICES.md](ANALYSIS_CHOICES.md) separates the brief's explicit
requirements from implementation decisions and additional statistical checks.
The report includes a plain-language table guide. "Score" means the named uncertainty or
negative-language measure; it is not a separate statistical test.

The revised sample contains 1,536 reports from 91 issuers. It follows the TA's
September 7 filters, including the $3 day -1 price threshold, 60-day history
requirements and one earliest filing per company-quarter. Outcome models include
the required size, dollar-volume, prior-return, report-type, company and quarter
controls. Table 5A compares models without and with prior volatility on one full sample;
Table 5B estimates the same pair separately for 10-K and 10-Q filings;
Table 6's pooled return estimates remain imprecise.

For reproduction, follow [RUNNING_zh.md](RUNNING_zh.md). Run acquisition scripts
00-03, audit 04, price/actions download 05, then `scripts/07_build_notebook.py`
(which executes analysis 06). Build the report with
`scripts/08_build_report.py --author "Your Name" --netid your_netid`.
Generated data stay local; only the instructor's frozen snapshot is versioned.
Future SEC/Yahoo downloads may change. `requirements-lock.txt` records the
Windows environment. The original instructor README follows; its remarks about
missing analysis, notebooks and tests describe the starter repository.

---

FRE-GY 7871 A · NLP and the Investment Process · Fall 2026
Out: Session 1 (5 Sep 2026) · Due: 9:00 AM, Session 2 (12 Sep 2026)

**This repository gets you the data. Everything after that is yours to write.**

The one-page assignment sheet on Brightspace says what to produce. This file says how
to get the data and pins down the details that need exact numbers. `REPORT.md` is the
skeleton for your write-up and lists the six questions.

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

### If the download will not run

**Try it properly first.** Getting a point-in-time dataset off EDGAR is part of the
assignment, and most failures are fixable in a minute:

- `RuntimeError` about the user agent: you have not set `SEC_USER_AGENT`. See Setup.
- 403s or hangs partway through: you are being rate-limited. The scripts already
  throttle to six requests a second; re-run and they resume from the cache.
- The run dies overnight: it is resumable. Run it again, it skips what it has.
- Disk pressure: add `--drop-html`.

If you have genuinely tried and it still will not work, email
**axs10695@nyu.edu** and the corpus will be sent to you directly. Do that only
after attempting the download, and say what you tried and what the error was.

## What you write

Everything else, in your own notebook:

- the two tone measures, proportional and tf.idf
- the trading calendar, the day-0 rule, and the filing-period excess return
- realised volatility before and after each filing
- the sample filters, the controls, and the waterfall in Table 1
- all seven exhibits and the regressions behind them

There is no notebook template and there are no tests in the starter repository.
Structure your own notebook around the exhibits on the assignment sheet, in that order.

## The details that need exact numbers

The September 7 instructor update fixes the following choices for everyone in the
class.

**Sample filters**, applied in this order:

1. Drop amendments and anything that failed to parse.
2. Require at least 2,000 words for a 10-K and 1,000 for a 10-Q.
3. Keep the earliest filing per company and calendar quarter.
4. Require a usable day 0 and a day -1 price of at least $3.
5. Require at least 60 trading days of returns before and after day 0.

**Day 0.** Use the first trading day on or after the later of the filing date and
the acceptance date shifted one day when acceptance occurs at or after 16:00
Eastern. Convert `acceptance_datetime` from UTC first.

**Windows.** Measure the SPY excess return over [0,+3] from the day -1 close.
Measure pre-filing volatility and controls over [-60,-6] and subsequent realized
volatility over [+4,+63].

**Controls.** Include log size, log dollar volume and SPY excess return over
[-60,-6], pre-filing volatility, a 10-K indicator, and company and calendar-quarter
fixed effects.

**TF-IDF self-check.** With three documents and list `{LOSS, RISK}`, the required
TF-IDF values for d1-d3 are 0.8480, 0.2885 and 0.5026 using natural logarithms.

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

Run the `--limit 3` version first. It takes a minute and tells you whether your
setup works before you commit to the full crawl.

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
- Reporting a filter you applied without listing it in Table 1.
- Describing what a chart shows before asking what else is in it.
- A conclusion the standard errors do not support, in either direction.
