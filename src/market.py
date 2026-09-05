"""Prices, trading days, and the filing-period excess return.

The download and calendar helpers are finished. The two functions that decide
what "day 0" means and what "excess" means are yours, because those two decisions
are where most of the damage in this literature gets done.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .config import BENCHMARK, EVENT_WINDOW, PRICE_DIR


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
    """Daily share volume, used for the turnover / liquidity control."""
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


# ---------------------------------------------------------------------------
# Calendar -- finished
# ---------------------------------------------------------------------------
def trading_calendar(prices: pd.DataFrame, benchmark: str = BENCHMARK) -> pd.DatetimeIndex:
    """Trading days, taken from the benchmark's own price history."""
    if benchmark in prices.columns:
        return prices[benchmark].dropna().index
    return prices.dropna(how="all").index


def next_trading_day(day: pd.Timestamp, calendar: pd.DatetimeIndex) -> pd.Timestamp | None:
    """First calendar entry on or after `day`."""
    day = pd.Timestamp(day).normalize()
    pos = calendar.searchsorted(day, side="left")
    return calendar[pos] if pos < len(calendar) else None


def buy_and_hold_return(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> float:
    """Compound return from the close before `start` to the close on `end`.

    Day 0's return is the move from the day -1 close to the day 0 close, which is
    what "the market's reaction on the filing day" means.
    """
    s = series.dropna()
    idx = s.index
    i0 = idx.searchsorted(pd.Timestamp(start), side="left")
    i1 = idx.searchsorted(pd.Timestamp(end), side="right") - 1
    if i0 <= 0 or i1 >= len(idx) or i1 < i0:
        return np.nan
    return float(s.iloc[i1] / s.iloc[i0 - 1] - 1.0)


# ---------------------------------------------------------------------------
# YOUR CODE
# ---------------------------------------------------------------------------
def effective_event_day(
    filing_date: pd.Timestamp,
    acceptance_datetime: pd.Timestamp,
    calendar: pd.DatetimeIndex,
) -> pd.Timestamp | None:
    """Day 0: the first trading day on which the filing could have been traded.

    `acceptance_datetime` from EDGAR is UTC. (Verified: read as UTC, the hour
    histogram spans 06:00-22:00 Eastern, which is exactly EDGAR's acceptance
    window. Read as Eastern it would contain filings accepted at 01:00, which
    EDGAR does not accept.)

    The rule:
        acc_et  = acceptance_datetime converted to America/New_York
        base    = acc_et.date() + 1 day  if acc_et.time() >= 16:00  else acc_et.date()
        day0    = next_trading_day(max(base, filing_date))

    EDGAR already rolls `filing_date` forward for anything accepted after 17:30
    Eastern, so the max() handles that; the 16:00 test catches the window between
    the market close and EDGAR's cutoff, where the filing carries the current
    day's filing date but could not have been traded on it. Return None if you
    roll off the end of the calendar.

    TODO(student). This is four lines of code and it moves a large share of your
    sample by one day. Report how many filings it moves.
    """
    raise NotImplementedError("implement effective_event_day")


def excess_return(
    ticker: str,
    day0: pd.Timestamp,
    prices: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    benchmark: str = BENCHMARK,
    window: tuple[int, int] = EVENT_WINDOW,
) -> float:
    """Buy-and-hold excess return over the event window.

        excess = BHR(stock, day0 .. day0+3) - BHR(benchmark, day0 .. day0+3)

    LM subtract the CRSP value-weighted index; SPY is the free stand-in. This is
    the "relative" in relative return: everything you report is relative to a
    benchmark, and which benchmark you pick is a modelling choice you must state.

    TODO(student): locate day0 in `calendar`, step `window[0]` and `window[1]`
    trading days from it, and difference the two buy-and-hold returns. Return nan
    if either leg is unavailable.
    """
    raise NotImplementedError("implement excess_return")
