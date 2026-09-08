"""Downloading daily price and volume data.

That is all this module does. Trading calendars, event windows, buy-and-hold
returns and realised volatility are yours to write; the assignment brief
specifies each of them.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import PRICE_DIR


# ---------------------------------------------------------------------------
# Downloading -- finished
# ---------------------------------------------------------------------------
def download_prices(
    tickers: list[str],
    start: str,
    end: str,
    cache_path: Path | None = None,
) -> pd.DataFrame:
    """Daily total-return prices (auto-adjusted close), tickers in columns.

    Cached as a parquet/csv file so you download once. Delete the cache to refresh.
    """
    import yfinance as yf

    cache_path = Path(cache_path or PRICE_DIR / "prices.csv")
    if cache_path.exists():
        px = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        missing = [t for t in tickers if t not in px.columns]
        if not missing:
            return px

    raw = yf.download(
        tickers=sorted(set(tickers)),
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    px = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    px = px.sort_index().dropna(how="all")
    px.to_csv(cache_path)
    return px


def download_volume(tickers: list[str], start: str, end: str,
                    cache_path: Path | None = None) -> pd.DataFrame:
    """Daily share volume, used to construct the dollar-volume control."""
    import yfinance as yf

    cache_path = Path(cache_path or PRICE_DIR / "volume.csv")
    if cache_path.exists():
        return pd.read_csv(cache_path, index_col=0, parse_dates=True)
    raw = yf.download(tickers=sorted(set(tickers)), start=start, end=end,
                      auto_adjust=True, progress=False, threads=True)
    vol = raw["Volume"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Volume"]]
    vol = vol.sort_index().dropna(how="all")
    vol.to_csv(cache_path)
    return vol
