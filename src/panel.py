"""Assembling the firm-filing panel, and the filters that define the sample.

Loughran and McDonald's Table I is a waterfall: 121,217 filings in, 50,115 out,
with every filter and how much it cost written down. You reproduce that table for
your own sample. A filter you applied but did not report is the thing this course
treats as academic dishonesty rather than sloppiness, so keep the counts as you go.
"""

from __future__ import annotations

import pandas as pd

from .config import (
    MIN_PRICE, MIN_TRADING_DAYS_AFTER, MIN_TRADING_DAYS_BEFORE,
    MIN_WORDS_10K, MIN_WORDS_10Q, POSTEVENT_WINDOW, PREEVENT_WINDOW,
)


class Waterfall:
    """Records how many observations each filter removed. Print it as Table 1."""

    def __init__(self, label: str, n: int):
        self.rows = [(label, n, None)]

    def step(self, label: str, n_after: int) -> None:
        removed = self.rows[-1][1] - n_after
        self.rows.append((label, n_after, removed))

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            self.rows, columns=["Filter", "Sample size", "Observations removed"]
        )


# ---------------------------------------------------------------------------
# YOUR CODE
# ---------------------------------------------------------------------------
def apply_filters(
    filings: pd.DataFrame,
    prices: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, Waterfall]:
    """Apply the sample filters in order, recording the waterfall.

    Required filters, in this order (the assignment's analogue of LM Table I;
    the thresholds live in src/config.py):

      1. Start: all 10-K and 10-Q filings for the universe in the sample window.
      2. Drop amendments (10-K/A, 10-Q/A) and any filing whose primary document
         failed to parse.
      3. Document length: 10-Ks with at least MIN_WORDS_10K words, 10-Qs with at
         least MIN_WORDS_10Q.
      4. One filing per firm per calendar quarter. Keep the earliest, drop the rest.
      5. A usable day 0 (see market.effective_event_day).
      6. Price on day -1 of at least MIN_PRICE dollars.
      7. At least MIN_TRADING_DAYS_BEFORE trading days of returns before day 0 and
         MIN_TRADING_DAYS_AFTER after, so the controls, the event window and the
         post-filing volatility window all exist.

    TODO(student). Return the filtered panel and the Waterfall object.
    """
    raise NotImplementedError("implement apply_filters")


def add_controls(
    panel: pd.DataFrame,
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Add the regression controls.

    LM control for size, book-to-market, share turnover, a pre-filing alpha,
    institutional ownership and a NASDAQ dummy. Institutional ownership and
    book-to-market need paid data, so this assignment uses what is free:

      log_size        log market capitalisation on day -1
                      = log(price on day -1 times shares outstanding)
                      Shares outstanding: the cover-page XBRL fact
                      dei:EntityCommonStockSharesOutstanding, which is
                      point-in-time by construction, because it is printed on the
                      filing you are scoring. Do NOT use today's share count.
      log_dollar_vol  log of average daily dollar volume over PREEVENT_WINDOW
                      (the liquidity / turnover control)
      pre_excess_ret  the firm's excess return over PREEVENT_WINDOW
                      (stands in for LM's pre-filing-date Fama-French alpha)
      is_10k          1 for a 10-K, 0 for a 10-Q
      quarter         calendar quarter of day 0, for fixed effects
      pre_vol         annualised realised volatility over PREEVENT_WINDOW
      post_vol        annualised realised volatility over POSTEVENT_WINDOW,
                      days [+4,+63], the dependent variable of Table 5

    pre_vol is not decoration. It is the control that decides whether Table 5
    says anything: volatile companies write hedged filings, so without it the
    uncertainty coefficient just re-measures the stock's own volatility.

    Optional, for extra credit: book-to-market from the XBRL company-facts API
    (us-gaap:StockholdersEquity as of the filing's report date).

    TODO(student).
    """
    raise NotImplementedError("implement add_controls")
