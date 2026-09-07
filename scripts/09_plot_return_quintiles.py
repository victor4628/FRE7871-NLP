"""Supplementary descriptive plot requested after the main analysis.

Sort the Table 6 sample into pooled negative-proportion quintiles. This is an
unadjusted median comparison, not a replacement for the controlled regression.
"""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "outputs/mpl_cache"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd


def main():
    directory = ROOT / "outputs/analysis"
    scored = pd.read_csv(ROOT / "data/interim/analysis/scored_text_corpus.csv")
    sample = pd.read_csv(ROOT / "data/interim/analysis/return_sample.csv")
    data = sample[["accession", "form", "excess_return"]].merge(
        scored[["accession", "negative_prop"]], on="accession", validate="one_to_one"
    )
    assert len(data) == len(sample) and data.notna().all().all()
    data["quintile"] = pd.qcut(data.negative_prop, 5, labels=False) + 1
    table = data.groupby("quintile").agg(
        n=("excess_return", "size"),
        min_negative_pct=("negative_prop", lambda x: 100*x.min()),
        max_negative_pct=("negative_prop", lambda x: 100*x.max()),
        mean_negative_pct=("negative_prop", lambda x: 100*x.mean()),
        median_return_pct=("excess_return", "median"),
        mean_return_pct=("excess_return", "mean"),
    )
    table.to_csv(directory / "return_quintiles.csv")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    ax.plot(table.index, table.median_return_pct, color="#193b58", marker="o",
            linewidth=2.3, markersize=7, label="Fin-Neg (LM negative list)")
    for q, row in table.iterrows():
        ax.annotate(f"{row.median_return_pct:.3f}%", (q, row.median_return_pct),
                    xytext=(0, 12), textcoords="offset points", ha="center")
    ax.set_xticks(range(1, 6), ["Low (Q1)", "Q2", "Q3", "Q4", "High (Q5)"])
    ax.set_xlim(.65, 5.35)
    ax.set_ylim(-1.85, .05)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.2f}%"))
    ax.set_ylabel("Median four-day excess return over SPY")
    ax.set_xlabel("Quintile based on proportion of negative words", labelpad=12)
    ax.set_title("Negative language and filing-period returns", loc="left",
                 fontweight="bold", pad=35)
    ax.text(0, 1.04, f"ARK filing sample, 2021-2025 | N = {len(data):,} | 10-K and 10-Q pooled",
            transform=ax.transAxes, fontsize=10, color="#52616d")
    ax.grid(axis="y", linestyle="--", alpha=.3)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower left", frameon=False, fontsize=10)
    fig.text(.12, .035, f"Unadjusted group medians; {table.n.min()}-{table.n.max()} filings per group. Connected points do not imply a fitted trend.\n"
             "Groups with more negative language have lower medians overall, but the five medians do not decrease monotonically.",
             fontsize=9, color="#52616d")
    fig.subplots_adjust(left=.12, right=.97, top=.81, bottom=.22)
    for extension in ["png", "svg"]:
        fig.savefig(directory / f"return_quintiles.{extension}", dpi=190)
    plt.close(fig)
    print(table.to_string())
    print("High-minus-low median (percentage points):",
          table.loc[5, "median_return_pct"]-table.loc[1, "median_return_pct"])


if __name__ == "__main__":
    main()
