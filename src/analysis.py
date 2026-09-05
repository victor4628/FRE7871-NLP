"""The exhibits you have to produce, in the order the paper produces them.

Two sentiment dimensions run through all of them, and they are not the same thing:

  NEGATIVE SENTIMENT     how bad the news is.
                         Two competing lists, H4N-Inf and Fin-Neg. Tested against
                         the filing-period return, because bad news should move
                         the price down.

  UNCERTAINTY SENTIMENT  how sure management is.
                         One list, Fin-Unc: approximate, contingency, depend,
                         fluctuate, indefinite, uncertain, variability. Tested
                         against the return AND against realised volatility after
                         the filing, because hedged language is a statement about
                         the width of the distribution, not its mean.

A filing can be full of uncertainty words and no negative words. "Results may
fluctuate depending on factors beyond our control" is not bad news; it is a
refusal to make a claim. Keep the two measures separate the whole way through and
do not collapse them into one "sentiment score".

Every function here is a TODO. The docstrings are the specification. Read them as
assignment text, not as hints.
"""

from __future__ import annotations

import pandas as pd


def table_summary_statistics(panel: pd.DataFrame) -> pd.DataFrame:
    """Table 2 - the analogue of LM Table II.

    Mean, median and standard deviation of every word-list proportion, plus the
    event-period excess return, the post-filing volatility and the controls.
    Report the 10-K column and the 10-Q column separately, so a reader can see
    whether quarterlies use language differently from annuals.

    LM's 10-K figures, for comparison: Fin-Neg 1.39%, Fin-Unc 1.20%, H4N-Inf
    3.79%. Note that uncertainty language is nearly as common as negative
    language, and considerably more common than positive language.

    TODO(student).
    """
    raise NotImplementedError


def table_top_words(
    counts_by_doc: pd.Series,
    word_list: set[str],
    n: int = 30,
) -> pd.DataFrame:
    """Table 3 - the analogue of LM Table III, and the heart of the paper.

    For one word list, the n most frequent words across the corpus, each with its
    share of that list's total count and the running cumulative share.

    Produce three panels: H4N-Inf, Fin-Neg, and Fin-Unc.

    Panels A and B carry the paper's argument. If your H4N-Inf panel is topped by
    TAX, COSTS, CAPITAL, LIABILITY and FOREIGN, you have reproduced the finding
    that gives the paper its title: those words are not negative in a filing, they
    are the vocabulary of accounting.

    Panel C is yours to interpret. Look at what actually drives the uncertainty
    count and ask the same question of it that LM asked of the Harvard list: are
    these words measuring management's genuine hedging, or are they the fixed
    furniture of a risk-factor section that every filer copies forward? A word
    appearing in 99% of filings carries no cross-sectional information whatever
    its meaning, which is the entire motivation for the tf.idf weighting.

    TODO(student).
    """
    raise NotImplementedError


def figure_quintile_returns(
    panel: pd.DataFrame,
    score_columns: list[str],
    return_column: str = "excess_ret_0_3",
):
    """Figure 1 - the analogue of LM Figure 1.

    Sort filings into five bins by tone and plot the MEDIAN [0,+3] excess return
    per bin. Three lines: H4N-Inf, Fin-Neg and Fin-Unc. Median, not mean: event
    returns have fat tails and LM use the median for exactly that reason.

    Sort within calendar quarter, not pooled, unless you can argue otherwise.
    Pooled quintiles mix a 2021 filing with a 2025 filing and let a time trend in
    the tone measure masquerade as a cross-sectional result.

    TODO(student). Return the matplotlib Axes and save the figure under outputs/.
    """
    raise NotImplementedError


def figure_quintile_volatility(
    panel: pd.DataFrame,
    score_column: str = "prop_Uncertainty",
    volatility_column: str = "post_vol",
):
    """Figure 2 - the uncertainty counterpart to Figure 1.

    Same five bins, but plot median realised volatility over days [+4,+63]
    instead of the event return. Add the pre-filing volatility as a second line
    on the same axes.

    The second line is the point of the exhibit. Uncertain language and volatile
    stocks go together for the obvious reason: volatile companies write hedged
    filings. If the two lines have the same slope, your uncertainty measure has
    told you nothing you did not already know from the price. Only the gap
    between them is a text signal.

    TODO(student).
    """
    raise NotImplementedError


def table_regressions(panel: pd.DataFrame) -> pd.DataFrame:
    """Table 4 - the analogue of LM Table IV. Negative sentiment and returns.

    Dependent variable: the day [0,+3] excess return, in percent.
    Six columns:
        (1) H4N-Inf,  proportional weights
        (2) Fin-Neg,  proportional weights
        (3) Fin-Unc,  proportional weights
        (4) H4N-Inf,  tf.idf weights
        (5) Fin-Neg,  tf.idf weights
        (6) Fin-Unc,  tf.idf weights
    Controls in every column: log_size, log_dollar_vol, pre_excess_ret, is_10k,
    plus calendar-quarter fixed effects.

    Then run one more specification with Fin-Neg and Fin-Unc entered TOGETHER.
    The two are correlated, so a univariate uncertainty coefficient may be
    picking up negativity. Report the correlation between them and say which of
    the two survives when both are in the regression.

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


def table_volatility_regressions(panel: pd.DataFrame) -> pd.DataFrame:
    """Table 5 - uncertainty sentiment and what happens after the filing.

    LM do not only test returns; they link their word lists to subsequent return
    volatility. This is where the uncertainty list should earn its keep, and it is
    a better-powered test than Table 4 because volatility is far more persistent
    than returns.

    Dependent variable: annualised realised volatility of daily excess returns
    over days [+4,+63], so the event window itself is excluded.

    Columns: Fin-Unc proportional, Fin-Unc tf.idf, Fin-Neg proportional, and one
    column with both.

    The control that decides whether this exhibit means anything is
    PRE-FILING VOLATILITY over days [-60,-6]. Without it you will find a large,
    significant uncertainty coefficient and it will be worthless: hedged language
    and volatile stocks are the same companies. With it, you are asking whether
    the language predicts a CHANGE in volatility, which is a real question.
    Report the regression both with and without that control, and explain the
    difference between the two numbers. That difference is the result.

    Same clustering as Table 4.

    TODO(student).
    """
    raise NotImplementedError


def power_check(lm_tstat: float, lm_n: int, your_n: int) -> dict:
    """Question 6 - what t-statistic should you expect before you look?

    A t-statistic scales roughly with the square root of the sample size. If LM
    found t = -2.64 on 50,115 filings, the same underlying effect in a sample of
    n filings should show up at about

        t_expected = t_LM * sqrt(n / 50115)

    Compute this for your sample size BEFORE you run Table 4, and put the number
    in your report. Do it first. It changes how you are entitled to read whatever
    you get.

    Apply the same arithmetic to Table 5 and notice that it comes out differently.
    Volatility is persistent and predictable in a way four-day returns are not, so
    the volatility test has real power at this sample size even though the return
    test does not. Say which of your two results you actually believe, and why.

    TODO(student). Return a dict with t_expected and the implied detectable
    effect size, and say in one sentence what it means for your conclusion.
    """
    raise NotImplementedError
