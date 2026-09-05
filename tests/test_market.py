"""Tests for the point-in-time event-day rule.

These fail until you implement market.effective_event_day. They encode the four
cases you have to get right; a passing implementation is worth more than a
paragraph explaining that you thought about look-ahead bias.
"""

import pandas as pd
import pytest

from src.market import buy_and_hold_return, effective_event_day, next_trading_day

# Mon 2024-03-04 .. Fri 2024-03-08, then Mon 2024-03-11. Weekend in between.
CAL = pd.DatetimeIndex(pd.to_datetime(
    ["2024-03-04", "2024-03-05", "2024-03-06", "2024-03-07", "2024-03-08",
     "2024-03-11", "2024-03-12", "2024-03-13", "2024-03-14", "2024-03-15"]
))


def utc(s):
    return pd.Timestamp(s, tz="UTC")


def test_morning_filing_trades_same_day():
    # 2024-03-05 11:00 UTC = 06:00 ET, before the open
    day0 = effective_event_day(pd.Timestamp("2024-03-05"), utc("2024-03-05 11:00"), CAL)
    assert day0 == pd.Timestamp("2024-03-05")


def test_after_close_filing_rolls_to_next_day():
    # 2024-03-05 21:30 UTC = 16:30 ET, after the close but before EDGAR's cutoff,
    # so EDGAR still stamps it 2024-03-05.
    day0 = effective_event_day(pd.Timestamp("2024-03-05"), utc("2024-03-05 21:30"), CAL)
    assert day0 == pd.Timestamp("2024-03-06")


def test_friday_evening_filing_rolls_over_the_weekend():
    # 2024-03-08 23:00 UTC = 18:00 ET Friday; EDGAR stamps it Monday 2024-03-11.
    day0 = effective_event_day(pd.Timestamp("2024-03-11"), utc("2024-03-08 23:00"), CAL)
    assert day0 == pd.Timestamp("2024-03-11")


def test_non_trading_day_rolls_forward():
    day0 = effective_event_day(pd.Timestamp("2024-03-09"), utc("2024-03-09 14:00"), CAL)
    assert day0 == pd.Timestamp("2024-03-11")


def test_off_the_end_of_the_calendar_returns_none():
    assert effective_event_day(pd.Timestamp("2024-04-01"), utc("2024-04-01 14:00"), CAL) is None


# --- helpers that already work -------------------------------------------------
def test_next_trading_day():
    assert next_trading_day(pd.Timestamp("2024-03-09"), CAL) == pd.Timestamp("2024-03-11")
    assert next_trading_day(pd.Timestamp("2024-03-11"), CAL) == pd.Timestamp("2024-03-11")


def test_buy_and_hold_return_uses_the_prior_close():
    px = pd.Series([100.0, 110.0, 121.0, 121.0], index=CAL[:4])
    got = buy_and_hold_return(px, CAL[1], CAL[2])   # 100 -> 121
    assert got == pytest.approx(0.21)
