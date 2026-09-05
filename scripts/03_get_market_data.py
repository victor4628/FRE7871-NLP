"""Download prices, volume and point-in-time shares outstanding.

    python scripts/03_get_market_data.py

Writes:
    data/prices/prices.csv   daily auto-adjusted closes, tickers in columns
    data/prices/volume.csv   daily share volume
    data/prices/shares.csv   dei:EntityCommonStockSharesOutstanding, per filing

On shares outstanding. The cover page of every 10-K and 10-Q states the share
count as of a date shortly before filing, and EDGAR exposes it as the XBRL fact
dei:EntityCommonStockSharesOutstanding. That is a point-in-time number: it was
printed on the document you are scoring. Market cap built from today's share
count and a 2021 price is a look-ahead bug, and it is the most common one in
assignments like this.

Some filings will have no such fact. Leave those rows missing rather than filling
them forward from a later filing, and report how many you lost.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import (  # noqa: E402
    ALT_BENCHMARK, BENCHMARK, INTERIM_DIR, PRICE_DIR, SAMPLE_END, SAMPLE_START,
    SEC_USER_AGENT,
)
from src.edgar import EdgarClient  # noqa: E402
from src.market import download_prices, download_volume  # noqa: E402

FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Preference order. The cover-page count is the cleanest, but multi-class filers
# report it per share class and it then disappears from the flat API, so the
# income-statement share counts are the fallback. All of them are reported ON the
# filing being scored, which is the property that matters.
SHARE_TAGS = [
    ("dei", "EntityCommonStockSharesOutstanding"),
    ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding"),
    ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic"),
    ("us-gaap", "CommonStockSharesOutstanding"),
]
# Prices need a run-up before the first filing (for the [-60,-6] controls) and a
# run-out after the last one (for the [0,+3] window).
PRICE_START = "2020-09-01"
PRICE_END = "2026-03-31"


def get_shares(client: EdgarClient, meta: pd.DataFrame) -> pd.DataFrame:
    """Share count as reported on each filing, using the first tag that has it."""
    rows = []
    for i, cik in enumerate(sorted(meta["cik"].unique()), 1):
        try:
            facts = client._get(FACTS_URL.format(cik=str(cik).zfill(10))).json().get("facts", {})
        except Exception:  # noqa: BLE001
            continue
        by_accession: dict[str, dict] = {}
        for ns, tag in reversed(SHARE_TAGS):        # least preferred first, overwrite
            for arr in facts.get(ns, {}).get(tag, {}).get("units", {}).values():
                for fact in arr:
                    accn = fact.get("accn")
                    if not accn or fact.get("val") in (None, 0):
                        continue
                    by_accession[accn] = {
                        "cik": str(cik).zfill(10),
                        "accession": accn,
                        "shares_outstanding": fact["val"],
                        "shares_as_of": fact.get("end"),
                        "shares_tag": f"{ns}:{tag}",
                    }
        rows.extend(by_accession.values())
        if i % 20 == 0:
            print(f"  company facts: {i} companies...")
    return pd.DataFrame(rows).drop_duplicates(subset=["accession"], keep="last")


def main() -> int:
    meta = pd.read_csv(INTERIM_DIR / "filings_meta.csv", dtype={"cik": str})
    tickers = sorted(meta["ticker"].unique()) + [BENCHMARK, ALT_BENCHMARK]
    print(f"{len(set(tickers))} tickers, {SAMPLE_START} to {SAMPLE_END}")

    px = download_prices(tickers, PRICE_START, PRICE_END)
    print(f"prices:  {px.shape[0]} days x {px.shape[1]} tickers -> {PRICE_DIR / 'prices.csv'}")
    missing = [t for t in tickers if t not in px.columns or px[t].notna().sum() == 0]
    if missing:
        print(f"  no price history for: {missing}")

    vol = download_volume(tickers, PRICE_START, PRICE_END)
    print(f"volume:  {vol.shape[0]} days x {vol.shape[1]} tickers -> {PRICE_DIR / 'volume.csv'}")

    client = EdgarClient(SEC_USER_AGENT or None)
    shares = get_shares(client, meta)
    shares.to_csv(PRICE_DIR / "shares.csv", index=False)
    matched = meta["accession"].isin(shares["accession"]).mean()
    print(f"shares:  {len(shares)} facts -> {PRICE_DIR / 'shares.csv'} "
          f"({matched:.1%} of filings matched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
