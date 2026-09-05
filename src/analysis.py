"""The exhibits you have to produce, in the order the paper produces them.

Every function here is a TODO. The docstrings are the specification. Read them as
assignment text, not as hints.
"""

from __future__ import annotations

import pandas as pd


def table_summary_statistics(panel: pd.DataFrame) -> pd.DataFrame:
    """Table 2 - the analogue of LM Table II.

    Mean, median and standard deviation of every word-list proportion, plus the
    event-period excess return and the controls. Report the 10-K column and the
    10-Q column separately, so a reader can see whether quarterlies use language
    differently from annuals.

    TODO(student).
    """
    raise NotImplementedError


def table_top_words(
    counts_by_doc: pd.Series,
    word_list: set[str],
    n: int = 30,
) -> pd.DataFrame:
    """Table 3 - the analogue of LM Table III, and the heart of the paper.

    For one negative word list, the n most frequent words across the corpus, each
    with its share of that list's total negative word count and the running
    cumulative share. Produce it for H4N-Inf and for Fin-Neg.

    This is the table that shows the result. If your H4N-Inf column is topped by
    TAX, COSTS, CAPITAL, LIABILITY and FOREIGN, you have reproduced the finding
    that gives the paper its title: those words are not negative in a filing, they
    are the vocabulary of accounting.

    TODO(student).
    """
    raise NotImplementedError


def figure_quintile_returns(
    panel: pd.DataFrame,
    score_columns: list[str],
    return_column: str = "excess_ret_0_3",
):
    """Figure 1 - the analogue of LM Figure 1.

    Sort filings into five bins by each negative-tone measure and plot the MEDIAN
    filing-period excess return per bin. Median, not mean: event returns have fat
    tails and LM use the median for exactly that reason.

    Sort within calendar quarter, not pooled, unless you can argue otherwise.
    Pooled quintiles mix a 2021 filing with a 2025 filing and let a time trend in
    the tone measure masquerade as a cross-sectional result.

    TODO(student). Return the matplotlib Axes and save the figure under outputs/.
    """
    raise NotImplementedError


def table_regressions(panel: pd.DataFrame) -> pd.DataFrame:
    """Table 4 - the analogue of LM Table IV.

    Dependent variable: the day [0,+3] excess return, in percent.
    Four columns, matching the paper:
        (1) H4N-Inf, proportional weights
        (2) Fin-Neg,  proportional weights
        (3) H4N-Inf, tf.idf weights
        (4) Fin-Neg,  tf.idf weights
    Controls in every column: log_size, log_dollar_vol, pre_excess_ret, is_10k,
    plus calendar-quarter fixed effects.

    Standard errors: cluster by firm AND by filing date. Filings pile up on a
    handful of dates each quarter, so date clustering is not optional here.
    In statsmodels: .fit(cov_type="cluster", cov_kwds={"groups": ...}), passing a
    two-column array for two-way clustering.

    Fama-MacBeth by quarter with Newey-West lag 1, as in the paper, earns extra
    credit. With 20 quarters it is a weak estimator, which is itself worth a
    sentence in your report.

    Report coefficients and t-statistics. Standardising the tone measures to mean
    zero and unit variance gives coefficients you can interpret; say so if you do.

    TODO(student).
    """
    raise NotImplementedError


def power_check(lm_tstat: float, lm_n: int, your_n: int) -> dict:
    """Question 5 - what t-statistic should you expect before you look?

    A t-statistic scales roughly with the square root of the sample size. If LM
    found t = -2.64 on 50,115 filings, the same underlying effect in a sample of
    n filings should show up at about

        t_expected = t_LM * sqrt(n / 50115)

    Compute this for your sample size BEFORE you run Table 4, and put the number
    in your report. Do it first. It changes how you are entitled to read whatever
    you get.

    TODO(student). Return a dict with t_expected and the implied detectable
    effect size, and say in one sentence what it means for your conclusion.
    """
    raise NotImplementedError
