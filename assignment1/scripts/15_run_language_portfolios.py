"""Build trial Negative and Uncertainty filing-language portfolios."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import exchange_calendars as xcals
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "outputs" / ".matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analysis_data import ANALYSIS, load_text_data  # noqa: E402
from src.config import OUTPUT_DIR, PRICE_DIR  # noqa: E402
from src.portfolio_backtest import (  # noqa: E402
    SIGNALS,
    effective_open_date,
    long_short_comparison,
    performance_statistics,
    point_in_time_tfidf,
    prepare_portfolio_filings,
    quintile_performance_statistics,
    run_event_portfolios,
    turnover_statistics,
    two_stage_historical_percentiles,
)


DEFAULT_TRIAL = OUTPUT_DIR / "investment_research" / "portfolio_trial_no_lookahead"
ALL_FILINGS_TRIAL = OUTPUT_DIR / "investment_research" / "portfolio_trial_all_filings_no_lookahead"
REPORT_SAMPLE_TRIAL = OUTPUT_DIR / "investment_research" / "portfolio_trial_report_sample"


def download_adjusted_prices(
    tickers: list[str], trial: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    import yfinance as yf

    cache = trial / "yf_cache"
    cache.mkdir(parents=True, exist_ok=True)
    yf.set_tz_cache_location(str(cache))
    raw = yf.download(
        sorted(set(tickers)),
        start="2021-01-01",
        end="2026-01-06",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if not isinstance(raw.columns, pd.MultiIndex):
        raise RuntimeError("Expected multi-ticker OHLC response")
    adjusted_open = raw["Open"].sort_index().dropna(how="all")
    adjusted_close = raw["Close"].sort_index().dropna(how="all")
    usable = adjusted_open.notna().any() & adjusted_close.notna().any()
    required_usable = min(25, len(set(tickers)))
    if adjusted_open.empty or int(usable.sum()) < required_usable:
        raise RuntimeError("Adjusted Open/Close download returned too few usable tickers")
    adjusted_open.to_csv(trial / "adjusted_open.csv")
    adjusted_close.to_csv(trial / "adjusted_close.csv")
    return adjusted_open, adjusted_close


def load_adjusted_prices(
    tickers: list[str], trial: Path, refresh: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reuse the audited local cache and download only genuinely missing names."""
    open_path = trial / "adjusted_open.csv"
    close_path = trial / "adjusted_close.csv"
    if refresh:
        return download_adjusted_prices(tickers, trial)
    if open_path.exists() and close_path.exists():
        adjusted_open = pd.read_csv(open_path, index_col=0, parse_dates=True)
        adjusted_close = pd.read_csv(close_path, index_col=0, parse_dates=True)
    elif trial == REPORT_SAMPLE_TRIAL and (
        (ALL_FILINGS_TRIAL / "adjusted_open.csv").exists()
        and (ALL_FILINGS_TRIAL / "adjusted_close.csv").exists()
    ):
        adjusted_open = pd.read_csv(
            ALL_FILINGS_TRIAL / "adjusted_open.csv", index_col=0, parse_dates=True
        )
        adjusted_close = pd.read_csv(
            ALL_FILINGS_TRIAL / "adjusted_close.csv", index_col=0, parse_dates=True
        )
    elif trial != DEFAULT_TRIAL and (
        (DEFAULT_TRIAL / "adjusted_open.csv").exists()
        and (DEFAULT_TRIAL / "adjusted_close.csv").exists()
    ):
        adjusted_open = pd.read_csv(
            DEFAULT_TRIAL / "adjusted_open.csv", index_col=0, parse_dates=True
        )
        adjusted_close = pd.read_csv(
            DEFAULT_TRIAL / "adjusted_close.csv", index_col=0, parse_dates=True
        )
    else:
        return download_adjusted_prices(tickers, trial)

    missing = sorted(
        set(tickers).difference(adjusted_open.columns)
        | set(tickers).difference(adjusted_close.columns)
    )
    if missing:
        extra_open, extra_close = download_adjusted_prices(missing, trial)
        adjusted_open = adjusted_open.drop(columns=missing, errors="ignore").join(
            extra_open, how="outer"
        ).sort_index()
        adjusted_close = adjusted_close.drop(columns=missing, errors="ignore").join(
            extra_close, how="outer"
        ).sort_index()
    adjusted_open.to_csv(open_path)
    adjusted_close.to_csv(close_path)
    return adjusted_open, adjusted_close


def plot_paths(
    paths: pd.DataFrame, signal: str, output: Path, sample_label: str = ""
) -> None:
    labels = {
        "negative": "Negative language",
        "uncertainty": "Uncertainty language",
    }
    colors = ["#B7D4EA", "#75ACD0", "#3B7FB1", "#20527D", "#0B263F"]
    fig, ax = plt.subplots(figsize=(11, 6.2))
    for quintile, color in zip(range(1, 6), colors):
        sample = paths.loc[paths["quintile"].eq(quintile)]
        direction = "Low" if quintile == 1 else "High" if quintile == 5 else ""
        label = f"Q{quintile}" + (f" ({direction})" if direction else "")
        ax.plot(sample["date"], sample["nav"], label=label, color=color, linewidth=2)
    ax.axhline(1, color="#94A3B8", linewidth=1, linestyle="--")
    title = f"{labels[signal]} TF-IDF percentile portfolios"
    if sample_label:
        title += f" — {sample_label}"
    ax.set_title(title, loc="left", weight="bold", fontsize=15)
    ax.set_ylabel("Cumulative value of $1")
    ax.set_xlabel("")
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(ncol=5, frameon=False, loc="upper left")
    fig.text(
        0.01, 0.01,
        "TF-IDF is converted first to a same-form historical percentile and then to a same-filing-quarter historical percentile. "
        "Portfolios rebalance at the first eligible market open and use adjusted stock returns.",
        fontsize=8.5, color="#475569",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_long_short_comparison(
    comparison: pd.DataFrame, output: Path, sample_label: str = ""
) -> None:
    fig, ax = plt.subplots(figsize=(11, 6.2))
    styles = [
        ("Q1_minus_Q5_index", "Uncertainty Q1 − Q5", "#0B263F", 2.6),
        ("SPY_index", "SPY", "#3B82F6", 1.9),
        ("ARKK_index", "ARKK", "#E76F51", 1.9),
    ]
    for column, label, color, width in styles:
        ax.plot(comparison["date"], comparison[column], label=label, color=color, linewidth=width)
    ax.axhline(1, color="#94A3B8", linewidth=1, linestyle="--")
    title = "Low-minus-high uncertainty portfolio"
    if sample_label:
        title += f" — {sample_label}"
    ax.set_title(title, loc="left", weight="bold", fontsize=15)
    ax.set_ylabel("Cumulative return index (start = 1)")
    ax.set_xlabel("")
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    fig.text(
        0.01, 0.01,
        "The strategy is long Q1 (lowest adjusted Uncertainty TF-IDF percentile) and short Q5 (highest). "
        "Daily spread return is Q1 minus Q5; SPY and ARKK use adjusted close-to-close returns. No trading costs.",
        fontsize=8.5, color="#475569",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_long_short_only(
    comparison: pd.DataFrame, output: Path, signal: str, sample_label: str = ""
) -> None:
    signal_title = signal.title()
    fig, ax = plt.subplots(figsize=(11, 6.2))
    ax.plot(
        comparison["date"], comparison["Q1_minus_Q5_index"],
        color="#0B263F", linewidth=2.6, label=f"{signal_title} Q1 - Q5",
    )
    ax.axhline(1, color="#94A3B8", linewidth=1, linestyle="--")
    title = f"Low-minus-high {signal} portfolio"
    if sample_label:
        title += f" - {sample_label}"
    ax.set_title(title, loc="left", weight="bold", fontsize=15)
    ax.set_ylabel("Cumulative return index (start = 1)")
    ax.set_xlabel("")
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    fig.text(
        0.01, 0.01,
        f"Long Q1 (lowest adjusted {signal_title} TF-IDF percentile) and short Q5 (highest). "
        "Daily return is Q1 minus Q5. No benchmark and no trading costs.",
        fontsize=8.5, color="#475569",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_q1_benchmarks(
    paths: pd.DataFrame, benchmark_prices: pd.DataFrame, output: Path, sample_label: str = ""
) -> pd.DataFrame:
    """Compare net-of-cost Uncertainty Q1 with close-to-close benchmarks."""
    cost_rate = 0.001  # 10 basis points per 100% of one-way turnover.
    fig, ax = plt.subplots(figsize=(11, 6.2))
    sample = paths.loc[
        paths["signal"].eq("uncertainty") & paths["quintile"].eq(1)
    ].sort_values("date").copy()
    q1_dates = pd.DatetimeIndex(sample["date"])
    sample["net_return"] = (
        sample["daily_return"].fillna(0)
        - cost_rate * sample["one_way_turnover"].fillna(0)
    )
    # The comparison starts at the first portfolio close, so the first plotted
    # return is zero and no initial-formation cost is charged before that base.
    sample.iloc[0, sample.columns.get_loc("net_return")] = 0.0
    comparison = pd.DataFrame({"date": q1_dates})
    comparison["Uncertainty_Q1_net_return"] = sample["net_return"].to_numpy()
    comparison["Uncertainty_Q1_net_index"] = (
        1 + comparison["Uncertainty_Q1_net_return"]
    ).cumprod()
    ax.plot(
        comparison["date"], comparison["Uncertainty_Q1_net_index"],
        label="Uncertainty Q1 (net)", color="#6BAED6", linewidth=2.5,
    )
    prices = benchmark_prices.copy()
    prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
    prices = prices.reindex(q1_dates).ffill()
    for ticker, color in [("SPY", "#243B53"), ("ARKK", "#E76F51")]:
        index = prices[ticker] / prices[ticker].iloc[0]
        ax.plot(index.index, index, label=ticker, color=color, linewidth=1.9)
        comparison[f"{ticker}_index"] = index.to_numpy()
    ax.axhline(1, color="#94A3B8", linewidth=1, linestyle="--")
    title = "Uncertainty Q1 versus benchmarks, net of trading costs"
    if sample_label:
        title += f" - {sample_label}"
    ax.set_title(title, loc="left", weight="bold", fontsize=15)
    ax.set_ylabel("Cumulative value (first close = 1)")
    ax.set_xlabel("")
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left", ncol=3)
    fig.text(
        0.01, 0.01,
        "Uncertainty Q1 contains the lowest adjusted TF-IDF percentiles and deducts 10 basis points per 100% of one-way turnover. "
        "All series are normalized at the first portfolio close; SPY and ARKK use adjusted close prices.",
        fontsize=8.5, color="#475569",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return comparison


def plot_report_portfolio_pair(
    paths: pd.DataFrame, output: Path, sample_label: str = ""
) -> None:
    labels = {"negative": "Negative language", "uncertainty": "Uncertainty language"}
    colors = ["#B7D4EA", "#75ACD0", "#3B7FB1", "#20527D", "#0B263F"]
    fig, axes = plt.subplots(2, 1, figsize=(11, 8.4), sharex=True)
    for ax, signal in zip(axes, ["negative", "uncertainty"]):
        signal_paths = paths.loc[paths["signal"].eq(signal)]
        for quintile, color in zip(range(1, 6), colors):
            sample = signal_paths.loc[signal_paths["quintile"].eq(quintile)]
            direction = "Low" if quintile == 1 else "High" if quintile == 5 else ""
            label = f"Q{quintile}" + (f" ({direction})" if direction else "")
            ax.plot(sample["date"], sample["nav"], label=label, color=color, linewidth=1.8)
        ax.axhline(1, color="#94A3B8", linewidth=0.9, linestyle="--")
        ax.set_title(labels[signal], loc="left", weight="bold", fontsize=13)
        ax.set_ylabel("Value of $1")
        ax.grid(axis="y", color="#E2E8F0", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].legend(ncol=5, frameon=False, loc="upper left")
    title = "Filing-language quintile portfolios"
    if sample_label:
        title += f" - {sample_label}"
    fig.suptitle(title, x=0.08, ha="left", weight="bold", fontsize=16)
    fig.text(
        0.01, 0.01,
        "Q1 has the lowest adjusted point-in-time TF-IDF percentile and Q5 the highest. "
        "Equal-weight portfolios rebalance at eligible filing-event opens; returns are adjusted raw stock returns.",
        fontsize=8.3, color="#475569",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.96])
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-prices", action="store_true")
    parser.add_argument(
        "--include-shell", action="store_true",
        help="retain filing-time shell-company filings in the raw portfolio sample",
    )
    parser.add_argument(
        "--report-sample", action="store_true",
        help="use the assignment report's filtered 1,536-filing analysis sample",
    )
    args = parser.parse_args()
    if args.include_shell and args.report_sample:
        parser.error("--include-shell and --report-sample are mutually exclusive")
    if args.report_sample:
        trial = REPORT_SAMPLE_TRIAL
        sample_label = "assignment report sample"
    elif args.include_shell:
        trial = ALL_FILINGS_TRIAL
        sample_label = "all filings including shell"
    else:
        trial = DEFAULT_TRIAL
        sample_label = "non-shell filings"
    trial.mkdir(parents=True, exist_ok=True)

    # Use raw parsed filings. The assignment regression sample is unsuitable
    # here because it requires future 60-day returns and other outcome fields.
    if args.report_sample:
        corpus = pd.read_csv(
            ANALYSIS / "scored_text_corpus.csv", dtype={"cik": str, "accession": str}
        )
    else:
        metadata = pd.read_csv(
            ANALYSIS / "text_metadata.csv", dtype={"cik": str, "accession": str}
        )
        corpus = prepare_portfolio_filings(metadata, exclude_shell=not args.include_shell)
    _, counts, vocabulary = load_text_data()
    scored = point_in_time_tfidf(corpus, counts, vocabulary)
    scored = two_stage_historical_percentiles(scored)

    calendar = xcals.get_calendar("XNYS", start="2020-12-01", end="2026-01-10")
    sessions = pd.DatetimeIndex(calendar.sessions).tz_localize(None)
    scored["effective_open"] = scored["acceptance_ts"].map(
        lambda timestamp: effective_open_date(timestamp, sessions)
    )
    scored.to_csv(trial / "point_in_time_filing_signals.csv", index=False)

    tickers = sorted(scored["ticker"].dropna().unique())
    adjusted_open, adjusted_close = load_adjusted_prices(
        tickers, trial, refresh=args.refresh_prices
    )

    all_paths = []
    all_constituents = []
    for signal in SIGNALS:
        paths, constituents = run_event_portfolios(
            scored, adjusted_open, adjusted_close, signal=signal,
            start_date="2022-01-01", end_date="2025-12-31",
        )
        all_paths.append(paths)
        all_constituents.append(constituents)
        plot_paths(
            paths, signal, trial / f"{signal}_portfolio_returns.png", sample_label
        )

    paths = pd.concat(all_paths, ignore_index=True)
    constituents = pd.concat(all_constituents, ignore_index=True)
    latest_names = (
        scored.loc[pd.to_datetime(scored["effective_open"]).le(pd.Timestamp("2025-12-31"))]
        .sort_values(["ticker", "acceptance_ts", "accession"])
        .groupby("ticker", as_index=False)
        .tail(1)[["ticker", "company", "filing_date"]]
    )
    constituents = constituents.merge(latest_names, on="ticker", how="left", validate="many_to_one")
    paths.to_csv(trial / "portfolio_daily_paths.csv", index=False)
    constituents.to_csv(trial / "latest_portfolio_constituents.csv", index=False)

    summary_rows = []
    for (signal, quintile), sample in paths.groupby(["signal", "quintile"]):
        summary_rows.append({
            "signal": signal,
            "quintile": quintile,
            "start_date": sample["date"].min(),
            "end_date": sample["date"].max(),
            "starting_value": 1.0,
            "ending_value": sample.iloc[-1]["nav"],
            "total_return_pct": 100 * (sample.iloc[-1]["nav"] - 1),
            "average_holdings": sample["holdings"].mean(),
            "rebalance_days": int(sample["rebalanced"].sum()),
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(trial / "portfolio_summary.csv", index=False)
    quintile_performance = quintile_performance_statistics(paths)
    quintile_performance.to_csv(trial / "quintile_performance.csv", index=False)

    benchmark_prices = pd.read_csv(PRICE_DIR / "prices.csv", index_col=0, parse_dates=True)[["SPY", "ARKK"]]
    comparison = long_short_comparison(paths, benchmark_prices, signal="uncertainty")
    comparison.to_csv(trial / "uncertainty_long_short_daily.csv", index=False)
    performance = performance_statistics(comparison)
    performance.to_csv(trial / "uncertainty_long_short_performance.csv", index=False)
    turnover_daily, turnover_summary = turnover_statistics(paths, signal="uncertainty")
    turnover_daily.to_csv(trial / "uncertainty_turnover_daily.csv", index=False)
    turnover_summary.to_csv(trial / "uncertainty_turnover_summary.csv", index=False)
    turnover_by_year = turnover_daily.assign(
        year=pd.to_datetime(turnover_daily["date"]).dt.year
    ).groupby("year", as_index=False)[
        ["Q1_turnover", "Q5_turnover", "long_short_gross_normalized_turnover"]
    ].sum(min_count=1)
    for column in ["Q1_turnover", "Q5_turnover", "long_short_gross_normalized_turnover"]:
        turnover_by_year[column] *= 100
    turnover_by_year = turnover_by_year.rename(columns={
        "Q1_turnover": "Q1_annual_turnover_pct",
        "Q5_turnover": "Q5_annual_turnover_pct",
        "long_short_gross_normalized_turnover": "long_short_annual_turnover_pct",
    })
    turnover_by_year.to_csv(trial / "uncertainty_turnover_by_year.csv", index=False)
    plot_long_short_comparison(
        comparison, trial / "uncertainty_long_short_vs_spy_arkk.png", sample_label
    )
    if args.report_sample:
        plot_long_short_only(
            comparison, trial / "uncertainty_long_short_only.png", "uncertainty", sample_label
        )
        negative_comparison = long_short_comparison(paths, benchmark_prices, signal="negative")
        negative_comparison.to_csv(trial / "negative_long_short_daily.csv", index=False)
        performance_statistics(negative_comparison).to_csv(
            trial / "negative_long_short_performance.csv", index=False
        )
        plot_long_short_only(
            negative_comparison, trial / "negative_long_short_only.png", "negative", sample_label
        )
        plot_report_portfolio_pair(
            paths, trial / "report_portfolio_quintiles.png", sample_label
        )
        q1_comparison = plot_q1_benchmarks(
            paths, benchmark_prices, trial / "report_q1_vs_spy_arkk.png", sample_label
        )
        q1_comparison.to_csv(trial / "report_q1_net_vs_benchmarks.csv", index=False)

    extremes = constituents.loc[constituents["quintile"].isin([1, 5])].copy()
    extremes["portfolio"] = extremes["signal"].str.title() + extremes["quintile"].map({1: " low", 5: " high"})
    extremes["rank_from_extreme"] = 0
    low = extremes["quintile"].eq(1)
    extremes.loc[low, "rank_from_extreme"] = extremes.loc[low].groupby("signal")[
        "adjusted_percentile"
    ].rank(ascending=True, method="first")
    extremes.loc[~low, "rank_from_extreme"] = extremes.loc[~low].groupby("signal")[
        "adjusted_percentile"
    ].rank(ascending=False, method="first")
    extremes = extremes.sort_values(["signal", "quintile", "rank_from_extreme"])
    extremes.to_csv(trial / "latest_extreme_companies.csv", index=False)
    extremes.loc[extremes["rank_from_extreme"].le(3)].to_csv(
        trial / "latest_top_bottom_three.csv", index=False
    )

    manifest = {
        "trial_isolated_from_assignment_outputs": True,
        "source_filings": (
            "Assignment report's filtered 1,536-filing scored text corpus"
            if args.report_sample else
            "Raw parsed 10-K/10-Q metadata with filing-time text filters; shell filings retained"
            if args.include_shell else
            "Raw parsed 10-K/10-Q metadata with filing-time text and non-shell filters"
        ),
        "shell_filings_included": args.include_shell or args.report_sample,
        "future_outcome_filter_used": args.report_sample,
        "warmup_period": "2021",
        "portfolio_period": "2022-01-01 through 2025-12-31",
        "signals": ["Negative point-in-time TF-IDF", "Uncertainty point-in-time TF-IDF"],
        "adjustment": "Same-form historical percentile, then same-filing-quarter historical percentile",
        "execution": "Before-open filing: same-day open; otherwise next trading-day open",
        "return": "Adjusted raw stock return; no benchmark subtraction",
        "weighting": "Equal weight at each filing-event rebalance",
        "long_short": "For both Negative and Uncertainty, long Q1 low score and short Q5 high score; daily return is Q1 minus Q5",
        "benchmarks": "SPY and ARKK adjusted close-to-close returns",
        "sharpe_ratio": "Daily mean divided by daily standard deviation, annualized by square root of 252; risk-free rate set to zero",
        "turnover": "One-way 0.5 times the absolute weight change; initial formation excluded; long-short is gross-normalized average of both legs",
        "price_eligibility_at_rebalance": "Adjusted Open must be observable; same-day Close is not used for eligibility",
        "dictionary_timing": "All active Negative and Uncertainty entries were added by 2020; removed Negative entries were removed in 2020",
        "known_excluded_issue": "Survivorship bias intentionally not addressed for this trial",
        "rollback": f"Delete {trial.relative_to(OUTPUT_DIR.parent).as_posix()} and the trial-only backtest files",
    }
    (trial / "trial_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
