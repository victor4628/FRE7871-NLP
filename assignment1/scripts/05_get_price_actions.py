"""Supplement returns with split history for historical size/turnover controls."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import PRICE_DIR, INTERIM_DIR


def main():
    target = PRICE_DIR / "control_prices_manifest.json"
    if target.exists():
        print("Using cached control prices and actions:", target)
        return
    meta = pd.read_csv(INTERIM_DIR / "filings_meta.csv")
    tickers = sorted(set(meta.ticker))
    # Yahoo's Close is split adjusted as of retrieval, so get split events right
    # through retrieval, not just through the last event-study return window.
    end = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
    raw = yf.download(tickers, start="2020-09-01", end=end, auto_adjust=False,
                      actions=True, progress=False, threads=True)
    for field, filename in [("Close", "close_split_adjusted.csv"),
                             ("Volume", "volume_split_adjusted.csv"),
                             ("Stock Splits", "stock_splits.csv")]:
        data = raw[field].sort_index()
        if any(t not in data or not data[t].notna().any() for t in tickers):
            raise RuntimeError(f"Incomplete download for {field}; inspect before caching.")
        data.to_csv(PRICE_DIR / filename)
    target.write_text(json.dumps({"retrieved_utc": datetime.now(timezone.utc).isoformat(),
                                  "start": "2020-09-01", "end_exclusive": end,
                                  "tickers": tickers}, indent=2), encoding="utf-8")
    print("Saved control prices and split actions for", len(tickers), "tickers")


if __name__ == "__main__":
    main()
