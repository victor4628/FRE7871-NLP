"""Render the short report from computed outputs; never type estimates by hand."""
from __future__ import annotations

import argparse
import json
import math
from html import escape
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'outputs'/'analysis'
DEST=ROOT/'output'/'pdf'
NAVY=colors.HexColor('#193b58')
GRAY=colors.HexColor('#52616d')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle',fontName='Helvetica-Bold',fontSize=20,leading=24,textColor=NAVY,spaceAfter=9))
styles.add(ParagraphStyle(name='Section',fontName='Helvetica-Bold',fontSize=13,leading=16,textColor=NAVY,spaceBefore=8,spaceAfter=7))
styles.add(ParagraphStyle(name='Prose',fontName='Helvetica',fontSize=9.2,leading=12.2,spaceAfter=7))
styles.add(ParagraphStyle(name='SmallNote',fontName='Helvetica',fontSize=7.7,leading=10,textColor=GRAY,spaceAfter=6))
styles.add(ParagraphStyle(name='TableCell',fontName='Helvetica',fontSize=7.7,leading=9.5))
styles.add(ParagraphStyle(name='TableHead',fontName='Helvetica-Bold',fontSize=7.7,leading=9.5,textColor=colors.white))


def P(text,style='Prose'):
    return Paragraph(text,styles[style])


def f(x,d=3):
    return 'NA' if pd.isna(x) else f'{x:,.{d}f}'


def pv(x):
    return 'NA' if pd.isna(x) else ('&lt;0.001' if x<.001 else f'{x:.3f}')


def tab(headers,rows,widths):
    content=[[P(escape(str(h)),'TableHead') for h in headers]]
    content += [[P(str(c),'TableCell') for c in row] for row in rows]
    t=Table(content,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#eef3f6'),colors.white]),
        ('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#c4cdd4'))]))
    return t


def page_number(canvas,doc):
    canvas.setFont('Helvetica',8);canvas.setFillColor(GRAY)
    canvas.drawString(43,25,'FRE-GY 7871 A  |  Assignment 1')
    canvas.drawRightString(A4[0]-43,25,str(doc.page))


def control_panels(models, coefficients):
    panels=[]
    score_label = 'Uncertainty score' if models.iloc[0].outcome == 'volatility' else 'Negative-language score'
    for weight, label in [('prop','Proportion'),('tfidf','TF-IDF')]:
        d=models.loc[models.measure.str.endswith(weight)].set_index('control_set').loc[
            ['none','size','volatility','both']]
        rows=[]
        for term, title in [('score_z',score_label+'<br/>(+1 standard deviation)'),
                            ('log_market_value','Company size (log market value)'),
                            ('log_pre_vol','Prior volatility (log)')]:
            values=[]
            for _, model in d.iterrows():
                found=coefficients.loc[coefficients.model.eq(model.model)&coefficients.term.eq(term)]
                values.append('-' if found.empty else f'{found.iloc[0].beta:.4f}<br/>({found.iloc[0].se:.4f})')
            rows.append([title]+values)
        rows += [['Number of filings']+[f(r.n,0) for _,r in d.iterrows()],
                 ['Score p-value']+[pv(r.p) for _,r in d.iterrows()],
                 ['Adjusted p-value (Holm)']+[('Not applied' if pd.isna(r.holm_p) else pv(r.holm_p)) for _,r in d.iterrows()]]
        panels += [P(label,'SmallNote'),
                   tab(['Variable / statistic','No controls','Size only','Prior volatility','Both controls'],rows,[137,93,93,93,93]),
                   Spacer(1,7)]
    return panels


def build(author,netid):
    DEST.mkdir(parents=True,exist_ok=True)
    s=json.loads((RESULTS/'summary.json').read_text())
    table2=pd.read_csv(RESULTS/'table2.csv')
    table3=pd.read_csv(RESULTS/'table3.csv')
    table4=pd.read_csv(RESULTS/'table4.csv')
    table5=pd.read_csv(RESULTS/'table5.csv')
    table6=pd.read_csv(RESULTS/'table6.csv')
    all_models=pd.read_csv(RESULTS/'all_outcome_models.csv')
    coefficients=pd.read_csv(RESULTS/'all_regression_coefficients.csv')
    flows=pd.read_csv(RESULTS/'table1_filings.csv')
    features=pd.read_csv(ROOT/'data/interim/analysis/filing_features.csv',dtype={'cik':str})
    core=pd.read_csv(ROOT/'data/interim/analysis/scored_text_corpus.csv',dtype={'cik':str})
    family=table4.loc[table4.measure.eq('negative_prop') & table4.form.eq('10-K')].iloc[0]
    controlled=table5.loc[table5.control_set.eq('both')]
    w=509
    story=[]
    story += [P('Uncertainty and Sentiment<br/>in ARK Company Filings','ReportTitle'),
              P(f'{escape(author)} | NetID {escape(netid)} | Fall 2026','SmallNote'),
              P('Repository: <link href="https://github.com/victor4628/FRE7871-NLP">github.com/victor4628/FRE7871-NLP</link>','SmallNote'),
              P(f'I examine financial negative language and uncertainty in {s["core_filings"]:,} eligible 10-K/10-Q filings from '
                f'{s["core_firms"]} ARK-held issuers, filed during 2021-2025. The clearest evidence is a rise in negative '
                'language within annual-report issuers. Uncertainty trends depend on report type and weighting. '
                'Its association with subsequent volatility weakens after controlling for existing volatility. '
                'Four-day return estimates are imprecise; they do not establish either predictability or the absence of an effect.'),
              P('Table 1  Sample construction','Section')]
    uni=pd.read_csv(RESULTS/'table1_universe.csv')
    story.append(tab(['Security and issuer screen','Removed','Remain'],
                     [[escape(r['filter']),str(r.removed),str(r.remaining)] for _,r in uni.iterrows()],[369,65,75]))
    story.append(Spacer(1,7))
    flowrows=[['Downloaded security-filing records','0','1,702'],
              ['Duplicate Alphabet records (retain GOOGL)','20','1,682']]
    for _,r in flows.loc[flows.branch.eq('text')].iloc[1:].iterrows():
        flowrows.append([escape(r['filter']),str(r.removed),str(r.remaining)])
    story.append(tab(['Unique filing screen','Removed','Remain'],flowrows,[369,65,75]))
    story.append(Spacer(1,7))
    vol=flows.loc[flows.branch.eq('volatility')].reset_index(drop=True)
    ret=flows.loc[flows.branch.eq('return')].reset_index(drop=True)
    rows=[]
    for i in range(len(vol)-1):
        name=vol.iloc[i]['filter']
        rows.append([escape(name),f'{vol.iloc[i].removed} / {vol.iloc[i].remaining}',f'{ret.iloc[i].removed} / {ret.iloc[i].remaining}'])
    rows += [['63 post-event daily returns available (volatility)',
              f'{vol.iloc[-1].removed} / {vol.iloc[-1].remaining}','Not applicable'],
             ['4 event-day stock and SPY/ARKK returns available',
              'Not applicable',f'{ret.iloc[-1].removed} / {ret.iloc[-1].remaining}']]
    story.append(tab(['Market-data requirement','Volatility: removed / kept','Returns: removed / kept'],rows,[309,100,100]))
    story += [Spacer(1,6),P('The initial 31 losses are 7 unresolved SEC ticker mappings and 24 mapped securities without an eligible '
                           '10-K/10-Q in the window. Filing counts for those excluded securities are not observed and are not invented. '
                           'The 93 eligible securities represent 92 issuers because GOOG and GOOGL share filings. '
                           'Explicitly reported shells are excluded. No minimum share-price threshold is imposed. '
                           'Shell indicators and dated share counts are read from the corresponding reports. '
                           'All download and parsing failures were zero.','SmallNote')]
    story.append(PageBreak())
    story += [P('Measures and identification','Section'),
              P('The instructor-specified LM lists contain 2,355 negative words and 297 uncertainty words. '
                f'They overlap on {s["lexicon_overlap"]} words, so the concepts are distinct but their empirical measures are not independent. '
                'Ten nonzero Negative flags actually mark removed entries; the required list is retained for comparability, '
                'with an active-only list as a sensitivity.'),
              P('For term i in document j, I implement equation (1) as:<br/>'
                '<b>w<sub>ij</sub> = [(1 + ln tf<sub>ij</sub>) / (1 + ln a<sub>j</sub>)] ln(N / df<sub>i</sub>)</b> for tf &gt; 0; otherwise zero.<br/>'
                'Here a<sub>j</sub> is total tokens divided by distinct tokens, not total document length. A category score sums its term weights. '
                'Proportions divide category occurrences by all tokens. IDF is recomputed on the exact document corpus used by each regression, '
                'including restricted sensitivities. This is full-corpus, retrospective scoring, not an out-of-sample forecast.'),
              P(f'Parsing retains visible inline-XBRL text and removes hidden resources and mostly numeric tables (digit share above 15%). '
                f'This extraction retains {s["parser_new_words"]:,} tokens across unique downloads versus {s["parser_old_words"]:,} '
                'under the starter parser, which also deleted visible tagged narrative. The starter uppercase tokenizer is retained; '
                'there is no stemming or stopword removal.'),
              P('Table 2  Summary statistics by form','Section')]
    label={'negative_prop':'Negative %','uncertainty_prop':'Uncertainty %',
           'negative_tfidf':'Negative TF-IDF','uncertainty_tfidf':'Uncertainty TF-IDF'}
    story.append(tab(['Form / measure','N','Mean','SD','P25','Median','P75'],
                     [[r.form+' / '+label[r.measure],f(r.n,0),f(r['mean']),f(r.sd),f(r.p25),f(r['median']),f(r.p75)] for _,r in table2.iterrows()],
                     [161,43,61,61,61,61,61]))
    correlations=s['correlations']
    story.append(P('Negative-uncertainty correlations: '+ '; '.join(f'{r["form"]} {r["weight"]}: {r["correlation"]:.3f}' for r in correlations)+'. '
                   'Shared risk topics, overlapping vocabulary and document structure can make the scores move together. '
                   'The separate outcome tests do not assume statistical independence.','SmallNote'))
    story += [P('Event timing and controls','Section'),
              P(f'Day 0 is the first exchange session closing strictly after the SEC acceptance timestamp, including early closes; '
                f'{s["shifted_event_days"]:,} core filings move from their filing date. Four-day return is stock buy-and-hold return '
                'over [0,3] minus SPY buy-and-hold return. Volatility is daily-return SD times sqrt(252): [-63,-1] before and [4,66] '
                'after, excluding the four-day reaction. All 63 returns are required; missing prices are never filled.'),
              P('Size is log market value: dated common shares from the same filing times day -1 nominal price, with split units aligned. '
                'It is an optional research control, included because company scale may affect both disclosure language and market behavior. '
                'Multiple common classes are summed and valued '
                'at the selected class price, an approximation. Weighted-average EPS shares are excluded. '
                'Tables 5-6 compare no controls, size only, prior volatility only and both on a common sample. '
                'The primary models contain no other controls or fixed effects. Prior return and turnover are not calculated. '
                'The 63 preceding returns provide prior volatility; size needs one preceding closing price and a share count. '
                'Standard errors cluster by issuer.','SmallNote'),
              P('Reading the tables','Section'),
              P('The score row is the estimated association for a one-standard-deviation increase in the named language score. '
                'In Table 5 the score measures uncertainty; in Table 6 it measures negative language. Parentheses show the uncertainty of the estimated coefficient: standard '
                'errors allowing repeated reports from the same company to be related. The score p-value tests a zero score '
                'coefficient. The Holm-adjusted p-value accounts for multiple tests; Not applied means no adjustment was made '
                'for that column, not that its result is insignificant. Log means natural logarithm. SD means standard deviation; '
                'P25/P75 are the 25th/75th percentiles. The intercept is a fitted baseline and is included in every model.','SmallNote')]
    story.append(PageBreak())
    story += [P('Table 3  Words driving each measure','Section'),
              P('Shares below divide each word count by all occurrences of words on its own list, not by all words in the filings. '
                f'The top 30 words account for {s["top30_negative_share"]:.1f}% of Negative occurrences and '
                f'{s["top30_uncertainty_share"]:.1f}% of Uncertainty occurrences. Uncertainty is particularly concentrated, '
                'which makes common-word downweighting consequential.')]
    neg=table3.loc[table3.category.eq('Negative')].reset_index(drop=True)
    unc=table3.loc[table3.category.eq('Uncertainty')].reset_index(drop=True)
    rows=[[str(i+1),escape(neg.iloc[i].word),f(neg.iloc[i].share_pct,2)+'%',escape(unc.iloc[i].word),f(unc.iloc[i].share_pct,2)+'%'] for i in range(30)]
    story.append(tab(['Rank','Negative word','List share','Uncertainty word','List share'],rows,[35,175,65,169,65]))
    story += [Spacer(1,8),P('A frequently used word can dominate proportional counts yet convey little cross-document distinction. '
                           'Equation (1) reduces that contribution through document frequency, while log term frequency dampens repetition. '
                           'A high TF-IDF value can also reflect unusual vocabulary and document structure; it is not a probability of bad news.','SmallNote')]
    story.append(PageBreak())
    story += [P('Figure 1  Language scores and VIX','Section'),
              P('Each line first averages filings within issuer, form and filing quarter, then weights issuers equally. '
                'Annual and quarterly reports remain separate. VIX is the quarterly mean on the right axis; it is a market comparison, '
                'not the dependent variable in the firm-volatility regressions.','SmallNote'),
              Image(str(RESULTS/'figure1.png'),width=w,height=w*7.2/11.5),
              P('Table 4  Overall trends and changes within companies','Section')]
    rows=[]
    for _,r in table4.iterrows():
        rows.append([r.form,label[r.measure],f(r.aggregate_beta,4),f(r.aggregate_ols_t,2),f(r.aggregate_hac_t,2),
                     f(r.within_beta,4),pv(r.within_p),pv(r.within_holm_p)])
    story.append(tab(['Form','Measure','Overall slope','OLS t','NW t','Within-company slope','Within-company p','Adjusted p (Holm)'],rows,[35,115,62,45,45,67,70,70]))
    story += [P('Slopes are standard deviations per quarter. OLS means ordinary least squares; NW means Newey-West. Aggregate models include quarter-of-year effects, with Bartlett Newey-West SEs (4 lags, '
                'finite-sample correction) alongside naive OLS t statistics. Within-company models include issuer and seasonal effects '
                'and company-clustered SEs; issuers observed in only one quarter are omitted from that test. Holm adjustment covers the '
                'four within-company tests separately for each weighting scheme. Redundant fixed-effect columns are removed algebraically.','SmallNote'),
              P('The within-company results, rather than the pooled chart, support the main trend interpretation. Annual-report negative '
                'language rises under both weights. Uncertainty does not have one universal trend: annual-report proportional uncertainty '
                'rises while its TF-IDF counterpart does not; quarterly-report uncertainty declines. Changing report mix and issuer mix '
                'therefore cannot be ignored. With only 20 aggregate quarters, even corrected aggregate inference is fragile.','SmallNote')]
    story.append(PageBreak())
    story += [P('Table 5  Uncertainty and subsequent volatility','Section'),
              P('The outcome is log annualized volatility on days [4,66]. Each panel compares exactly the same filings and '
                'standardized uncertainty scores under four control choices. No controls means the uncertainty score plus an intercept; size is log market value '
                'and volatility is log prior volatility. Parentheses contain company-clustered SEs.')]
    story += control_panels(table5, coefficients)
    passages=[]
    for weight in ['prop','tfidf']:
        d=table5.loc[table5.measure.eq('uncertainty_'+weight)].set_index('control_set')
        passages.append(f'{"Proportion" if weight=="prop" else "TF-IDF"}: adding prior volatility changes the uncertainty-score coefficient '
                        f'from {d.loc["none","beta"]:.4f} to {d.loc["volatility","beta"]:.4f} without size, '
                        f'and from {d.loc["size","beta"]:.4f} to {d.loc["both","beta"]:.4f} holding size constant.')
    story += [P(' '.join(passages)),
              P('Adding size to the prior-volatility model raises the uncertainty coefficient. Conditional on prior volatility, '
                'uncertainty is positively associated with company size, while size has a negative coefficient in the full model. '
                'Omitting size therefore lowers the uncertainty coefficient. The change reflects a different conditional comparison, '
                'not stronger evidence of causation.','SmallNote'),
              P('Prior volatility accounts for much of the pooled association. With both controls, the remaining association '
                'is significant after Holm adjustment across the four both-control outcome tests. This is a conditional '
                'association, not evidence that words cause volatility. The other columns show sensitivity to the controls; '
                'their p values are unadjusted.','SmallNote'),
              P('Sensitivity of the model with both controls','Section')]
    vr=all_models.loc[all_models.outcome.eq('volatility') & all_models.control_set.eq('both') & ~all_models.variant.eq('pooled')]
    rows=[]
    for variant in ['10-K','10-Q','firm_FE','two_way']:
        d=vr.loc[vr.variant.eq(variant)]
        values=[]
        for weight in ['prop','tfidf']:
            r=d.loc[d.measure.str.endswith(weight)].iloc[0]
            values.append(f'{r.beta:.4f} / '+pv(r.p))
        readable={'10-K':'Annual reports only','10-Q':'Quarterly reports only',
                  'firm_FE':'Add company/time/type effects','two_way':'Cluster by company and quarter'}
        rows.append([readable[variant]]+values)
    story += [tab(['Specification','Proportion: coefficient / p','TF-IDF: coefficient / p'],rows,[159,175,175]),
              P('Form-specific samples re-estimate IDF. The firm FE sensitivity adds issuer, calendar-quarter and form effects; '
                'both uncertainty coefficients then become negative and insignificant. A robust within-company predictive '
                'relationship is therefore not established. Two-way clustering has only 20 time clusters; invalid nuisance '
                'variances are logged in the notebook.','SmallNote')]
    story.append(PageBreak())
    story += [P('Table 6  Sentiment and four-day excess returns','Section'),
              P('The outcome is stock minus SPY buy-and-hold return over [0,3], in percentage points. The same four models '
                'are estimated on a common sample within each weight. Parentheses contain company-clustered SEs; a dash '
                'means the regressor is omitted, not estimated to be zero.')]
    story += control_panels(table6, coefficients)
    both=table6.loc[table6.control_set.eq('both')].set_index('measure')
    story += [P('All four specifications produce negative but statistically imprecise negative-language coefficients. With both controls, '
                f'the estimates are {both.loc["negative_prop","beta"]:.3f} and {both.loc["negative_tfidf","beta"]:.3f} percentage '
                'points per SD. Failure to reject zero does not establish the absence of an economically meaningful effect.'),
              P('Approximate 80%-power minimum detectable effects for the models with both controls are '
                f'{both.loc["negative_prop","mde80"]:.2f} and {both.loc["negative_tfidf","mde80"]:.2f} percentage points per SD, '
                'using (cluster-t critical + 0.842) times the clustered SE. This is a precision diagnostic, not observed power. '
                'Form-specific, added fixed-effect, two-way-cluster, ARKK-benchmark and active-word-list results are saved '
                'in the notebook. Holm adjustment covers only the four pooled both-control outcome tests.','SmallNote')]
    full_years=core.groupby('cik').filing_date.apply(lambda x:pd.to_datetime(x).dt.year.nunique())
    story += [P('Limits and next step','Section'),
              P(f'The 124-security universe is selected from 2026 holdings snapshots, not historical ARK ownership. '
                f'Only {int(full_years.eq(5).sum())} of {s["core_firms"]} retained issuers appear in all five filing years. '
                'The number of formerly held firms missing from this snapshot cannot be established from the supplied data. '
                'Survivorship can distort trends as well as return tests; fixed effects do not remove this selection. Other limits are '
                '20 aggregate quarters, full-corpus rather than live scoring, noisy daily event timing, multi-class valuation proxies, '
                'and overlapping post-filing windows. A natural extension is a historical holdings universe with inclusion dates, '
                'followed by a genuinely held-out forecasting test.','SmallNote'),
              P('Sources: Loughran and McDonald (2011), Journal of Finance 66(1), 35-65, equation (1); Fall 2026 assignment brief; '
                '<link href="https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1">instructor starter repository</link>; '
                '<link href="https://sraf.nd.edu/loughranmcdonald-master-dictionary/">LM dictionary documentation</link>; '
                '<link href="https://help.yahoo.com/kb/SLN28256.html">Yahoo price-adjustment documentation</link>; '
                '<link href="https://github.com/gerrymanoim/exchange_calendars">exchange_calendars</link>; '
                '<link href="https://www.statsmodels.org/">statsmodels</link>. AI assistance is disclosed in AI_USE.md.','SmallNote')]
    story += [PageBreak(),P('Additional methodological specifications','Section'),
              P('The assignment specifies the principal exhibits, separate negative-language and uncertainty measures, '
                'within-company trend analysis, Newey-West errors for aggregate trends, and a prior-volatility comparison. '
                'The following specifications and supplementary analyses extend those explicit requirements.'),
              P('Sample and measurement','Section'),
              P('Reports must have a valid acceptance timestamp and at least 2,000 extracted words. Explicitly identified '
                'shell-company reports are excluded. Duplicate reports across share classes are consolidated, with GOOGL '
                'representing Alphabet. There is no minimum share-price threshold. The extraction preserves visible tagged '
                'text and removes tables containing more than 15% digits; no stemming or stopword removal is applied. '
                'IDF uses the exact document sample of each specification. Scores are standardized for regression comparisons.'),
              P('Event windows and controls','Section'),
              P('Day 0 is the first exchange session closing after the SEC acceptance timestamp. Event excess returns compound '
                'four daily returns and subtract the SPY return. Prior and subsequent volatility use 63 trading days, '
                '[-63,-1] and [4,66], annualized from sample standard deviations. Models use natural logarithms of volatility '
                'and company market value. Dated shares are matched to the same filing and aligned for splits; valuing multiple '
                'share classes at one class price is an approximation. Complete observations are required on a common sample '
                'for the four control comparisons. Prior cumulative return and turnover are not included.'),
              P('Estimation and statistical inference','Section'),
              P('Quarterly scores first average within company and report type, then equally across companies. Trend models '
                'include seasonal effects; the within-company model includes company effects and at least two observed quarters '
                'per company. The Newey-West implementation uses four lags, Bartlett weights and a finite-sample correction. '
                'Outcome regressions use company-clustered standard errors. Holm adjustment is applied separately to four '
                'within-company trend tests per weight and to the four outcome tests with both controls. The other model '
                'columns report unadjusted p-values. Return-test precision is summarized by an approximate 80%-power '
                'minimum detectable effect.'),
              P('Supplementary analyses and reproducibility','Section'),
              P('Robustness checks separate annual and quarterly reports, add company/calendar-quarter/report-type effects, '
                'use company-and-quarter clustering, replace SPY with ARKK, and exclude retired Negative words. Other '
                'descriptive checks examine dictionary overlap, score correlations, word concentration and median returns '
                'by negative-word-proportion quintile. All estimated specifications are retained. Data audits, ten '
                'numerical and timing tests, saved notebook outputs and reproducible report generation support verification. '
                'AI assistance is disclosed in AI_USE.md. The methodological record is available in METHODOLOGY.md.')]
    target=DEST/'assignment1_report.pdf'
    doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=43,leftMargin=43,topMargin=36,bottomMargin=40,
                          title='Uncertainty and Sentiment in ARK Company Filings',author=author)
    doc.build(story,onFirstPage=page_number,onLaterPages=page_number)
    print(target)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--author',required=True);ap.add_argument('--netid',required=True)
    args=ap.parse_args();build(args.author,args.netid)
