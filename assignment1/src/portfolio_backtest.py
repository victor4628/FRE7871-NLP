"""Point-in-time filing-language signals and event-driven quintile portfolios."""
from __future__ import annotations

import bisect
from collections import defaultdict

import numpy as np
import pandas as pd

from .lexicons import load_master_dictionary, lm_word_lists


SIGNALS = ("negative", "uncertainty")


def prepare_portfolio_filings(
    metadata: pd.DataFrame,
    exclude_shell: bool = True,
) -> pd.DataFrame:
    """Apply only filing-time eligibility rules, never future-return filters."""
    out = metadata.copy()
    out["acceptance_ts"] = pd.to_datetime(out["acceptance_datetime"], utc=True, errors="coerce")
    valid_length = (
        (out["form"].eq("10-K") & out["analysis_words"].ge(2_000))
        | (out["form"].eq("10-Q") & out["analysis_words"].ge(1_000))
    )
    keep = out["form"].isin(["10-K", "10-Q"]) & out["acceptance_ts"].notna()
    keep &= valid_length
    if exclude_shell:
        keep &= ~out["shell_company"].fillna(True).astype(bool)
    return out.loc[keep].sort_values(["acceptance_ts", "accession"]).reset_index(drop=True)


def point_in_time_tfidf(
    filings: pd.DataFrame,
    counts: np.ndarray,
    vocabulary: list[str],
) -> pd.DataFrame:
    """Calculate TF-IDF using only filings public by each acceptance timestamp.

    Filings accepted at the same timestamp enter the document-frequency corpus
    together, so their ordering within that timestamp cannot affect scores.
    """
    required = {
        "accession", "acceptance_datetime", "text_row", "analysis_words",
        "analysis_distinct", "form", "ticker",
    }
    missing = required.difference(filings.columns)
    if missing:
        raise ValueError(f"Missing filing columns: {sorted(missing)}")
    if not filings["accession"].is_unique:
        raise ValueError("Point-in-time TF-IDF requires unique filing accessions")

    out = filings.copy()
    out["acceptance_ts"] = pd.to_datetime(out["acceptance_datetime"], utc=True)
    out = out.sort_values(["acceptance_ts", "accession"]).copy()
    matrix = counts[out["text_row"].to_numpy(dtype=int)]
    master = load_master_dictionary()
    lists = lm_word_lists(master)
    masks = {
        signal: np.array([word in lists[signal.title()] for word in vocabulary])
        for signal in SIGNALS
    }
    scores = {signal: np.full(len(out), np.nan) for signal in SIGNALS}

    seen_documents = 0
    document_frequency = np.zeros(len(vocabulary), dtype=np.int64)
    acceptance_values = out["acceptance_ts"].to_numpy()
    start = 0
    while start < len(out):
        end = start + 1
        while end < len(out) and acceptance_values[end] == acceptance_values[start]:
            end += 1
        batch = matrix[start:end]
        seen_documents += len(batch)
        document_frequency += (batch > 0).sum(axis=0)
        idf = np.log(
            np.divide(
                seen_documents,
                document_frequency,
                out=np.ones(len(vocabulary), dtype=float),
                where=document_frequency > 0,
            )
        )
        log_tf = np.zeros_like(batch, dtype=float)
        np.log(batch, out=log_tf, where=batch > 0)
        log_tf = np.where(batch > 0, 1 + log_tf, 0)
        average = (
            out.iloc[start:end]["analysis_words"].to_numpy(dtype=float)
            / out.iloc[start:end]["analysis_distinct"].to_numpy(dtype=float)
        )
        weighted = log_tf * idf / (1 + np.log(average))[:, None]
        for signal in SIGNALS:
            scores[signal][start:end] = weighted[:, masks[signal]].sum(axis=1)
        start = end

    for signal in SIGNALS:
        out[f"{signal}_tfidf_pit"] = scores[signal]
    return out.reset_index(drop=True)


def two_stage_historical_percentiles(
    filings: pd.DataFrame,
    min_form_history: int = 20,
    min_quarter_history: int = 20,
) -> pd.DataFrame:
    """Adjust point-in-time TF-IDF for filing form and filing-season effects.

    Stage 1 ranks a score against strictly earlier filings of the same form.
    Stage 2 ranks that stage-1 percentile against strictly earlier filings in
    the same calendar filing quarter, after forms are already comparable.
    """
    required = {"accession", "acceptance_ts", "filing_date", "form"}
    required |= {f"{signal}_tfidf_pit" for signal in SIGNALS}
    missing = required.difference(filings.columns)
    if missing:
        raise ValueError(f"Missing percentile columns: {sorted(missing)}")

    out = filings.sort_values(["acceptance_ts", "accession"]).copy()
    out["filing_quarter_of_year"] = pd.to_datetime(out["filing_date"]).dt.quarter
    for signal in SIGNALS:
        out[f"{signal}_form_percentile"] = np.nan
        out[f"{signal}_adjusted_percentile"] = np.nan

    form_histories: dict[tuple[str, str], list[float]] = defaultdict(list)
    quarter_histories: dict[tuple[int, str], list[float]] = defaultdict(list)
    for _, same_time in out.groupby("acceptance_ts", sort=True):
        stage_one: dict[tuple[int, str], float] = {}
        for index, row in same_time.iterrows():
            for signal in SIGNALS:
                score = float(row[f"{signal}_tfidf_pit"])
                history = form_histories[(row["form"], signal)]
                if np.isfinite(score) and len(history) >= min_form_history:
                    position = bisect.bisect_right(history, score)
                    percentile = 100 * (position + 0.5) / (len(history) + 1)
                    out.at[index, f"{signal}_form_percentile"] = percentile
                    stage_one[(index, signal)] = percentile

        for index, row in same_time.iterrows():
            quarter = int(row["filing_quarter_of_year"])
            for signal in SIGNALS:
                percentile = stage_one.get((index, signal), np.nan)
                history = quarter_histories[(quarter, signal)]
                if np.isfinite(percentile) and len(history) >= min_quarter_history:
                    position = bisect.bisect_right(history, percentile)
                    out.at[index, f"{signal}_adjusted_percentile"] = (
                        100 * (position + 0.5) / (len(history) + 1)
                    )

        for index, row in same_time.iterrows():
            for signal in SIGNALS:
                score = float(row[f"{signal}_tfidf_pit"])
                if np.isfinite(score):
                    bisect.insort(form_histories[(row["form"], signal)], score)
                percentile = stage_one.get((index, signal), np.nan)
                if np.isfinite(percentile):
                    quarter = int(row["filing_quarter_of_year"])
                    bisect.insort(quarter_histories[(quarter, signal)], percentile)
    return out


def effective_open_date(acceptance, sessions: pd.DatetimeIndex) -> pd.Timestamp:
    """First eligible open under the daily-price timing convention.

    A filing accepted before 09:30 Eastern on a trading day is tradable at that
    day's open. Intraday, after-close, weekend and holiday filings are tradable
    at the next trading day's open.
    """
    local = pd.Timestamp(acceptance).tz_convert("America/New_York")
    local_date = local.tz_localize(None).normalize()
    session_dates = pd.DatetimeIndex(sessions).tz_localize(None).normalize()
    is_session = local_date in session_dates
    before_open = (local.hour, local.minute, local.second) < (9, 30, 0)
    side = "left" if is_session and before_open else "right"
    position = session_dates.searchsorted(local_date, side=side)
    if position >= len(session_dates):
        return pd.NaT
    return session_dates[position]


def assign_quintiles(signal_values: dict[str, float], eligible: set[str]) -> dict[int, list[str]]:
    """Create five near-equal deterministic portfolios from current scores."""
    ranked = sorted(
        ((ticker, value) for ticker, value in signal_values.items()
         if ticker in eligible and np.isfinite(value)),
        key=lambda item: (item[1], item[0]),
    )
    if len(ranked) < 25:
        return {}
    groups: dict[int, list[str]] = {quintile: [] for quintile in range(1, 6)}
    for position, (ticker, _) in enumerate(ranked):
        quintile = min(5, 1 + position * 5 // len(ranked))
        groups[quintile].append(ticker)
    return groups


def run_event_portfolios(
    events: pd.DataFrame,
    adjusted_open: pd.DataFrame,
    adjusted_close: pd.DataFrame,
    signal: str,
    start_date: str = "2022-01-01",
    end_date: str = "2025-12-31",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run five self-contained equal-weight portfolios rebalanced at event opens."""
    score_column = f"{signal}_adjusted_percentile"
    if score_column not in events:
        raise ValueError(f"Missing score column: {score_column}")
    open_px = adjusted_open.copy()
    close_px = adjusted_close.copy()
    open_px.index = pd.to_datetime(open_px.index).tz_localize(None).normalize()
    close_px.index = pd.to_datetime(close_px.index).tz_localize(None).normalize()
    sessions = open_px.index.intersection(close_px.index)
    sessions = sessions[(sessions >= pd.Timestamp(start_date)) & (sessions <= pd.Timestamp(end_date))]
    if sessions.empty:
        raise ValueError("No price sessions fall inside the requested portfolio period")
    open_px = open_px.reindex(sessions)
    close_px = close_px.reindex(sessions)

    valid_events = events.dropna(subset=[score_column, "effective_open"]).copy()
    valid_events["effective_open"] = pd.to_datetime(valid_events["effective_open"])
    valid_events = valid_events.sort_values(["effective_open", "acceptance_ts", "accession"])
    by_date = {date: group for date, group in valid_events.groupby("effective_open")}

    current_scores: dict[str, float] = {}
    for row in valid_events.loc[valid_events["effective_open"] < sessions[0]].itertuples():
        current_scores[row.ticker] = float(getattr(row, score_column))

    nav = {quintile: 1.0 for quintile in range(1, 6)}
    shares: dict[int, dict[str, float]] = {quintile: {} for quintile in range(1, 6)}
    memberships: dict[int, list[str]] = {quintile: [] for quintile in range(1, 6)}
    rows = []
    started = False
    pending_rebalance = False
    last_close = close_px.ffill(limit=5)

    for day in sessions:
        actual_open = open_px.loc[day]
        actual_close = close_px.loc[day]
        event_today = day in by_date
        if event_today:
            for row in by_date[day].itertuples():
                current_scores[row.ticker] = float(getattr(row, score_column))

        # Eligibility is decided at the rebalance open. Requiring a valid close
        # here would use information unavailable when the trade is made.
        eligible = set(actual_open.index[actual_open.notna()])
        new_groups = assign_quintiles(current_scores, eligible)
        pending_rebalance = pending_rebalance or event_today
        held = set().union(*(set(group) for group in memberships.values()))
        can_sell_at_open = all(np.isfinite(actual_open.get(ticker, np.nan)) for ticker in held)
        rebalance = pending_rebalance and bool(new_groups) and can_sell_at_open
        if not started and new_groups:
            rebalance = True
            started = True

        prior_nav = nav.copy()
        turnover_today = {quintile: 0.0 for quintile in range(1, 6)}
        initial_formation = {quintile: False for quintile in range(1, 6)}
        if rebalance:
            for quintile in range(1, 6):
                if shares[quintile]:
                    open_positions = {}
                    for ticker, units in shares[quintile].items():
                        price = actual_open.get(ticker, np.nan)
                        if not np.isfinite(price):
                            raise RuntimeError(f"Missing rebalance-open price for held ticker {ticker} on {day}")
                        open_positions[ticker] = units * price
                    open_value = sum(open_positions.values())
                    pretrade_weights = {
                        ticker: value / open_value for ticker, value in open_positions.items()
                    }
                else:
                    open_value = nav[quintile]
                    pretrade_weights = {}
                    initial_formation[quintile] = True
                memberships[quintile] = new_groups[quintile]
                target_weight = 1.0 / len(memberships[quintile])
                if pretrade_weights:
                    names = set(pretrade_weights) | set(memberships[quintile])
                    turnover_today[quintile] = 0.5 * sum(
                        abs(
                            (target_weight if ticker in memberships[quintile] else 0.0)
                            - pretrade_weights.get(ticker, 0.0)
                        )
                        for ticker in names
                    )
                else:
                    # Initial capital deployment is reported separately and is
                    # excluded from average rebalancing turnover.
                    turnover_today[quintile] = np.nan
                allocation = open_value / len(memberships[quintile])
                shares[quintile] = {
                    ticker: allocation / float(actual_open[ticker])
                    for ticker in memberships[quintile]
                }
            pending_rebalance = False

        if not started:
            continue
        for quintile in range(1, 6):
            close_value = 0.0
            for ticker, units in shares[quintile].items():
                price = actual_close.get(ticker, np.nan)
                if not np.isfinite(price):
                    price = actual_open.get(ticker, np.nan)
                if not np.isfinite(price):
                    prior_prices = last_close.loc[last_close.index < day, ticker].dropna()
                    if prior_prices.empty:
                        raise RuntimeError(f"No observable price for held ticker {ticker} on {day}")
                    price = prior_prices.iloc[-1]
                close_value += units * price
            nav[quintile] = close_value
            daily_return = nav[quintile] / prior_nav[quintile] - 1 if prior_nav[quintile] else np.nan
            rows.append({
                "date": day,
                "signal": signal,
                "quintile": quintile,
                "nav": nav[quintile],
                "daily_return": daily_return,
                "holdings": len(memberships[quintile]),
                "rebalanced": rebalance,
                "one_way_turnover": turnover_today[quintile],
                "initial_formation": initial_formation[quintile],
            })

    paths = pd.DataFrame(rows)
    latest_scores = pd.Series(current_scores, name="adjusted_percentile")
    last_day = sessions[-1]
    eligible = set(open_px.loc[last_day].dropna().index)
    final_groups = assign_quintiles(current_scores, eligible)
    constituents = []
    for quintile, tickers in final_groups.items():
        for ticker in tickers:
            constituents.append({
                "signal": signal,
                "quintile": quintile,
                "ticker": ticker,
                "adjusted_percentile": latest_scores[ticker],
            })
    return paths, pd.DataFrame(constituents)


def long_short_comparison(
    paths: pd.DataFrame,
    benchmark_prices: pd.DataFrame,
    signal: str = "uncertainty",
    low_quintile: int = 1,
    high_quintile: int = 5,
) -> pd.DataFrame:
    """Build a Q1-minus-Q5 return series and aligned benchmark return indexes.

    All series begin at the first portfolio close. The first row therefore has
    a zero return; subsequent benchmark returns are adjusted close-to-close.
    """
    sample = paths.loc[paths["signal"].eq(signal)].copy()
    returns = sample.pivot(index="date", columns="quintile", values="daily_return")
    needed = {low_quintile, high_quintile}
    if not needed.issubset(returns.columns):
        raise ValueError(f"Missing quintile returns: {sorted(needed.difference(returns.columns))}")
    result = pd.DataFrame(index=pd.DatetimeIndex(returns.index))
    result["Q1_minus_Q5_return"] = returns[low_quintile] - returns[high_quintile]

    prices = benchmark_prices.copy()
    prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
    for ticker in prices.columns:
        result[f"{ticker}_return"] = prices[ticker].pct_change(fill_method=None).reindex(result.index)

    # Start every plotted index from the same closing-date base of one.
    result.iloc[0] = 0.0
    for column in list(result.columns):
        result[column.replace("_return", "_index")] = (1 + result[column].fillna(0)).cumprod()
    result.index.name = "date"
    return result.reset_index()


def performance_statistics(comparison: pd.DataFrame) -> pd.DataFrame:
    """Annualized performance statistics using a zero risk-free rate."""
    rows = []
    return_columns = [column for column in comparison if column.endswith("_return")]
    for column in return_columns:
        returns = comparison[column].dropna()
        index_column = column.replace("_return", "_index")
        index = comparison.loc[returns.index, index_column]
        years = max(len(returns) / 252, 1 / 252)
        ending_value = float(index.iloc[-1])
        volatility = float(returns.std(ddof=1) * np.sqrt(252))
        sharpe = float(returns.mean() / returns.std(ddof=1) * np.sqrt(252))
        drawdown = index / index.cummax() - 1
        rows.append({
            "series": column.removesuffix("_return"),
            "total_return_pct": 100 * (ending_value - 1),
            "annualized_return_pct": 100 * (ending_value ** (1 / years) - 1),
            "annualized_volatility_pct": 100 * volatility,
            "sharpe_ratio_rf_0": sharpe,
            "maximum_drawdown_pct": 100 * float(drawdown.min()),
            "observations": len(returns),
        })
    return pd.DataFrame(rows)


def quintile_performance_statistics(paths: pd.DataFrame) -> pd.DataFrame:
    """Summarize each fully invested quintile using a zero risk-free rate."""
    rows = []
    for (signal, quintile), sample in paths.groupby(["signal", "quintile"], sort=True):
        sample = sample.sort_values("date")
        returns = sample["daily_return"].dropna()
        ending_value = float(sample.iloc[-1]["nav"])
        years = max(len(returns) / 252, 1 / 252)
        volatility = float(returns.std(ddof=1) * np.sqrt(252))
        sharpe = float(returns.mean() / returns.std(ddof=1) * np.sqrt(252))
        indexed = pd.concat([pd.Series([1.0]), sample["nav"].reset_index(drop=True)], ignore_index=True)
        drawdown = indexed / indexed.cummax() - 1
        rows.append({
            "signal": signal,
            "quintile": int(quintile),
            "total_return_pct": 100 * (ending_value - 1),
            "annualized_return_pct": 100 * (ending_value ** (1 / years) - 1),
            "annualized_volatility_pct": 100 * volatility,
            "sharpe_ratio_rf_0": sharpe,
            "maximum_drawdown_pct": 100 * float(drawdown.min()),
            "observations": len(returns),
        })
    return pd.DataFrame(rows)


def turnover_statistics(
    paths: pd.DataFrame,
    signal: str = "uncertainty",
    low_quintile: int = 1,
    high_quintile: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Summarize one-way turnover for both legs and the gross-normalized spread."""
    sample = paths.loc[paths["signal"].eq(signal)].copy()
    turnover = sample.pivot(index="date", columns="quintile", values="one_way_turnover")
    rebalanced = sample.pivot(index="date", columns="quintile", values="rebalanced")
    initial = sample.pivot(index="date", columns="quintile", values="initial_formation")
    dates = pd.DatetimeIndex(turnover.index)
    daily = pd.DataFrame(index=dates)
    daily["Q1_turnover"] = turnover[low_quintile]
    daily["Q5_turnover"] = turnover[high_quintile]
    daily["long_short_gross_normalized_turnover"] = (
        daily["Q1_turnover"] + daily["Q5_turnover"]
    ) / 2
    daily["rebalanced"] = rebalanced[low_quintile].astype(bool)
    daily["initial_formation"] = initial[low_quintile].astype(bool)
    daily.index.name = "date"

    rows = []
    for column, label in [
        ("Q1_turnover", "Q1 low uncertainty"),
        ("Q5_turnover", "Q5 high uncertainty"),
        ("long_short_gross_normalized_turnover", "Q1 minus Q5 (gross-normalized)"),
    ]:
        rebalance_values = daily.loc[
            daily["rebalanced"] & ~daily["initial_formation"], column
        ].dropna()
        annual_sample = daily.loc[~daily["initial_formation"], column]
        annual = annual_sample.groupby(annual_sample.index.year).sum(min_count=1)
        rows.append({
            "portfolio": label,
            "rebalances_excluding_initial": len(rebalance_values),
            "average_turnover_per_rebalance_pct": 100 * rebalance_values.mean(),
            "median_turnover_per_rebalance_pct": 100 * rebalance_values.median(),
            "average_annual_turnover_pct": 100 * annual.mean(),
        })
    return daily.reset_index(), pd.DataFrame(rows)
