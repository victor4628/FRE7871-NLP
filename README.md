# Assignment 1: Uncertainty and Sentiment Analysis of Quarterly and Annual Financial Reports

FRE-GY 7871 A · NLP and the Investment Process · Fall 2026
Out: Session 1 (5 Sep 2026) · Due: 9:00 AM, Session 2 (12 Sep 2026)

You are replicating the core of Loughran & McDonald (2011), *"When Is a Liability
Not a Liability? Textual Analysis, Dictionaries, and 10-Ks"*, on a small modern
sample: five years of 10-K and 10-Q filings from the companies held by six ARK
Invest ETFs.

Two dimensions, kept separate throughout: **negative sentiment** (H4N-Inf against
Fin-Neg, tested on returns) and **uncertainty sentiment** (Fin-Unc, tested on returns
and on realised volatility after the filing).

The full assignment brief is on Brightspace. This file is about running the code.

---

## Setup

```bash
git clone <your fork of this repo>
cd assignment1
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

Tell the SEC who you are. They rate-limit and block unidentified traffic, and it
is their server:

```bash
$env:SEC_USER_AGENT = "Your Name your.netid@nyu.edu"     # PowerShell
export SEC_USER_AGENT="Your Name your.netid@nyu.edu"     # bash
```

Then, in order:

```bash
python scripts/00_get_lexicons.py        # word lists            ~15 s
python scripts/01_build_universe.py      # 93 filers             ~1 min
python scripts/02_download_filings.py    # ~1,700 filings        ~25 min
python scripts/03_get_market_data.py     # prices, volume, shares ~3 min
jupyter lab notebooks/assignment1.ipynb
```

Run `python scripts/02_download_filings.py --limit 3` first if you want to check
your setup before committing to the full download. Add `--drop-html` if you are
short on disk: it deletes the raw filings after extracting the text, at the cost
of having to re-download if you change the parser.

Nothing under `data/` is committed. Everything there is reproducible from the
scripts, which is the point.

---

## What is finished and what is yours

Finished — read it, do not rewrite it:

| File | What it does |
|---|---|
| `src/edgar.py` | Rate-limited, cached EDGAR client. Returns point-in-time metadata including `acceptanceDateTime`. |
| `src/parse.py` | Filing HTML to tokens. Strips inline-XBRL scaffolding and mostly-numeric tables. |
| `src/lexicons.py` | Loads the LM master dictionary; rebuilds H4N-Inf from the Harvard General Inquirer. |
| `src/market.py` (top half) | Price/volume download, trading calendar, buy-and-hold helper. |
| `scripts/00`–`03` | The data pipeline. |

Yours — every function raising `NotImplementedError`:

| File | What you implement |
|---|---|
| `src/score.py` | Proportional and tf.idf (equation 1) tone measures. |
| `src/market.py` (bottom) | `effective_event_day`, `excess_return`. |
| `src/panel.py` | Sample filters with a waterfall, and the controls. |
| `src/analysis.py` | Tables 2, 3 and 4, Figure 1, and the power check. |

## Tests

```bash
pytest -q
```

Ten tests pass now (the parser, and the proportional score). Fourteen fail
until you write the code; they encode a hand-computed worked example of
equation (1) and the four cases of the day-0 rule. All of them must pass when you
submit.

## Submitting

1. **GitHub.** Push this repo, public or with a viewable link. It must contain the
   completed notebook with output, your `src/` code, a passing `pytest -q`,
   `AI_USE.md`, and no data files.
2. **Brightspace.** Upload `REPORT.pdf` (from `REPORT.md`) and paste the repo URL.

Both are due at 9:00 AM before Session 2. Late work loses 10 points per 24 hours,
up to 72 hours.

## Things that will cost you marks

- Using today's share count with a 2021 price. The share count printed on the
  filing is in `data/prices/shares.csv`; use it.
- Treating the EDGAR filing date as tradable without checking the acceptance time.
- Computing tf.idf statistics on one corpus and running regressions on another.
- Reporting a filter you applied without listing it in Table 1.
- Reporting a significant result without saying what your sample size can detect.
- A conclusion the standard errors do not support. A clean null result, honestly
  established, earns full marks.
