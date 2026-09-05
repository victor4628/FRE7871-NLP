"""Build the filer universe from the six ARK ETFs.

    python scripts/01_build_universe.py            # use the frozen snapshot (default)
    python scripts/01_build_universe.py --refresh  # re-download today's holdings

Reads data/universe/ark_holdings_raw.csv, a frozen snapshot of the six funds'
published daily holdings, so that everyone in the class works on the same sample
and results are comparable. --refresh pulls live holdings instead, which will give
you a different universe from everyone else's; if you use it, say so.

Writes data/universe/universe.csv with one row per company:
    ticker, cik, sec_name, ark_name, funds, n_10k, n_10q, status

Read the survivorship warning in the assignment before you use this file. These
are the companies ARK holds *now*. Any company ARK bought and sold during
2021-2025 is missing, and it is missing for reasons that are correlated with
returns.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import (  # noqa: E402
    ARK_FUNDS, SAMPLE_END, SAMPLE_START, SEC_USER_AGENT, UNIVERSE_DIR,
)
from src.edgar import EdgarClient  # noqa: E402

ARK_CSV_BASE = "https://assets.ark-funds.com/fund-documents/funds-etf-csv/"
ARK_CSV_NAMES = {
    "ARKK": "ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv",
    "ARKQ": "ARK_AUTONOMOUS_TECH._&_ROBOTICS_ETF_ARKQ_HOLDINGS.csv",
    "ARKW": "ARK_NEXT_GENERATION_INTERNET_ETF_ARKW_HOLDINGS.csv",
    "ARKF": "ARK_FINTECH_INNOVATION_ETF_ARKF_HOLDINGS.csv",
    "ARKG": "ARK_GENOMIC_REVOLUTION_ETF_ARKG_HOLDINGS.csv",
    "ARKX": "ARK_SPACE_EXPLORATION_&_INNOVATION_ETF_ARKX_HOLDINGS.csv",
}

RAW_PATH = UNIVERSE_DIR / "ark_holdings_raw.csv"
OUT_PATH = UNIVERSE_DIR / "universe.csv"


def refresh_holdings() -> pd.DataFrame:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (course assignment)"})
    frames = []
    for fund in ARK_FUNDS:
        url = ARK_CSV_BASE + ARK_CSV_NAMES[fund]
        resp = session.get(url, timeout=60)
        resp.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(resp.text)))
        rows = [r for r in rows if (r.get("ticker") or "").strip()]
        print(f"  {fund}: {len(rows)} holdings, as of {rows[0]['date']}")
        frames.append(pd.DataFrame(rows))
    out = pd.concat(frames, ignore_index=True)
    out.to_csv(RAW_PATH, index=False)
    return out


def clean_ticker(raw: str) -> str | None:
    """ARK publishes Bloomberg-style tickers. Strip the exchange code, drop
    non-US listings and non-equity positions."""
    t = (raw or "").strip().upper().split(" ")[0]
    if not t or "/" in t:          # crypto and derivative share classes
        return None
    if re.fullmatch(r"\d+", t):    # foreign numeric listings (Tokyo, Hong Kong)
        return None
    return t


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download live holdings")
    args = ap.parse_args()

    if args.refresh or not RAW_PATH.exists():
        print("Downloading ARK holdings...")
        raw = refresh_holdings()
    else:
        raw = pd.read_csv(RAW_PATH)
        print(f"Using frozen snapshot {RAW_PATH.name} "
              f"({len(raw)} positions, as of {sorted(raw['date'].unique())})")

    funds_by_ticker: dict[str, set[str]] = defaultdict(set)
    names: dict[str, str] = {}
    for _, r in raw.iterrows():
        t = clean_ticker(r["ticker"])
        if t is None:
            continue
        funds_by_ticker[t].add(r["fund"])
        names.setdefault(t, str(r["company"]).strip())
    print(f"Unique US-listed tickers in the union: {len(funds_by_ticker)}")

    client = EdgarClient(SEC_USER_AGENT or None)
    cik_map = client.ticker_to_cik()

    records = []
    unmatched = []
    for i, ticker in enumerate(sorted(funds_by_ticker), 1):
        cik = cik_map.get(ticker)
        if cik is None:
            unmatched.append(ticker)
            continue
        filings = client.list_filings(cik, ["10-K", "10-Q"], SAMPLE_START, SAMPLE_END)
        n_10k = int((filings["form"] == "10-K").sum()) if len(filings) else 0
        n_10q = int((filings["form"] == "10-Q").sum()) if len(filings) else 0
        status = "domestic_filer" if (n_10k or n_10q) else "no_10x_filings"
        records.append({
            "ticker": ticker,
            "cik": cik,
            "sec_name": filings["company"].iloc[0] if len(filings) else "",
            "ark_name": names[ticker],
            "funds": "|".join(sorted(funds_by_ticker[ticker])),
            "n_10k": n_10k,
            "n_10q": n_10q,
            "status": status,
        })
        if i % 20 == 0:
            print(f"  checked {i} tickers...")

    df = pd.DataFrame(records).sort_values("ticker")
    df.to_csv(OUT_PATH, index=False)

    keep = df[df["status"] == "domestic_filer"]
    print()
    print(f"No CIK on file (foreign / private):      {len(unmatched):4d}  {sorted(unmatched)}")
    print(f"CIK found, no 10-K or 10-Q in window:    {(df['status'] != 'domestic_filer').sum():4d}")
    print(f"Filers kept:                             {len(keep):4d}")
    print(f"10-K filings: {keep['n_10k'].sum()}   10-Q filings: {keep['n_10q'].sum()}   "
          f"total: {keep['n_10k'].sum() + keep['n_10q'].sum()}")
    print(f"\nWrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
