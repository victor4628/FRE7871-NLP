import numpy as np
import pandas as pd
import pytest

from src.portfolio_backtest import (
    assign_quintiles,
    effective_open_date,
    long_short_comparison,
    performance_statistics,
    point_in_time_tfidf,
    prepare_portfolio_filings,
    quintile_performance_statistics,
    run_event_portfolios,
    turnover_statistics,
)


def test_effective_open_respects_before_open_and_after_open_timing():
    sessions = pd.DatetimeIndex(["2025-02-25", "2025-02-26", "2025-02-27"])
    before_open = pd.Timestamp("2025-02-25 13:00:00+00:00")  # 08:00 Eastern
    after_open = pd.Timestamp("2025-02-25 15:00:00+00:00")   # 10:00 Eastern
    assert effective_open_date(before_open, sessions) == pd.Timestamp("2025-02-25")
    assert effective_open_date(after_open, sessions) == pd.Timestamp("2025-02-26")


def test_assign_quintiles_is_complete_and_nearly_equal():
    scores = {f"T{i:02d}": float(i) for i in range(27)}
    groups = assign_quintiles(scores, set(scores))
    assert set().union(*map(set, groups.values())) == set(scores)
    assert max(map(len, groups.values())) - min(map(len, groups.values())) <= 1
    assert "T00" in groups[1]
    assert "T26" in groups[5]


def test_assign_quintiles_requires_five_meaningful_groups():
    scores = {f"T{i:02d}": float(i) for i in range(24)}
    assert assign_quintiles(scores, set(scores)) == {}


def test_future_document_does_not_change_earlier_point_in_time_score():
    base = pd.DataFrame([
        {"accession": "a", "acceptance_datetime": "2021-01-01T12:00:00Z", "text_row": 0,
         "analysis_words": 10, "analysis_distinct": 1, "form": "10-Q", "ticker": "A"},
        {"accession": "b", "acceptance_datetime": "2021-02-01T12:00:00Z", "text_row": 1,
         "analysis_words": 10, "analysis_distinct": 1, "form": "10-Q", "ticker": "B"},
    ])
    counts = np.array([[0], [1], [1]])
    first = point_in_time_tfidf(base, counts, ["LOSS"]).set_index("accession")
    future = pd.concat([
        base,
        pd.DataFrame([{"accession": "c", "acceptance_datetime": "2021-03-01T12:00:00Z",
                       "text_row": 2, "analysis_words": 10, "analysis_distinct": 1,
                       "form": "10-Q", "ticker": "C"}]),
    ], ignore_index=True)
    second = point_in_time_tfidf(future, counts, ["LOSS"]).set_index("accession")
    assert second.loc["b", "negative_tfidf_pit"] == pytest.approx(
        first.loc["b", "negative_tfidf_pit"]
    )


def test_event_portfolio_earns_returns_of_its_assigned_quintile():
    tickers = [f"T{i:02d}" for i in range(25)]
    events = pd.DataFrame({
        "ticker": tickers,
        "accession": [f"a{i:02d}" for i in range(25)],
        "acceptance_ts": pd.to_datetime(["2021-12-30T12:00:00Z"] * 25),
        "effective_open": pd.to_datetime(["2021-12-31"] * 25),
        "negative_adjusted_percentile": np.arange(25, dtype=float),
    })
    dates = pd.DatetimeIndex(["2022-01-03", "2022-01-04"])
    adjusted_open = pd.DataFrame(100.0, index=dates, columns=tickers)
    adjusted_close = adjusted_open.copy()
    adjusted_close.loc["2022-01-03", tickers[-5:]] = 110.0
    adjusted_open.loc["2022-01-04", tickers[-5:]] = 110.0
    adjusted_close.loc["2022-01-04", tickers[-5:]] = 110.0
    paths, constituents = run_event_portfolios(
        events, adjusted_open, adjusted_close, "negative",
        start_date="2022-01-01", end_date="2022-01-04",
    )
    first_day = paths.loc[paths["date"].eq(pd.Timestamp("2022-01-03"))].set_index("quintile")
    assert first_day.loc[5, "nav"] == pytest.approx(1.1)
    assert first_day.loc[1, "nav"] == pytest.approx(1.0)
    assert set(constituents.loc[constituents["quintile"].eq(5), "ticker"]) == set(tickers[-5:])


def test_portfolio_filing_filter_does_not_require_future_outcomes():
    metadata = pd.DataFrame([
        {"accession": "a", "acceptance_datetime": "2022-01-01T12:00:00Z", "form": "10-Q",
         "analysis_words": 1500, "shell_company": False},
        {"accession": "b", "acceptance_datetime": "2022-01-01T12:00:00Z", "form": "10-Q",
         "analysis_words": 1500, "shell_company": True},
    ])
    result = prepare_portfolio_filings(metadata)
    assert result["accession"].tolist() == ["a"]
    result_with_shell = prepare_portfolio_filings(metadata, exclude_shell=False)
    assert result_with_shell["accession"].tolist() == ["a", "b"]


def test_long_short_return_and_turnover_statistics():
    dates = pd.DatetimeIndex(["2022-01-03", "2022-01-04", "2022-01-05"])
    rows = []
    q1_returns = [0.0, 0.02, -0.01]
    q5_returns = [0.0, -0.01, 0.01]
    for quintile, returns, turnovers in [
        (1, q1_returns, [np.nan, 0.20, 0.40]),
        (5, q5_returns, [np.nan, 0.40, 0.20]),
    ]:
        for date, daily_return, turnover in zip(dates, returns, turnovers):
            rows.append({
                "date": date, "signal": "uncertainty", "quintile": quintile,
                "daily_return": daily_return, "one_way_turnover": turnover,
                "rebalanced": True, "initial_formation": date == dates[0],
            })
    paths = pd.DataFrame(rows)
    benchmarks = pd.DataFrame({
        "SPY": [100.0, 101.0, 102.01],
        "ARKK": [100.0, 98.0, 98.0],
    }, index=dates)
    comparison = long_short_comparison(paths, benchmarks)
    assert comparison.loc[1, "Q1_minus_Q5_return"] == pytest.approx(0.03)
    assert comparison.loc[1, "Q1_minus_Q5_index"] == pytest.approx(1.03)
    assert comparison.loc[1, "SPY_return"] == pytest.approx(0.01)
    performance = performance_statistics(comparison)
    assert set(performance["series"]) == {"Q1_minus_Q5", "SPY", "ARKK"}

    daily, summary = turnover_statistics(paths)
    assert daily.loc[1, "long_short_gross_normalized_turnover"] == pytest.approx(0.30)
    spread = summary.loc[summary["portfolio"].str.startswith("Q1 minus")].iloc[0]
    assert spread["average_turnover_per_rebalance_pct"] == pytest.approx(30.0)


def test_quintile_performance_uses_nav_for_total_return_and_daily_returns_for_sharpe():
    paths = pd.DataFrame({
        "date": pd.to_datetime(["2022-01-03", "2022-01-04", "2022-01-05"]),
        "signal": ["negative"] * 3,
        "quintile": [1] * 3,
        "nav": [1.00, 1.10, 0.99],
        "daily_return": [0.00, 0.10, -0.10],
    })
    result = quintile_performance_statistics(paths).iloc[0]
    assert result["total_return_pct"] == pytest.approx(-1.0)
    assert result["maximum_drawdown_pct"] == pytest.approx(-10.0)
    assert result["observations"] == 3
