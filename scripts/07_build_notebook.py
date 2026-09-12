"""Build and execute the deliverable notebook, saving all exhibit outputs."""
import os
from pathlib import Path
import sys

import nbformat as nbf
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]


def main():
    cells=[]
    md=lambda text: cells.append(nbf.v4.new_markdown_cell(text))
    code=lambda text: cells.append(nbf.v4.new_code_cell(text))
    md('# Assignment 1\n## Uncertainty and Sentiment in ARK Company Filings\n'
       'Victor Chen (yc8027) | FRE-GY 7871 A, Fall 2026. The analysis follows the current assignment brief. '
       'The instructor supplied data acquisition; the analysis additions and AI assistance are disclosed in `AI_USE.md`.\n\n'
       'This is a retrospective event study, not an out-of-sample investment strategy. '
       'The complete specification and declared sensitivities are in [METHODOLOGY.md](METHODOLOGY.md).')
    md('## Reproduction\nRun scripts `00` through `03`, then `05_get_price_actions.py` first. '
       'The downloads remain local and are excluded from Git. This notebook executes the analysis from those inputs, '
       'including text parsing, share recovery, exact-sample TF-IDF, all regressions and figures. '
       'A cached text matrix accelerates reruns; `build_text_data(force=True)` rebuilds it from the original HTML.')
    code('''from pathlib import Path
import os, sys, runpy, json, subprocess
import pandas as pd
from IPython.display import display, Markdown, Image
ROOT=Path.cwd()
assert (ROOT/'src/config.py').exists(), 'Run the notebook from the repository root.'
os.environ['MPLCONFIGDIR']=str(ROOT/'outputs/mpl_cache')
sys.path.insert(0,str(ROOT))
RESULTS=ROOT/'outputs/analysis'
pd.set_option('display.max_rows',100)
pd.set_option('display.max_columns',30)
pd.set_option('display.float_format',lambda x:f'{x:.4f}')
def show_table(frame):
    labels={'measure':'Language measure','control_set':'Controls','beta':'Estimated coefficient',
            'se':'Standard error','t':'t statistic','p':'p-value (zero coefficient)',
            'n':'Observations','firms':'Number of companies','form':'Report type',
            'ci_low':'95% confidence interval: lower','ci_high':'95% confidence interval: upper',
            'within_beta':'Within-company slope','within_se':'Within-company standard error',
            'within_p':'Within-company p-value',
            'aggregate_beta':'Overall slope','aggregate_ols_t':'Ordinary OLS t statistic',
            'aggregate_hac_t':'Newey-West t statistic','within_n':'Company-quarter observations',
            'term':'Variable','formula':'Regression equation','mde80':'Approximate detectable effect (80% power)'}
    readable={'negative_prop':'Negative-word proportion','negative_tfidf':'Negative-language TF-IDF',
              'uncertainty_prop':'Uncertainty-word proportion','uncertainty_tfidf':'Uncertainty TF-IDF',
              'without_pre_volatility':'Without prior volatility',
              'with_pre_volatility':'With prior volatility','with_controls':'With controls',
              'score_z':'Language score (standardized internally)',
              'log_market_value':'Company size (log market value)','log_pre_vol':'Prior volatility (log)',
              'log_dollar_volume':'Average dollar volume (log)',
              'prior_excess_return':'Prior SPY excess return'}
    view=frame.copy()
    for col in ['measure','control_set','term']:
        if col in view:
            view[col]=view[col].replace(readable)
    display(view.rename(columns=labels))
''')
    md('## Numerical and timing tests\nThe tests cover the assignment\'s three-document TF-IDF check, same-corpus IDF, '
       'the 16:00 Eastern cutoff, missing returns, compounding, split units, inline text, shell checkboxes, common-share classes, '
       'and redundant fixed effects.')
    code("r=subprocess.run([sys.executable,'-m','pytest','tests','-q'],cwd=ROOT,capture_output=True,text=True)\nprint(r.stdout)\nassert r.returncode==0,r.stderr")
    md('## Run the complete analysis\nThe filters follow the instructor repository: form-specific word minimums, '
       'one earliest filing per company-quarter, a day -1 price of at least $3, and at least 60 returns before and after day 0. '
       'The volatility comparison shares one sample and differs only by the prior-volatility control. IDF is estimated on '
       'exactly each regression corpus.')
    code("analysis=runpy.run_path(str(ROOT/'scripts/06_run_analysis.py'),run_name='analysis_module')\nsummary=analysis['main']()")
    md('## Table 1 — Sample filters\nThe universe table counts securities/issuers. The filing table counts unique '
       'documents; the raw 1,702 ticker-filing rows contain 20 duplicate Alphabet reports. Unknown SEC mappings are '
       'reported as unresolved, not presumed to be private firms. Every sequential filter is shown.')
    code("show_table(pd.read_csv(RESULTS/'table1_universe.csv'))\nshow_table(pd.read_csv(RESULTS/'table1_filings.csv'))")
    md('## Measures\nNegative language and uncertainty remain separate. A proportional score is category occurrences '
       'divided by all tokens. Equation (1) is\n\n'
       '$$w_{ij}=\\frac{1+\\ln(tf_{ij})}{1+\\ln(a_j)}\\ln(N/df_i),\\quad tf_{ij}>0,$$\n\n'
       'and zero otherwise, with $a_j=L_j/U_j$, the mean token frequency across all distinct document terms. '
       'The category score sums its term weights. Natural logarithms and no smoothing are used. The assignment self-check '
       'produces 0.8480, 0.2885 and 0.5026 for d1-d3.')
    md('## Table 2 — Descriptive statistics\nProportional measures in this table are expressed as percentages of all words. '
       'TF-IDF scores are sums of weights. Annual and quarterly filings are shown separately.')
    code("show_table(pd.read_csv(RESULTS/'table2.csv'))\nshow_table(pd.read_csv(RESULTS/'tone_correlations.csv'))\nprint('Dictionary overlap:',summary['lexicon_overlap'],'words')\nshow_table(pd.read_csv(RESULTS/'measure_contrast_candidates.csv'))")
    md('## Table 3 — Thirty most common words per list\nEach share uses all occurrences on its own category list '
       'as the denominator. The ten most frequent words account for 28.1% of Negative and 74.4% of Uncertainty counts.')
    code("t3=pd.read_csv(RESULTS/'table3.csv')\nfor category in ['Negative','Uncertainty']:\n    display(Markdown('### '+category))\n    show_table(t3.loc[t3.category.eq(category)].reset_index(drop=True))")
    md('## Q1 and Q2 — Filing text and its outcomes\n'
       'The PayPal case uses the same visible narrative as the scorer. Match uncertainty-containing sentences '
       'of at least 12 tokens in Risk Factors against the preceding annual report, ignoring punctuation and case. '
       'This is a case study of retained disclosure, not a corpus-wide estimate of duplication. '
       'Negative counts also reflect ordinary credit-loss and fraud-protection accounting; a high count need not be new bad news.')
    code("evidence_module=runpy.run_path(str(ROOT/'scripts/10_report_evidence.py'),run_name='evidence_module')\nevidence_module['main']()\nevidence=json.loads((RESULTS/'report_evidence.json').read_text())\ndisplay(pd.Series(evidence['case'],name='PayPal 10-K filed 2024-02-08'))\nprint('Repeated uncertainty sentences:',evidence['sentences_reappearing_in_prior_risk_section'],'of',evidence['uncertainty_sentences_at_least_12_tokens'])\nprint('Example:',evidence['matched_examples'][6])")
    md('## Figure 1 — Quarterly language scores and VIX\nAverage within issuer/form/filing quarter before averaging across issuers. '
       'Separate 10-K and 10-Q to expose form composition. VIX is quarterly mean market uncertainty on the right axis, '
       'not a substitute for company-level realized volatility.')
    code("display(Image(filename=str(RESULTS/'figure1.png')))\nshow_table(pd.read_csv(RESULTS/'quarterly_tone.csv'))")
    md('## Table 4 — Trend tests\nThe primary trend test includes issuer and quarter-of-year effects with issuer-clustered '
       'SEs. Aggregate OLS and Newey-West (four lags, finite-sample correction) t statistics are both reported. '
       'Proportional slopes are percentage points per year; TF-IDF slopes are term-weight units per year.')
    code("t4=pd.read_csv(RESULTS/'table4.csv')\nshow_table(t4[['form','measure','unit','aggregate_beta','aggregate_ols_t','aggregate_hac_t','within_beta','within_se','within_t','within_p','within_n','firms']])")
    md('## Table 5 — Uncertainty and next-quarter volatility\nThe outcome is log annualized volatility on [+4,+63]; '
       'pre-volatility uses [-60,-6]. Both models include log size, log average dollar volume, prior SPY excess return, '
       'a 10-K indicator, company effects and calendar-quarter effects. The second adds log prior volatility. '
       'Both language measures remain continuous. Reported proportional coefficients are per 1 percentage-point increase; '
       'reported TF-IDF coefficients are per 1 unit. Internal standardization is rescaled back to these units and does not '
       'change fitted values, t-statistics or p-values.')
    code("t5=pd.read_csv(RESULTS/'table5.csv')\nt5['Reported unit']=t5.measure.map(lambda x:'per 1 percentage point' if x.endswith('_prop') else 'per 1 TF-IDF unit')\nt5['unit_scale']=t5.apply(lambda r:.01/r.score_sd if r.measure.endswith('_prop') else 1/r.score_sd,axis=1)\nfor col in ['beta','se','ci_low','ci_high']:\n    t5[col]=t5[col]*t5.unit_scale\nshow_table(t5[['measure','Reported unit','control_set','formula','beta','se','t','p','ci_low','ci_high','n','firms','corpus']])\nassert t5.groupby('measure').corpus.nunique().eq(1).all()\nc=pd.read_csv(RESULTS/'all_regression_coefficients.csv')")
    md('## Table 6 — Sentiment and filing-period excess returns\nThe outcome is stock minus SPY buy-and-hold return '
       'over [0,+3], in percentage points. Proportion coefficients are per 1 percentage-point increase and TF-IDF '
       'coefficients per 1 unit. The model includes the full required control and fixed-effect set. The minimum '
       'detectable effect is an approximate 80%-power precision diagnostic, not observed power.')
    code("t6=pd.read_csv(RESULTS/'table6.csv')\nt6['Reported unit']=t6.measure.map(lambda x:'per 1 percentage point' if x.endswith('_prop') else 'per 1 TF-IDF unit')\nt6['unit_scale']=t6.apply(lambda r:.01/r.score_sd if r.measure.endswith('_prop') else 1/r.score_sd,axis=1)\nfor col in ['beta','se','ci_low','ci_high','mde80']:\n    t6[col]=t6[col]*t6.unit_scale\nshow_table(t6[['measure','Reported unit','control_set','formula','beta','se','t','p','ci_low','ci_high','mde80','n','firms']])")
    md('## Form and benchmark checks\nTable 5 is re-estimated separately for 10-K and 10-Q samples, with sample-specific IDF. '
       'The return model is also estimated against ARKK to disclose benchmark sensitivity.')
    code("models=pd.read_csv(RESULTS/'all_outcome_models.csv')\nshow_table(models[['outcome','variant','measure','control_set','formula','beta','se','p','n','corpus']])")
    md('## Interpretation and limitations\nThe annual-report Negative trend is the result I trust most within this '
       'selected sample because proportion and TF-IDF both rise inside companies and the aggregate estimates agree in '
       'direction. I do not infer a general Uncertainty trend because annual proportion and TF-IDF disagree while both '
       'quarterly measures fall. Prior volatility explains much of the apparent volatility relationship; the remaining '
       'pooled language estimates are imprecise. The negative return signs are inconclusive rather than evidence of no effect.\n\n'
       'The 2026 holdings snapshot omits former holdings and creates survivorship/selection bias. Dictionary scores do '
       'not distinguish new information from repeated risk language, full-corpus IDF is retrospective, 20 quarters give '
       'a short aggregate series, daily timing cannot isolate simultaneous earnings news, and multi-class size is '
       'approximated. Several related form, weighting, control and benchmark specifications also make an isolated small '
       'p-value less persuasive. Earlier no-control, size-only, prior-volatility-only and both-control models, an '
       'issuer/time-effects sensitivity, a shell screen, a temporary no-$3 sample and a return-quintile plot are disclosed '
       'in `AI_USE.md`; the current assignment specification supersedes them.\n\n'
       'The highest-value next step is to rebuild point-in-time ARK membership from dated holdings files, including firms '
       'later sold, delisted or failed. The cost is reconciling identifier changes and obtaining filings plus '
       'delisting-adjusted prices for companies missing from current sources.\n\n'
       'See the short PDF report for the test-by-test discussion and `AI_USE.md` for the authorship disclosure.')
    md('## Plain-language table guide\nA score is the measured amount of uncertainty or negative language. '
       'Outcome tables report proportions per 1 percentage point and TF-IDF per 1 unit. A score p-value tests a zero '
       'score coefficient. The PDF labels company-clustered standard errors in separate rows or columns. '
       'Log means natural logarithm. P25/P75 are percentiles. Internal variable `score_z` means the '
       'standardized language score named by that model. The intercept is its fitted baseline.')
    md((ROOT/'ANALYSIS_CHOICES.md').read_text(encoding='utf-8'))
    nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}})
    target=ROOT/'assignment1.ipynb'
    os.environ['PATH']=str(Path(sys.executable).parent)+os.pathsep+os.environ.get('PATH','')
    os.environ['MPLCONFIGDIR']=str(ROOT/'outputs/mpl_cache')
    os.environ['JUPYTER_RUNTIME_DIR']=str(ROOT/'outputs/jupyter_runtime')
    os.environ['IPYTHONDIR']=str(ROOT/'outputs/ipython')
    client=NotebookClient(nb,timeout=900,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}})
    client.execute()
    nbf.write(nb,target)
    print('Executed notebook saved:',target)


if __name__=='__main__':
    main()
