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
       'FRE-GY 7871 A, Fall 2026. The analysis follows the current assignment brief. '
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
              'score_z':'Language score (+1 standard deviation)',
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
       'The score is standardized within the same complete-case corpus.')
    code("t5=pd.read_csv(RESULTS/'table5.csv')\nshow_table(t5[['measure','control_set','formula','beta','se','t','p','ci_low','ci_high','n','firms','corpus']])\nassert t5.groupby('measure').corpus.nunique().eq(1).all()\nc=pd.read_csv(RESULTS/'all_regression_coefficients.csv')\nshow_table(c.loc[c.model.isin(t5.model)])")
    md('## Table 6 — Sentiment and filing-period excess returns\nThe outcome is stock minus SPY buy-and-hold return '
       'over [0,+3], in percentage points. The model includes the full required control and fixed-effect set. The minimum '
       'detectable effect is an approximate 80%-power precision diagnostic, not observed power.')
    code("t6=pd.read_csv(RESULTS/'table6.csv')\nshow_table(t6[['measure','control_set','formula','beta','se','t','p','ci_low','ci_high','mde80','n','firms']])\nshow_table(c.loc[c.model.isin(t6.model)])")
    md('## Form and benchmark checks\nTable 5 is re-estimated separately for 10-K and 10-Q samples, with sample-specific IDF. '
       'The return model is also estimated against ARKK to disclose benchmark sensitivity.')
    code("models=pd.read_csv(RESULTS/'all_outcome_models.csv')\nshow_table(models[['outcome','variant','measure','control_set','formula','beta','se','p','n','corpus']])")
    md('## Interpretation and limitations\nAnnual-report negative language rises within issuers under both weighting '
       'schemes; uncertainty trends differ by form and weight. The pre-volatility control attenuates the uncertainty '
       'coefficient, and neither remaining pooled estimate is precise, so a robust incremental volatility relationship '
       'is not established. The four-day return test is imprecise. These are different tests '
       'with different evidence; a blanket claim that the sample is too small is not warranted.\n\n'
       'The 2026 holdings snapshot creates survivorship/selection bias. It does not reveal former holdings that '
       'disappeared. Correct acceptance times and contemporaneous share counts do not cure that selection. '
       'Further limits include full-corpus scoring, 20 aggregate quarters, daily timing, and '
       'multi-class valuation approximations. The next improvement is a historical holdings universe followed by '
       'a held-out forecasting evaluation.\n\n'
       'See the short PDF report for the test-by-test discussion and `AI_USE.md` for the authorship disclosure.')
    md('## Plain-language table guide\nA score is the measured amount of uncertainty or negative language. '
       'One standard deviation is a common scale for comparing coefficients. A score p-value tests a zero '
       'score coefficient. Parentheses in the PDF contain company-clustered standard errors. '
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
