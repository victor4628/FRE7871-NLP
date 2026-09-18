"""Compare Uncertainty quintiles under market-cap and signal weights."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "outputs/.matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.analysis_data import nominal_market_data
from src.portfolio_backtest import run_event_portfolios, quintile_performance_statistics

SOURCE = ROOT / "outputs/investment_research/portfolio_trial_report_sample"
DEST = ROOT / "outputs/investment_research/portfolio_weighting_report_sample"


def known_market_caps(events, adjusted_open):
    """Latest public filing shares times last observed nominal closing price.

    Shares and prices use the same historical split units. Filing share counts
    become available only at their eligible trading open, never at the earlier
    cover-page share measurement date.
    """
    price_dir = ROOT / "data/prices"
    close = pd.read_csv(price_dir / "close_split_adjusted.csv", index_col=0, parse_dates=True)
    volume = pd.read_csv(price_dir / "volume_split_adjusted.csv", index_col=0, parse_dates=True)
    splits = pd.read_csv(price_dir / "stock_splits.csv", index_col=0, parse_dates=True)
    nominal, _, ratios = nominal_market_data(close, volume, splits)
    dates = pd.DatetimeIndex(adjusted_open.index)
    caps = pd.DataFrame(index=dates, columns=adjusted_open.columns, dtype=float)
    for ticker, filings in events.groupby("ticker"):
        filings = filings.sort_values(["effective_open", "acceptance_ts", "accession"])
        cumulative = ratios[ticker].cumprod()
        basis = []
        for row in filings.itertuples():
            asof = pd.Timestamp(row.shares_date)
            if asof > pd.Timestamp(row.effective_open):
                raise ValueError(f"Future-dated share count for {row.accession}")
            factor = cumulative.asof(asof)
            if pd.isna(factor):
                factor = 1.0
            basis.append(float(row.shares_used) / factor)
        updates = pd.Series(basis, index=pd.DatetimeIndex(filings.effective_open))
        updates = updates.loc[~updates.index.duplicated(keep="last")].sort_index()
        known_basis = updates.reindex(updates.index.union(dates)).ffill().reindex(dates)
        prior_price = nominal[ticker].reindex(dates).ffill().shift(1)
        prior_split_factor = cumulative.reindex(dates).ffill().shift(1)
        caps[ticker] = known_basis * prior_split_factor * prior_price
    return caps


def plot(paths, weighting, output):
    title = {
        "market_cap": "Uncertainty portfolios: market-cap weights within each quintile",
        "score": "Uncertainty portfolios: signal weights within each quintile",
    }[weighting]
    colors = ["#254C45", "#507D61", "#8B9D55", "#9A744F", "#473F52"]
    fig, ax = plt.subplots(figsize=(11, 6.2))
    for q, color in zip(range(1, 6), colors):
        sample = paths.loc[paths.quintile.eq(q)]
        label = f"Q{q}" + (" (Low)" if q == 1 else " (High)" if q == 5 else "")
        ax.plot(sample.date, sample.nav, label=label, color=color, linewidth=2)
    ax.axhline(1, color="#94A3B8", linestyle="--", linewidth=0.9)
    ax.set_title(title, loc="left", color="#254C45", weight="bold", fontsize=14)
    ax.set_ylabel("Cumulative value of $1")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(ncol=5, loc="upper left", frameon=False)
    note = (
        "Market-cap weights use the latest public filing share count and prior close, aligned for splits."
        if weighting == "market_cap" else
        "Signal weights are proportional to the existing adjusted Uncertainty TF-IDF percentile within each group."
    )
    fig.text(0.01, 0.025, note, fontsize=8.5, color="#374151")
    fig.text(0.01, 0.007,
             "Same 1,536-filing report sample and event-open rebalancing as the equal-weight version. Gross adjusted stock returns; no fees.",
             fontsize=8.5, color="#374151")
    fig.tight_layout(rect=[0, 0.055, 1, 1])
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(SOURCE / "point_in_time_filing_signals.csv",
                         dtype={"accession": str, "cik": str})
    events["effective_open"] = pd.to_datetime(events.effective_open)
    events["acceptance_ts"] = pd.to_datetime(events.acceptance_ts, utc=True)
    opens = pd.read_csv(SOURCE / "adjusted_open.csv", index_col=0, parse_dates=True)
    closes = pd.read_csv(SOURCE / "adjusted_close.csv", index_col=0, parse_dates=True)
    # Changing the allocation code must leave the original equal-weight paths intact.
    equal_paths, _ = run_event_portfolios(events, opens, closes, "uncertainty")
    saved = pd.read_csv(SOURCE / "portfolio_daily_paths.csv", parse_dates=["date"])
    saved = saved.loc[saved.signal.eq("uncertainty")]
    merged = equal_paths.merge(saved, on=["date", "signal", "quintile"],
                               suffixes=("_new", "_saved"), validate="one_to_one")
    if len(merged) != len(saved) or not np.allclose(merged.nav_new, merged.nav_saved, rtol=1e-12, atol=1e-12):
        raise RuntimeError("Equal-weight results changed unexpectedly")
    caps = known_market_caps(events, opens)
    caps.to_csv(DEST / "known_market_caps.csv")
    statistics = []
    for weighting in ["market_cap", "score"]:
        paths, constituents = run_event_portfolios(
            events, opens, closes, "uncertainty", weighting=weighting, market_caps=caps
        )
        paths.to_csv(DEST / f"{weighting}_daily_paths.csv", index=False)
        constituents.to_csv(DEST / f"{weighting}_latest_constituents.csv", index=False)
        stats = quintile_performance_statistics(paths)
        stats.insert(0, "weighting", weighting)
        statistics.append(stats)
        plot(paths, weighting, DEST / f"uncertainty_{weighting}_portfolios.png")
    pd.concat(statistics).to_csv(DEST / "performance.csv", index=False)
    (DEST / "manifest.json").write_text(json.dumps({
        "source": str(SOURCE.relative_to(ROOT)),
        "signal": "Uncertainty adjusted point-in-time TF-IDF percentile",
        "grouping": "Unchanged quintile assignments; 10-K and 10-Q combined",
        "market_cap": "Latest publicly available filing shares, split-aligned, times prior observed nominal close",
        "score_weights": "Adjusted percentile divided by the group percentile sum; equal weights only if all scores are zero",
        "execution": "Same filing-event eligible opens as original; weights drift between rebalances",
        "fees": "None",
        "equal_weight_reproduction": "Passed: all saved daily NAV observations reproduced",
        "limitations": "Same report-selected sample and survivorship limitation as first version",
    }, indent=2), encoding="utf-8")
    print(pd.concat(statistics).to_string(index=False))


if __name__ == "__main__":
    main()
