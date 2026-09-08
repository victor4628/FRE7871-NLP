"""Pre-specified estimators and tables. Every model carries its own corpus ID."""
from __future__ import annotations

import hashlib
import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm
from scipy.linalg import qr
from scipy.stats import t, norm

from .analysis_data import score_corpus

TONES = ["negative_prop", "negative_tfidf", "uncertainty_prop", "uncertainty_tfidf"]


def corpus_id(frame):
    return hashlib.sha256("\n".join(sorted(frame.accession)).encode()).hexdigest()[:16]


def standardize(x):
    sd = x.std(ddof=1)
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("Cannot standardize a constant or invalid measure")
    return (x-x.mean())/sd


def clustered_fit(formula, data, two_way=False):
    groups = pd.factorize(data.cik)[0]
    if two_way:
        groups = np.column_stack([groups, pd.factorize(data.quarter)[0]])
    model = smf.ols(formula, data=data, missing="raise")
    # Nested fixed effects can create redundant dummy columns (especially when
    # annual filers always report in the same season). Remove only algebraic
    # redundancies, preserving the estimable tone/time coefficient.
    x = model.exog
    _, r, pivot = qr(x, mode="economic", pivoting=True)
    tol = max(x.shape)*np.finfo(float).eps*abs(r).max()
    rank = int((np.abs(np.diag(r)) > tol).sum())
    selected = sorted(pivot[:rank])
    dropped = [n for i,n in enumerate(model.exog_names) if i not in selected]
    if any(n in dropped for n in ["time", "time_years", "score_z"]):
        raise ValueError("Target coefficient is not identified by this design")
    if dropped:
        model = sm.OLS(pd.Series(model.endog,index=data.index),
                       pd.DataFrame(x[:,selected],index=data.index,
                                    columns=[model.exog_names[i] for i in selected]))
    result = model.fit(
        cov_type="cluster", cov_kwds={"groups": groups, "use_correction": True}, use_t=True
    )
    result.analysis_dropped_terms = dropped
    return result


def result_row(result, term):
    # Two-way cluster covariance need not be PSD in finite samples. Preserve
    # and disclose invalid nuisance variances instead of replacing them by zero.
    negative = [n for n,v in zip(result.params.index,np.diag(result.cov_params())) if v < 0]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        ci = result.conf_int().loc[term]
    return {"beta": float(result.params[term]), "se": float(result.bse[term]),
            "t": float(result.tvalues[term]), "p": float(result.pvalues[term]),
            "ci_low": float(ci.iloc[0]), "ci_high": float(ci.iloc[1]),
            "n": int(result.nobs), "adj_r2": float(result.rsquared_adj),
            "redundant_terms": "|".join(getattr(result,"analysis_dropped_terms",[])),
            "negative_variance_terms": "|".join(negative)}


def model_coefficients(result, model_id):
    ci = result.conf_int()
    return pd.DataFrame({"model": model_id, "term": result.params.index,
                         "beta": result.params.to_numpy(), "se": result.bse.to_numpy(),
                         "t": result.tvalues.to_numpy(), "p": result.pvalues.to_numpy(),
                         "ci_low": ci.iloc[:,0].to_numpy(), "ci_high": ci.iloc[:,1].to_numpy()})


def trend_tests(core, counts, vocabulary):
    rows, coefficients = [], []
    for form in ["10-K", "10-Q"]:
        sample = core.loc[core.form.eq(form)].copy()
        # Each form-specific test uses its own corpus, not the figure's pooled IDF.
        scored = score_corpus(sample, counts, vocabulary)
        panel = scored.groupby(["cik", "quarter", "time", "quarter_of_year"], as_index=False)[TONES].mean()
        multi = panel.groupby("cik").quarter.nunique()
        within_sample = sample.loc[sample.cik.isin(multi[multi >= 2].index)]
        within_scores = score_corpus(within_sample, counts, vocabulary)
        within = within_scores.groupby(["cik", "quarter", "time", "quarter_of_year"], as_index=False)[TONES].mean()
        for tone in TONES:
            unit = "percentage points per year" if tone.endswith("prop") else "TF-IDF units per year"
            scale = 100 if tone.endswith("prop") else 1
            data = panel.copy()
            data["y"] = data[tone]*scale
            data["time_years"] = data.time/4
            aggregate = data.groupby(["quarter", "time_years", "quarter_of_year"], as_index=False).y.mean()
            ols = smf.ols("y ~ time_years + C(quarter_of_year)", aggregate).fit()
            hac = smf.ols("y ~ time_years + C(quarter_of_year)", aggregate).fit(
                cov_type="HAC", cov_kwds={"maxlags": 4, "use_correction": True}, use_t=True
            )
            wd = within.copy()
            wd["y"] = wd[tone]*scale
            wd["time_years"] = wd.time/4
            firm = clustered_fit("y ~ time_years + C(cik) + C(quarter_of_year)", wd)
            mid = f"trend_{form}_{tone}"
            rows.append({"form": form, "measure": tone,
                         "unit": unit,
                         "aggregate_beta": float(hac.params["time_years"]),
                         "aggregate_ols_t": float(ols.tvalues["time_years"]),
                         "aggregate_hac_t": float(hac.tvalues["time_years"]),
                         "aggregate_hac_p": float(hac.pvalues["time_years"]),
                         "aggregate_n": len(aggregate),
                         **{"within_"+k: v for k,v in result_row(firm,"time_years").items()},
                         "firms": wd.cik.nunique(), "corpus": corpus_id(within_sample),
                         "aggregate_corpus": corpus_id(sample),
                         "single_quarter_filing_exclusions": len(sample)-len(within_sample)})
            coefficients.extend([model_coefficients(hac, mid+"_aggregate_HAC"),
                                 model_coefficients(firm, mid+"_within_firm")])
    out = pd.DataFrame(rows)
    return out, pd.concat(coefficients, ignore_index=True)


def outcome_models(sample, counts, vocabulary, outcome, variant="pooled",
                   two_way=False, active_only=False, benchmark="SPY"):
    scored = score_corpus(sample, counts, vocabulary, active_only=active_only)
    category = "uncertainty" if outcome == "volatility" else "negative"
    outcome_name = "log_post_vol" if outcome == "volatility" else (
        "excess_return" if benchmark == "SPY" else "excess_return_arkk")
    settings = ([('without_pre_volatility', False), ('with_pre_volatility', True)]
                if outcome == 'volatility' else [('with_controls', True)])
    if variant not in {"pooled", "10-K", "10-Q"}:
        settings = settings[-1:]
    rows, coefficients = [], []
    for weight in ["prop", "tfidf"]:
        tone = category+"_"+weight
        data = scored.copy()
        data["score_z"] = standardize(data[tone])
        for control_set, with_pre in settings:
            formula = (outcome_name + " ~ score_z + log_market_value + log_dollar_volume"
                       " + prior_excess_return")
            if with_pre:
                formula += " + log_pre_vol"
            if data.form.nunique() > 1:
                formula += " + C(form)"
            formula += " + C(cik) + C(quarter)"
            result = clustered_fit(formula, data, two_way=two_way)
            model_id = f"{outcome}_{variant}_{tone}_{control_set}"
            row = {"model": model_id, "outcome": outcome, "variant": variant, "measure": tone,
                   "control_set": control_set, "size_control": True,
                   "pre_vol_control": with_pre, "firm_effects": True,
                   "formula": formula,
                   "two_way_cluster": two_way, "benchmark": benchmark,
                   **result_row(result, "score_z"), "firms": data.cik.nunique(),
                   "quarters": data.quarter.nunique(), "corpus": corpus_id(data),
                   "score_sd": float(data[tone].std(ddof=1))}
            df = min(data.cik.nunique(), data.quarter.nunique())-1 if two_way else data.cik.nunique()-1
            row["mde80"] = float((t.ppf(.975,df)+norm.ppf(.8))*row["se"])
            rows.append(row)
            coefficients.append(model_coefficients(result, model_id))
    return pd.DataFrame(rows), pd.concat(coefficients, ignore_index=True)


def all_outcome_models(vol_sample, return_sample, counts, vocabulary):
    rows, coefs = [], []
    for outcome, sample in [("volatility",vol_sample), ("return",return_sample)]:
        specs = [("pooled",sample,{})]
        if outcome == "volatility":
            specs.extend((form,sample.loc[sample.form.eq(form)],{}) for form in ["10-K","10-Q"])
        else:
            specs.append(("ARKK",sample,{"benchmark":"ARKK"}))
        for variant, data, options in specs:
            r,c = outcome_models(data,counts,vocabulary,outcome,variant,**options)
            rows.append(r); coefs.append(c)
    result = pd.concat(rows,ignore_index=True)
    return result, pd.concat(coefs,ignore_index=True)
