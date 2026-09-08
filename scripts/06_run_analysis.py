"""Construct the analysis samples and reproduce all seven required exhibits."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, INTERIM_DIR, PRICE_DIR, OUTPUT_DIR, UNIVERSE_DIR
from src.lexicons import load_master_dictionary,lm_word_lists
from src.analysis_data import build_text_data,build_market_features,score_corpus,ANALYSIS
from src.analysis_models import trend_tests,all_outcome_models,TONES

RESULTS = OUTPUT_DIR / "analysis"


def waterfall(frame, steps, branch):
    rows=[]
    current=frame.copy()
    rows.append({"branch":branch,"filter":"Starting unique filings","removed":0,"remaining":len(current),"firms":current.cik.nunique()})
    audit=frame[["accession","ticker","cik"]].copy()
    audit["first_exclusion"]="retained"
    for name, rule in steps:
        keep=rule(current)
        excluded=current.loc[~keep]
        audit.loc[audit.accession.isin(excluded.accession),"first_exclusion"]=name
        current=current.loc[keep].copy()
        rows.append({"branch":branch,"filter":name,"removed":len(excluded),"remaining":len(current),"firms":current.cik.nunique()})
    audit.to_csv(RESULTS / (branch+"_sample_audit.csv"),index=False)
    return current,rows


def make_figure(scored):
    quarterly=(scored.groupby(["cik","form","quarter"],as_index=False)[TONES].mean()
               .groupby(["form","quarter"],as_index=False)[TONES].mean())
    prices=pd.read_csv(PRICE_DIR/"prices.csv",index_col=0,parse_dates=True)
    vix=prices["^VIX"].loc["2021":"2025"].groupby(lambda d:str(d.to_period("Q"))).mean()
    quarters=[str(q) for q in pd.period_range("2021Q1","2025Q4",freq="Q")]
    colors={"10-K":"#235b8e","10-Q":"#bd5b34"}
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False})
    fig,axs=plt.subplots(2,2,figsize=(11.5,7.2),sharex=True)
    for ax,tone in zip(axs.flat,TONES):
        for form in ["10-K","10-Q"]:
            values=quarterly.loc[quarterly.form.eq(form)].set_index("quarter")[tone].reindex(quarters)
            ax.plot(range(20),values*(100 if tone.endswith("prop") else 1),label=form,color=colors[form],lw=1.8,marker="o",ms=3)
        names={"negative_prop":"Negative-word proportion", "negative_tfidf":"Negative-language TF-IDF",
               "uncertainty_prop":"Uncertainty-word proportion", "uncertainty_tfidf":"Uncertainty TF-IDF"}
        ax.set_title(names[tone],loc="left",fontweight="bold")
        ax.set_ylabel("% of words" if tone.endswith("prop") else "Sum of term weights")
        ax.grid(axis="y",alpha=.18)
        other=ax.twinx()
        other.plot(range(20),vix.reindex(quarters),color="#737b83",alpha=.55,ls="--",lw=1.2,label="VIX")
        other.set_ylim(10,40);other.set_ylabel("VIX",color="#737b83");other.spines["top"].set_visible(False)
        ax.set_xticks([0,4,8,12,16,19],labels=[quarters[i] for i in [0,4,8,12,16,19]],rotation=30,ha="right")
    handles,labels=axs.flat[0].get_legend_handles_labels()
    handles2,labels2=other.get_legend_handles_labels()
    fig.legend(handles+handles2,labels+labels2,loc="lower center",ncol=3,frameon=False)
    fig.tight_layout(rect=(0,.05,1,1))
    fig.savefig(RESULTS/"figure1.png",dpi=200,bbox_inches="tight")
    fig.savefig(RESULTS/"figure1.svg",bbox_inches="tight")
    plt.close(fig)
    quarterly.to_csv(RESULTS/"quarterly_tone.csv",index=False)
    vix.rename("VIX").to_csv(RESULTS/"quarterly_vix.csv")
    return quarterly


def main():
    RESULTS.mkdir(parents=True,exist_ok=True)
    meta,counts,vocabulary=build_text_data()
    features=build_market_features(meta)
    def earliest_company_quarter(d):
        ordered=d.sort_values(["cik","quarter","filing_date","acceptance_datetime","accession"])
        keep=ordered.drop_duplicates(["cik","quarter"],keep="first").accession
        return d.accession.isin(keep)
    sample_steps=[
        ("Parsed non-amended 10-K/10-Q",lambda d:d.form.isin(["10-K","10-Q"])
         & pd.to_datetime(d.acceptance_datetime,utc=True,errors="coerce").notna()),
        ("At least 2,000 words (10-K) or 1,000 words (10-Q)",
         lambda d:(d.form.eq("10-K") & d.analysis_words.ge(2000))
         | (d.form.eq("10-Q") & d.analysis_words.ge(1000))),
        ("Earliest filing per company-calendar quarter",earliest_company_quarter),
        ("Usable day 0 and day -1 price at least $3",
         lambda d:d.event_day.notna() & d.prior_price.ge(3)),
        ("At least 60 return days before and after day 0",
         lambda d:d.pre_return_count.ge(60) & d.post_return_count.ge(60)),
        ("Complete share count, controls and outcomes",
         lambda d:d[["log_market_value","log_dollar_volume","prior_excess_return","log_pre_vol",
                     "log_post_vol","excess_return","excess_return_arkk"]].notna().all(axis=1))]
    core,flow=waterfall(features,sample_steps,"analysis")
    vol_sample=core.copy()
    ret_sample=core.copy()
    flows=pd.DataFrame(flow)
    flows.to_csv(RESULTS/"table1_filings.csv",index=False)
    universe=pd.read_csv(UNIVERSE_DIR/"universe.csv",dtype={"cik":str})
    raw=pd.read_csv(UNIVERSE_DIR/"ark_holdings_raw.csv")
    company_table=pd.DataFrame([
        ["Unique cleaned securities in frozen snapshot",124,0],
        ["SEC ticker-to-CIK mapping found",len(universe),124-len(universe)],
        ["At least one 2021-2025 10-K/10-Q",int(universe.status.eq('domestic_filer').sum()),int(universe.status.ne('domestic_filer').sum())],
        ["Unique companies (GOOG and GOOGL count as one)",meta.cik.nunique(),1],
    ],columns=["filter","remaining","removed"])
    company_table.to_csv(RESULTS/"table1_universe.csv",index=False)
    eligible=universe.loc[universe.status.eq('domestic_filer')]
    scored=score_corpus(core,counts,vocabulary)
    scored.to_csv(ANALYSIS/"scored_text_corpus.csv",index=False)
    vol_sample.to_csv(ANALYSIS/"volatility_sample.csv",index=False)
    ret_sample.to_csv(ANALYSIS/"return_sample.csv",index=False)
    summaries=[]
    for form in ["10-K","10-Q"]:
        for tone in TONES:
            x=scored.loc[scored.form.eq(form),tone]*(100 if tone.endswith('prop') else 1)
            summaries.append({"form":form,"measure":tone,"n":len(x),"mean":x.mean(),"sd":x.std(),
                              "p25":x.quantile(.25),"median":x.median(),"p75":x.quantile(.75)})
    table2=pd.DataFrame(summaries);table2.to_csv(RESULTS/"table2.csv",index=False)
    correlations=[]
    for w in ["prop","tfidf"]:
        correlations.append({"form":"All","weight":w,
                             "correlation":scored['negative_'+w].corr(scored['uncertainty_'+w])})
    for form in ["10-K","10-Q"]:
        d=scored.loc[scored.form.eq(form)]
        for w in ["prop","tfidf"]:
            correlations.append({"form":form,"weight":w,"correlation":d['negative_'+w].corr(d['uncertainty_'+w])})
    pd.DataFrame(correlations).to_csv(RESULTS/"tone_correlations.csv",index=False)
    lists=lm_word_lists()
    totals=counts[core.text_row.to_numpy(dtype=int)].sum(axis=0)
    word_rows=[]
    for cat in ["Negative","Uncertainty"]:
        pairs=sorted([(w,int(totals[i])) for i,w in enumerate(vocabulary) if w in lists[cat]],key=lambda x:(-x[1],x[0]))
        total=sum(n for _,n in pairs)
        for rank,(word,count) in enumerate(pairs[:30],1):
            word_rows.append({"category":cat,"rank":rank,"word":word,"count":count,"share_pct":100*count/total})
    table3=pd.DataFrame(word_rows);table3.to_csv(RESULTS/"table3.csv",index=False)
    contrast=scored[["ticker","cik","form","filing_date","accession","text_path"]+TONES].copy()
    for w in ["prop","tfidf"]:
        for category in ["negative","uncertainty"]:
            col=category+'_'+w
            contrast[col+'_percentile']=contrast.groupby('form')[col].rank(pct=True)
        contrast['negative_minus_uncertainty_'+w]=(contrast['negative_'+w+'_percentile']
                                                   - contrast['uncertainty_'+w+'_percentile'])
    candidates=[]
    for w in ["prop","tfidf"]:
        gap='negative_minus_uncertainty_'+w
        candidates.append(contrast.nlargest(1,gap).assign(weight=w,direction='high negative / low uncertainty'))
        candidates.append(contrast.nsmallest(1,gap).assign(weight=w,direction='high uncertainty / low negative'))
    pd.concat(candidates,ignore_index=True).to_csv(RESULTS/'measure_contrast_candidates.csv',index=False)
    make_figure(scored)
    table4,trend_coeffs=trend_tests(core,counts,vocabulary)
    table4.to_csv(RESULTS/"table4.csv",index=False)
    models,coeffs=all_outcome_models(vol_sample,ret_sample,counts,vocabulary)
    models.to_csv(RESULTS/"all_outcome_models.csv",index=False)
    models.loc[models.variant.eq('pooled') & models.outcome.eq('volatility')].to_csv(RESULTS/"table5.csv",index=False)
    models.loc[models.variant.eq('pooled') & models.outcome.eq('return')].to_csv(RESULTS/"table6.csv",index=False)
    pd.concat([trend_coeffs,coeffs],ignore_index=True).to_csv(RESULTS/"all_regression_coefficients.csv",index=False)
    summary={"core_filings":len(core),"core_firms":core.cik.nunique(),"core_forms":core.form.value_counts().to_dict(),
             "unique_downloaded_filings":len(meta),"duplicate_security_records_removed":20,
             "shell_filings_observed":int(features.shell_company.eq(True).sum()),
             "unknown_shell_status":int(features.shell_company.isna().sum()),
             "vol_sample":len(vol_sample),"return_sample":len(ret_sample),
             "shifted_event_days":int(core.event_shifted.sum()),
             "shares_sources":features.shares_source.value_counts().to_dict(),
             "core_unresolved_shares":int(core.log_market_value.isna().sum()),
             "cover_sentence_recoveries":int(features.shares_source.eq('cover_sentence').sum()),
             "parser_old_words":int(meta.n_words.sum()),"parser_new_words":int(meta.analysis_words.sum()),
             "lexicon_overlap":len(lists['Negative']&lists['Uncertainty']),
             "top10_negative_share":float(table3.loc[(table3.category.eq('Negative')) & table3['rank'].le(10),'share_pct'].sum()),
             "top10_uncertainty_share":float(table3.loc[(table3.category.eq('Uncertainty')) & table3['rank'].le(10),'share_pct'].sum()),
             "top30_negative_share":float(table3.loc[table3.category.eq('Negative'),'share_pct'].sum()),
             "top30_uncertainty_share":float(table3.loc[table3.category.eq('Uncertainty'),'share_pct'].sum()),
             "quarterly_observations":20,"correlations":correlations,
             "tested_outcome_models":len(models),"tested_trend_models":len(table4)*2,
             "holdings_dates":sorted(raw.date.unique().tolist())}
    (RESULTS/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    features.loc[features.cover_sentence.notna() & features.cover_sentence.ne(''),
                 ['ticker','accession','cover_shares','cover_shares_date','cover_sentence']].to_csv(RESULTS/'cover_sentence_review.csv',index=False)
    print(json.dumps(summary,indent=2))
    print('\nPRIMARY OUTCOME MODELS\n',models.loc[models.variant.eq('pooled'),['outcome','measure','pre_vol_control','beta','se','p','n']].to_string(index=False))
    print('\nWITHIN-FIRM TRENDS\n',table4[['form','measure','within_beta','within_t','within_p','unit']].to_string(index=False))
    return summary


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
