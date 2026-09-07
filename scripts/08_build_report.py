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
    controlled=table5.loc[table5.pre_vol_control]
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
    for i in range(len(vol)):
        name=vol.iloc[i]['filter'] if i<len(vol)-1 else 'Complete outcome window and benchmark'
        rows.append([escape(name),f'{vol.iloc[i].removed} / {vol.iloc[i].remaining}',f'{ret.iloc[i].removed} / {ret.iloc[i].remaining}'])
    story.append(tab(['Market screen (separate branches)','Vol: removed / left','Return: removed / left'],rows,[309,100,100]))
    story += [Spacer(1,6),P('The initial 31 losses are 7 unresolved SEC ticker mappings and 24 mapped securities without an eligible '
                           '10-K/10-Q in the window. Filing counts for those excluded securities are not observed and are not invented. '
                           'The 93 eligible securities represent 92 issuers because GOOG and GOOGL share filings. '
                           'Explicitly reported shells are excluded. The optional $3 price cutoff was removed at the student\'s request; '
                           'low-priced stocks remain eligible. Legacy shell checkboxes and ordinary-share cover wording were corrected. '
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
                f'The corrected parser retains {s["parser_new_words"]:,} tokens across unique downloads versus {s["parser_old_words"]:,} '
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
              P('Size uses dated common shares from the same filing and day -1 nominal price; subsequent split adjustments are reversed. '
                'Turnover uses split-consistent pre-filing volume and the filing share count. Multiple common classes are summed and valued '
                'at the selected class price, an approximation. Weighted-average EPS shares are excluded from the main analysis. '
                'Models control for log size, log turnover, prior return, form, two-digit SIC and calendar-quarter effects; controlled models '
                'also include log prior volatility. Standard errors cluster by issuer.','SmallNote')]
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
    story += [P('Figure 1  Tone and market uncertainty','Section'),
              P('Each line first averages filings within issuer, form and filing quarter, then weights issuers equally. '
                'Annual and quarterly reports remain separate. VIX is the quarterly mean on the right axis; it is a market comparison, '
                'not the dependent variable in the firm-volatility regressions.','SmallNote'),
              Image(str(RESULTS/'figure1.png'),width=w,height=w*7.2/11.5),
              P('Table 4  Aggregate and within-issuer trends','Section')]
    rows=[]
    for _,r in table4.iterrows():
        rows.append([r.form,label[r.measure],f(r.aggregate_beta,4),f(r.aggregate_ols_t,2),f(r.aggregate_hac_t,2),
                     f(r.within_beta,4),pv(r.within_p),pv(r.within_holm_p)])
    story.append(tab(['Form','Measure','Agg. slope','OLS t','NW t','Within slope','p','Holm p'],rows,[35,115,62,45,45,67,70,70]))
    story += [P('Slopes are SDs per quarter. Aggregate models include quarter-of-year effects, with Bartlett Newey-West SEs (4 lags, '
                'finite-sample correction) alongside naive OLS t statistics. Within-issuer models include issuer and seasonal effects '
                'and issuer-clustered SEs; issuers observed in only one quarter are omitted from that test. Holm adjustment covers the '
                'four within-issuer tests separately for each weighting scheme. Redundant fixed-effect columns are removed algebraically.','SmallNote'),
              P('The within-issuer results, rather than the pooled chart, support the main trend interpretation. Annual-report negative '
                'language rises under both weights. Uncertainty does not have one universal trend: annual-report proportional uncertainty '
                'rises while its TF-IDF counterpart does not; quarterly-report uncertainty declines. Changing report mix and issuer mix '
                'therefore cannot be ignored. With only 20 aggregate quarters, even corrected aggregate inference is fragile.','SmallNote')]
    story.append(PageBreak())
    story += [P('Table 5  Uncertainty and subsequent volatility','Section'),
              P('The dependent variable is log annualized post-filing volatility. Each coefficient is for a one-SD increase in the '
                'uncertainty score. Paired models share the same complete-case sample and IDF corpus; only the pre-volatility control changes.')]
    rows=[]
    for _,r in table5.iterrows():
        rows.append(['Proportion' if r.measure.endswith('prop') else 'TF-IDF','Yes' if r.pre_vol_control else 'No',
                     f(r.beta,4),f(r.se,4),pv(r.p),pv(r.get('holm_p')),f(r.n,0)])
    story.append(tab(['Weight','Prior vol.','Coefficient','Cluster SE','p','Holm p','N'],rows,[90,60,88,78,65,65,63]))
    passages=[]
    for weight in ['prop','tfidf']:
        a=table5.loc[table5.measure.eq('uncertainty_'+weight)&~table5.pre_vol_control].iloc[0]
        b=table5.loc[table5.measure.eq('uncertainty_'+weight)&table5.pre_vol_control].iloc[0]
        reduction=100*(1-b.beta/a.beta)
        passages.append(f'{"Proportional" if weight=="prop" else "TF-IDF"} uncertainty falls from {a.beta:.4f} to {b.beta:.4f} '
                        f'after controlling for prior volatility, a {reduction:.1f}% attenuation. The controlled estimate corresponds '
                        f'to about {100*(math.exp(b.beta)-1):.1f}% higher volatility per SD.')
    story += [Spacer(1,9),P(' '.join(passages)),
              P('The attenuation is the central result: hedged language partly describes companies that were already volatile. '
                'The controlled coefficients are conditional associations, not evidence that the words cause volatility. '
                'They are modest and their family-adjusted p values are less compelling than the unadjusted tests. '
                'Holm adjustment here covers the two controlled volatility and two return tests together.'),
              P('Declared robustness checks','Section')]
    vr=all_models.loc[all_models.outcome.eq('volatility') & all_models.pre_vol_control & ~all_models.variant.eq('pooled')]
    rows=[]
    for variant in ['10-K','10-Q','firm_FE','two_way']:
        d=vr.loc[vr.variant.eq(variant)]
        vals=[]
        for weight in ['prop','tfidf']:
            r=d.loc[d.measure.str.endswith(weight)].iloc[0]
            vals.extend([f(r.beta,4),pv(r.p)])
        rows.append([variant.replace('_',' ')]+vals)
    story.append(tab(['Specification','Prop. coefficient','p','TF-IDF coefficient','p'],rows,[125,115,65,129,75]))
    story += [Spacer(1,8),P('The form-specific rows re-estimate IDF within that form. Firm effects replace industry effects. '
                          'Two-way clustering uses issuer and calendar quarter; there are only 20 quarter clusters. '
                          'The two-way covariance can have negative nuisance-parameter variances in this finite sample; '
                          'these are logged, not set to zero, and target coefficients with invalid variances are reported as NA. '
                          'The complete coefficient tables preserve all estimated specifications.','SmallNote'),
              P('Replacing industry effects with issuer effects makes both uncertainty coefficients negative and insignificant. '
                'The positive pooled association therefore depends on between-issuer differences; robust incremental prediction '
                'within issuers is not established. Trend, volatility and return tests answer different questions. '
                'Sample selection and overlapping outcome windows further limit interpretation.')]
    story.append(PageBreak())
    story += [P('Table 6  Sentiment and four-day excess returns','Section'),
              P('Before interpreting significance, consider precision. Approximate 80%-power minimum detectable effects are '
                f'{table6.iloc[0].mde80:.2f} and {table6.iloc[1].mde80:.2f} percentage points per SD for proportional and TF-IDF sentiment, '
                'using (cluster-t critical + 0.842) times the clustered SE. This is a design-precision diagnostic, not observed power.')]
    terms=[('tone_z','Negative tone (1 SD)'),('log_market_value','Log market value'),('log_turnover','Log turnover'),
           ('pre_return','Prior 63-day return'),('log_pre_vol','Log prior volatility')]
    rows=[]
    for term,label_ in terms:
        values=[]
        for _,model in table6.iterrows():
            r=coefficients.loc[coefficients.model.eq(model.model)&coefficients.term.eq(term)].iloc[0]
            values.append(f'{r.beta:.3f}<br/>({r.se:.3f})')
        rows.append([label_]+values)
    for label_,column,format_ in [('N','n',0),('Issuer clusters','firms',0),('Adjusted R squared','adj_r2',3),('Tone p','p',3),('Tone Holm p','holm_p',3)]:
        rows.append([label_]+[f(r[column],format_) for _,r in table6.iterrows()])
    story.append(tab(['Regressor / statistic','Proportion','TF-IDF'],rows,[245,132,132]))
    story += [P('Dependent variable: stock minus SPY buy-and-hold return, in percentage points. Parentheses contain issuer-clustered SEs. '
                'Form, two-digit SIC and calendar-quarter effects are included but not printed. Both tone coefficients are negative '
                'and statistically imprecise. A null here is compatible with economically nontrivial effects and does not invalidate '
                'the separate trend or volatility tests.','SmallNote')]
    rr=all_models.loc[all_models.outcome.eq('return') & ~all_models.variant.eq('pooled')]
    rows=[]
    for variant in ['10-K','10-Q','firm_FE','two_way','ARKK','active_negative']:
        d=rr.loc[rr.variant.eq(variant)]
        vals=[]
        for weight in ['prop','tfidf']:
            r=d.loc[d.measure.str.endswith(weight)].iloc[0]
            vals.append(f'{r.beta:.3f} / '+pv(r.p))
        rows.append([variant.replace('_',' ')] + vals)
    story += [P('Return sensitivities (coefficient / p)','SmallNote'),tab(['Specification','Proportion','TF-IDF'],rows,[245,132,132]),Spacer(1,7)]
    full_years=core.groupby('cik').filing_date.apply(lambda x:pd.to_datetime(x).dt.year.nunique())
    story += [P('Limits and next step','Section'),
              P(f'The 124-security universe is selected from 2026 holdings snapshots, not historical ARK ownership. '
                f'Only {int(full_years.eq(5).sum())} of {s["core_firms"]} retained issuers appear in all five filing years. '
                'The number of formerly held firms missing from this snapshot cannot be established from the supplied data. '
                'Survivorship can distort trends as well as return tests; fixed effects do not remove this selection. Other limits are '
                '20 aggregate quarters, full-corpus rather than live scoring, noisy daily event timing, multi-class valuation proxies, '
                'and overlapping post-filing windows. My highest-priority extension is a historical holdings universe with inclusion dates, '
                'followed by a genuinely held-out forecasting test.','SmallNote'),
              P('Sources: Loughran and McDonald (2011), Journal of Finance 66(1), 35-65, equation (1); Fall 2026 assignment brief; '
                '<link href="https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1">instructor starter repository</link>; '
                '<link href="https://sraf.nd.edu/loughranmcdonald-master-dictionary/">LM dictionary documentation</link>; '
                '<link href="https://help.yahoo.com/kb/SLN28256.html">Yahoo price-adjustment documentation</link>; '
                '<link href="https://github.com/gerrymanoim/exchange_calendars">exchange_calendars</link>; '
                '<link href="https://www.statsmodels.org/">statsmodels</link>. AI assistance is disclosed in AI_USE.md.','SmallNote')]
    target=DEST/'assignment1_report.pdf'
    doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=43,leftMargin=43,topMargin=36,bottomMargin=40,
                          title='Uncertainty and Sentiment in ARK Company Filings',author=author)
    doc.build(story,onFirstPage=page_number,onLaterPages=page_number)
    print(target)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--author',required=True);ap.add_argument('--netid',required=True)
    args=ap.parse_args();build(args.author,args.netid)
