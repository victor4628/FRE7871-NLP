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
            'se':'Standard error','t':'t statistic','p':'p-value (zero coefficient)','holm_p':'Adjusted p-value (Holm)',
            'n':'Observations','firms':'Number of companies','form':'Report type',
            'ci_low':'95% confidence interval: lower','ci_high':'95% confidence interval: upper',
            'within_beta':'Within-company slope','within_se':'Within-company standard error',
            'within_p':'Within-company p-value','within_holm_p':'Adjusted within-company p-value (Holm)',
            'aggregate_beta':'Overall slope','aggregate_ols_t':'Ordinary OLS t statistic',
            'aggregate_hac_t':'Newey-West t statistic','within_n':'Company-quarter observations',
            'term':'Variable','formula':'Regression equation','mde80':'Approximate detectable effect (80% power)'}
    readable={'negative_prop':'Negative-word proportion','negative_tfidf':'Negative-language TF-IDF',
              'uncertainty_prop':'Uncertainty-word proportion','uncertainty_tfidf':'Uncertainty TF-IDF',
              'none':'No controls','size':'Company size only','volatility':'Prior volatility only',
              'both':'Both controls','score_z':'Language score (+1 standard deviation)',
              'log_market_value':'Company size (log market value)','log_pre_vol':'Prior volatility (log)'}
    view=frame.copy()
    for col in ['measure','control_set','term']:
        if col in view:
            view[col]=view[col].replace(readable)
    display(view.rename(columns=labels))
''')
    md('## Numerical and timing tests\nThe tests cover the paper\'s weighting formula, same-corpus IDF, '
       'early closes, missing returns, compounding, split units, inline text, shell checkboxes, common-share classes, '
       'and redundant fixed effects.')
    code("r=subprocess.run([sys.executable,'-m','pytest','tests','-q'],cwd=ROOT,capture_output=True,text=True)\nprint(r.stdout)\nassert r.returncode==0,r.stderr")
    md('## Run the complete analysis\nThe initial specification was defined independently of significance. '
       'The student subsequently requested removal of the optional $3 price cutoff; all results below '
       'use that amended sample, retaining low-priced stocks. The outcome models were subsequently revised '
       'at the student\'s request to no controls, size only, prior volatility only, and both. '
       'Returns and volatility have separate sample waterfalls. Within each specification IDF is estimated on '
       'exactly its regression documents. Before/after pre-volatility-control pairs share the same sample.')
    code("analysis=runpy.run_path(str(ROOT/'scripts/06_run_analysis.py'),run_name='analysis_module')\nsummary=analysis['main']()")
    md('## Table 1 — Sample filters\nThe universe table counts securities/issuers. The filing table counts unique '
       'documents; the raw 1,702 ticker-filing rows contain 20 duplicate Alphabet reports. Unknown SEC mappings are '
       'reported as unresolved, not presumed to be private firms. Shell status is assessed at the filing date.')
    code("show_table(pd.read_csv(RESULTS/'table1_universe.csv'))\nshow_table(pd.read_csv(RESULTS/'table1_filings.csv'))")
    md('## Measures\nNegative language and uncertainty remain separate. A proportional score is category occurrences '
       'divided by all tokens. Equation (1) is\n\n'
       '$$w_{ij}=\\frac{1+\\ln(tf_{ij})}{1+\\ln(a_j)}\\ln(N/df_i),\\quad tf_{ij}>0,$$\n\n'
       'and zero otherwise, with $a_j=L_j/U_j$, the mean token frequency across all distinct document terms. '
       'The category score sums its term weights. Natural logarithms and no smoothing are used. '
       'The assignment\'s nonzero Negative flags include ten removed terms; active-only Negative is a sensitivity.')
    md('## Table 2 — Descriptive statistics\nProportional measures in this table are expressed as percentages of all words. '
       'TF-IDF scores are sums of weights. Annual and quarterly filings are shown separately.')
    code("show_table(pd.read_csv(RESULTS/'table2.csv'))\nshow_table(pd.read_csv(RESULTS/'tone_correlations.csv'))\nprint('Dictionary overlap:',summary['lexicon_overlap'],'words')")
    md('## Table 3 — Thirty most common words per list\nEach share uses all occurrences on its own category list '
       'as the denominator. The lists\' overlap and correlated topics mean their scores are not statistically independent.')
    code("t3=pd.read_csv(RESULTS/'table3.csv')\nfor category in ['Negative','Uncertainty']:\n    display(Markdown('### '+category))\n    show_table(t3.loc[t3.category.eq(category)].reset_index(drop=True))")
    md('## Figure 1 — Quarterly language scores and VIX\nAverage within issuer/form/filing quarter before averaging across issuers. '
       'Separate 10-K and 10-Q to expose form composition. VIX is quarterly mean market uncertainty on the right axis, '
       'not a substitute for company-level realized volatility.')
    code("display(Image(filename=str(RESULTS/'figure1.png')))\nshow_table(pd.read_csv(RESULTS/'quarterly_tone.csv'))")
    md('## Table 4 — Trend tests\nThe primary trend test includes issuer and quarter-of-year effects with issuer-clustered '
       'SEs. Aggregate OLS and Newey-West (four lags, finite-sample correction) t statistics are both reported. '
       'Each slope is in SDs per quarter. Holm correction covers the four category-by-form within-issuer tests '
       'separately for each weighting scheme.')
    code("t4=pd.read_csv(RESULTS/'table4.csv')\nshow_table(t4[['form','measure','aggregate_beta','aggregate_ols_t','aggregate_hac_t','within_beta','within_se','within_p','within_holm_p','within_n','firms']])")
    md('## Table 5 — Uncertainty and next-quarter volatility\nThe outcome is log annualized volatility on trading days '
       '[4,66]. Pre-volatility uses [-63,-1]. Four models contain the language score plus an intercept, then add size only, '
       'prior volatility only, or both. No other controls or fixed effects enter these primary models. '
       'Size is log market value, included because company scale may relate to both language scores and market behavior. '
       'It is a methodological choice, not explicitly required by the assignment. The score is standardized '
       'within the same complete-case corpus, so the coefficient change is not a change in sample composition.')
    code("t5=pd.read_csv(RESULTS/'table5.csv')\nshow_table(t5[['measure','control_set','formula','beta','se','t','p','holm_p','ci_low','ci_high','n','firms','corpus']])\nassert t5.groupby('measure').corpus.nunique().eq(1).all()\nc=pd.read_csv(RESULTS/'all_regression_coefficients.csv')\nshow_table(c.loc[c.model.isin(t5.model)])")
    md('## Table 6 — Sentiment and filing-period excess returns\nThe outcome is stock minus SPY buy-and-hold return '
       'over [0,3], in percentage points. The same four control specifications are compared on one common '
       'sample, so even the no-control model uses filings with an available pre-volatility baseline. The minimum '
       'detectable effect is an approximate 80%-power precision diagnostic, not observed power.')
    code("t6=pd.read_csv(RESULTS/'table6.csv')\nshow_table(t6[['measure','control_set','formula','beta','se','t','p','holm_p','ci_low','ci_high','mde80','n','firms']])\nshow_table(c.loc[c.model.isin(t6.model)])\nassert t6.groupby('measure').corpus.nunique().eq(1).all()")
    md('## Outcome sensitivities\nAll sensitivities use both size and prior volatility. Form-specific samples '
       're-estimate IDF. Other checks add issuer, calendar-quarter and form effects, use two-way clustering, '
       'change the return benchmark to ARKK, or remove retired '
       'Negative terms. Negative nuisance variances in the two-way covariance are disclosed; they are not clipped. '
       'There are only 20 time clusters, so those sensitivities also need caution.')
    code("models=pd.read_csv(RESULTS/'all_outcome_models.csv')\nshow_table(models[['outcome','variant','measure','control_set','formula','beta','se','p','n','corpus','negative_variance_terms']])")
    md('## Interpretation and limitations\nAnnual-report negative language rises within issuers under both weighting '
       'schemes; uncertainty trends differ by form and weight. The pre-volatility control attenuates the uncertainty '
       'coefficient, so much of the association reflects existing volatility. With both controls, pooled '
       'associations remain significant after family adjustment. Adding issuer, calendar-quarter and form effects makes both '
       'uncertainty coefficients negative and insignificant, so a robust within-issuer predictive relationship '
       'is not established. The four-day return test is imprecise. These are different tests '
       'with different evidence; a blanket claim that the sample is too small is not warranted.\n\n'
       'The 2026 holdings snapshot creates survivorship/selection bias. It does not reveal former holdings that '
       'disappeared. Correct acceptance times and contemporaneous share counts do not cure that selection. '
       'Further limits include full-corpus scoring, 20 aggregate quarters, daily timing, overlapping windows, and '
       'multi-class valuation approximations. The next improvement is a historical holdings universe followed by '
       'a held-out forecasting evaluation.\n\n'
       'See the short PDF report for the test-by-test discussion and `AI_USE.md` for the authorship disclosure.')
    md('## Plain-language table guide\nA score is the measured amount of uncertainty or negative language. '
       'One standard deviation is a common scale for comparing coefficients. A score p-value tests a zero '
       'score coefficient; an adjusted p-value accounts for multiple testing. Not applied means no adjustment '
       'was made, not a nonsignificant finding. Parentheses in the PDF contain company-clustered standard errors. '
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
