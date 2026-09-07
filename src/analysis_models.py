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
from statsmodels.stats.multitest import multipletests

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
    if any(n in dropped for n in ["time","score_z"]):
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
            data = panel.copy()
            data["y"] = standardize(data[tone])
            aggregate = data.groupby(["quarter", "time", "quarter_of_year"], as_index=False).y.mean()
            ols = smf.ols("y ~ time + C(quarter_of_year)", aggregate).fit()
            hac = smf.ols("y ~ time + C(quarter_of_year)", aggregate).fit(
                cov_type="HAC", cov_kwds={"maxlags": 4, "use_correction": True}, use_t=True
            )
            wd = within.copy()
            wd["y"] = standardize(wd[tone])
            firm = clustered_fit("y ~ time + C(cik) + C(quarter_of_year)", wd)
            mid = f"trend_{form}_{tone}"
            rows.append({"form": form, "measure": tone,
                         "aggregate_beta": float(hac.params["time"]),
                         "aggregate_ols_t": float(ols.tvalues["time"]),
                         "aggregate_hac_t": float(hac.tvalues["time"]),
                         "aggregate_hac_p": float(hac.pvalues["time"]),
                         "aggregate_n": len(aggregate),
                         **{"within_"+k: v for k,v in result_row(firm,"time").items()},
                         "firms": wd.cik.nunique(), "corpus": corpus_id(within_sample),
                         "aggregate_corpus": corpus_id(sample),
                         "single_quarter_filing_exclusions": len(sample)-len(within_sample)})
            coefficients.extend([model_coefficients(hac, mid+"_aggregate_HAC"),
                                 model_coefficients(firm, mid+"_within_firm")])
    out = pd.DataFrame(rows)
    for weight in ["prop", "tfidf"]:
        mask = out.measure.str.endswith(weight)
        out.loc[mask, "within_holm_p"] = multipletests(out.loc[mask,"within_p"], method="holm")[1]
    return out, pd.concat(coefficients, ignore_index=True)


def outcome_models(sample, counts, vocabulary, outcome, variant="pooled", firm_effects=False,
                   two_way=False, active_only=False, benchmark="SPY"):
    scored = score_corpus(sample, counts, vocabulary, active_only=active_only)
    category = "uncertainty" if outcome == "volatility" else "negative"
    outcome_name = "log_post_vol" if outcome == "volatility" else (
        "excess_return" if benchmark == "SPY" else "excess_return_arkk")
    settings = [("none", False, False), ("size", True, False),
                ("volatility", False, True), ("both", True, True)]
    if variant != "pooled":
        settings = settings[-1:]
    rows, coefficients = [], []
    for weight in ["prop", "tfidf"]:
        tone = category+"_"+weight
        data = scored.copy()
        data["score_z"] = standardize(data[tone])
        for control_set, with_size, with_pre in settings:
            formula = outcome_name + " ~ score_z"
            if with_size:
                formula += " + log_market_value"
            if with_pre:
                formula += " + log_pre_vol"
            if firm_effects:
                formula += " + C(cik) + C(quarter)"
                if data.form.nunique() > 1:
                    formula += " + C(form)"
            result = clustered_fit(formula, data, two_way=two_way)
            model_id = f"{outcome}_{variant}_{tone}_{control_set}"
            row = {"model": model_id, "outcome": outcome, "variant": variant, "measure": tone,
                   "control_set": control_set, "size_control": with_size,
                   "pre_vol_control": with_pre, "firm_effects": firm_effects,
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
        specs = [("pooled",sample,{}),
                 ("firm_FE",sample,{"firm_effects":True}),
                 ("two_way",sample,{"two_way":True})]
        specs.extend((form,sample.loc[sample.form.eq(form)],{}) for form in ["10-K","10-Q"])
        if outcome == "return":
            specs += [("ARKK",sample,{"benchmark":"ARKK"}),
                      ("active_negative",sample,{"active_only":True})]
        for variant, data, options in specs:
            r,c = outcome_models(data,counts,vocabulary,outcome,variant,**options)
            rows.append(r); coefs.append(c)
    result = pd.concat(rows,ignore_index=True)
    primary = result.variant.eq("pooled") & result.control_set.eq("both")
    result.loc[primary,"holm_p"] = multipletests(result.loc[primary,"p"],method="holm")[1]
    return result, pd.concat(coefs,ignore_index=True)
