"""Build a self-contained report in the instructor's ten-section order."""
from __future__ import annotations
import argparse
import json
from html import escape
from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "outputs/analysis"
DEST = ROOT / "output/pdf"
INK = colors.HexColor("#111111")
NAVY = colors.HexColor("#193b58")
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=19,
                         leading=23, textColor=NAVY, spaceAfter=8))
styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=13,
                         leading=16, textColor=NAVY, spaceBefore=9, spaceAfter=6, keepWithNext=True))
styles.add(ParagraphStyle(name="Prose", fontName="Helvetica", fontSize=10.5,
                         leading=13.5, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle(name="Note", fontName="Helvetica", fontSize=9,
                         leading=11.5, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="TableCell", fontName="Helvetica", fontSize=8.5,
                         leading=10.2, textColor=INK))
styles.add(ParagraphStyle(name="TableHead", fontName="Helvetica-Bold", fontSize=8.5,
                         leading=10.2, textColor=colors.white))

def P(text, style="Prose"):
    return Paragraph(text, styles[style])

def pv(x):
    return "&lt;0.001" if x < .001 else f"{x:.3f}"

def tab(headers, rows, widths, compact=False):
    body = [[P(escape(str(h)), "TableHead") for h in headers]]
    body += [[P(str(c), "TableCell") for c in row] for row in rows]
    table = Table(body, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY), ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),4), ("RIGHTPADDING",(0,0),(-1,-1),4),
        ("TOPPADDING",(0,0),(-1,-1),1.5 if compact else 3),
        ("BOTTOMPADDING",(0,0),(-1,-1),1.5 if compact else 3),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#eef3f6"),colors.white]),
        ("LINEBELOW",(0,-1),(-1,-1),.4,colors.HexColor("#b5bec5"))]))
    return table

def page_number(canvas, doc, author):
    canvas.setFont("Helvetica",8)
    canvas.setFillColor(INK)
    canvas.drawString(40,24,f"FRE-GY 7871 A | Assignment 1 | {author}")
    canvas.drawRightString(A4[0]-40,24,str(doc.page))

def build(author, netid):
    DEST.mkdir(parents=True, exist_ok=True)
    s = json.loads((RESULTS/"summary.json").read_text())
    e = json.loads((RESULTS/"report_evidence.json").read_text())
    t2,t3,t4,t5,t6 = [pd.read_csv(RESULTS/f"table{i}.csv") for i in range(2,7)]
    models = pd.read_csv(RESULTS/"all_outcome_models.csv")
    coefficients = pd.read_csv(RESULTS/"all_regression_coefficients.csv")
    core = pd.read_csv(ROOT/"data/interim/analysis/scored_text_corpus.csv")
    flows = pd.read_csv(RESULTS/"table1_filings.csv")
    universe = pd.read_csv(RESULTS/"table1_universe.csv")
    corr = {(r["form"],r["weight"]):r["correlation"] for r in s["correlations"]}
    trend = t4.set_index(["form","measure"])
    vol = t5.set_index(["measure","control_set"])
    ret = t6.set_index("measure")
    case = e["case"]
    candidates = pd.read_csv(RESULTS/"measure_contrast_candidates.csv")
    pypl = candidates.loc[candidates.accession.eq(case["accession"])].iloc[0]
    labels = {"negative_prop":"Negative %", "negative_tfidf":"Negative TF-IDF",
              "uncertainty_prop":"Uncertainty %","uncertainty_tfidf":"Uncertainty TF-IDF"}
    w = 515
    story = [
        P("Uncertainty and Sentiment in ARK Company Filings","ReportTitle"),
        P(f'{escape(author)} | NetID: {escape(netid)} | Fall 2026<br/>'
          '<link href="https://github.com/victor4628/FRE7871-NLP">github.com/victor4628/FRE7871-NLP</link>',"Note"),
        P("1. What I did","Section"),
        P(f'I study {s["core_filings"]:,} filings from {s["core_firms"]} companies in the ARK holdings universe, '
          'submitted during 2021-2025. I count negative and uncertainty words, compare proportions with TF-IDF, '
          'test language trends, and relate uncertainty to subsequent stock volatility and negative language to '
          'four-day excess returns. The strongest result is rising negative language within annual reports; '
          'incremental volatility prediction and pooled return prediction are not established.'),
        P("2. Data construction","Section")]
    story.append(tab(["Security / company screen","Removed","Remain"],
                     [[escape(r["filter"]),str(r.removed),str(r.remaining)] for _,r in universe.iterrows()],
                     [375,65,75]))
    story.append(Spacer(1,6))
    rows = [["Downloaded security-filing records","0","1,702"],
            ["Duplicate Alphabet accessions (retain GOOGL)","20","1,682"]]
    for _,r in flows.iloc[1:].iterrows():
        label = "Missing filing share count needed for size control" if r["filter"] == "Complete share count, controls and outcomes" else escape(r["filter"])
        rows.append([label,str(r.removed),str(r.remaining)])
    story.append(tab(["Table 1. Sequential filing screens","Removed","Remain"],rows,[375,65,75]))
    story += [
        P('The last row is an additional regression-data requirement: one JOBY filing has no usable share count, '
          'so size cannot be calculated. No further filing is lost to other controls or outcomes. All exhibits use '
          'this common sample. The earliest-filing rule uses submission quarter, across form types; it removes '
          '14 distinct 10-Qs, not duplicate text.','Note'),
        P(f'Day 0 follows the assignment: convert acceptance time to Eastern; shift its date forward one day at '
          f'or after 16:00; take the later of that date and the filing date, then the next available trading day. '
          f'This moves {s["shifted_event_days"]} retained filings. Share counts are read from the same filing cover '
          'or a dated same-accession fact, never a later report. Prices and shares are aligned for splits.','Note'),
        P('Parsing keeps visible inline-XBRL narrative, removes hidden resources, and strips tables with more than '
          '15% digits among non-space characters. The uppercase tokenizer retains words of at least two characters; '
          'there is no stemming or stopword removal. No filing failed parsing.','Note'),
        PageBreak(),
        P("3. Word lists","Section"),
        P(f'The Loughran-McDonald dictionary supplies 2,355 Negative words and 297 Uncertainty words; '
          f'{s["lexicon_overlap"]} occur in both lists. Negative words describe adverse conditions; uncertainty '
          'words qualify what may happen or what is known. Shared words and shared disclosure topics mean these '
          'are conceptually different but empirically related measures.'),
        P("4. Method","Section"),
        P('For each filing, the proportional measure is list-word occurrences divided by all tokens. '
          'TF-IDF downweights repetition and words that occur in many documents. For term i in document j:'),
        P('<b>w<sub>ij</sub> = [(1 + ln tf<sub>ij</sub>) / (1 + ln a<sub>j</sub>)] ln(N / df<sub>i</sub>)</b>','Note'),
        P('The weight is zero if tf is zero. Here tf is the term count, a is total tokens divided by distinct tokens, '
          'N is the number of documents and df is the number containing the term. A category score sums these weights. '
          'Natural logs reproduce the instructor checks: 0.8480, 0.2885, 0.5026. IDF is recomputed within each '
          'pooled or form-specific regression corpus.','Note'),
        P('For trends, each company receives equal weight within form and filing quarter. Separate 10-K and 10-Q '
          'series remove the seasonal form-mix problem. Aggregate regressions use time and quarter-of-year effects; '
          'Newey-West standard errors with four lags allow serial correlation. The within-company model adds company '
          'effects, comparing changes inside the same company. Company-clustered errors allow its repeated filings to be related.'),
        P('For market outcomes, each language measure enters as a continuous regressor. Reported proportional-score '
          'coefficients are effects per 1 percentage-point increase in words (for example, 1.8% to 2.8%); reported TF-IDF '
          'coefficients are effects per 1 TF-IDF unit. The estimation code standardizes scores internally, then rescales '
          'the coefficients and standard errors to these original units. This does not change fitted values, t-statistics or p-values.'),
        P('Both models include log size (day -1 price times filing shares), log mean daily dollar volume and stock-minus-SPY '
          'buy-and-hold return over [-60,-6], report type, company effects and calendar-quarter effects. Table 5 adds '
          'log prior volatility only in its second specification; Table 6 includes it. The code uses a 10-Q dummy with '
          '10-K as reference, algebraically equivalent to a 10-K dummy with the intercept changed.','Note'),
        P('Realized volatility is daily-return sample SD multiplied by sqrt(252): 55 returns on [-60,-6] before '
          'and 60 on [+4,+63] after. The four-day return compounds days [0,+3] from the day -1 close, then subtracts '
          'the corresponding SPY return. No missing returns are filled. Outcome errors cluster by company.','Note'),
        P("5. What the measures are made of","Section"),
        P("Table 2. Filing-level summary statistics, by report type","Note")]
    story.append(tab(["Form / measure","N","Mean","SD","P25","Median","P75"],
        [[r.form+" / "+labels[r.measure],f"{r.n:,.0f}",f'{r["mean"]:.3f}',f"{r.sd:.3f}",
          f"{r.p25:.3f}",f'{r["median"]:.3f}',f"{r.p75:.3f}"] for _,r in t2.iterrows()],
        [161,44,62,62,62,62,62],True))
    story += [P('Proportions are percentages of all words; TF-IDF is the sum of term weights. P25 and P75 are percentiles.','Note'),PageBreak(),
              P("Table 3. Thirty most frequent words on each list","Section"),
              P("Each share is the word's fraction of all occurrences on its own list.","Note")]
    neg,unc = [t3.loc[t3.category.eq(cat)].reset_index(drop=True) for cat in ["Negative","Uncertainty"]]
    story.append(tab(["Rank","Negative word","List share","Uncertainty word","List share"],
        [[i+1,neg.iloc[i].word,f"{neg.iloc[i].share_pct:.2f}%",unc.iloc[i].word,f"{unc.iloc[i].share_pct:.2f}%"] for i in range(30)],
        [34,157,70,184,70],True))
    matched,eligible = e["sentences_reappearing_in_prior_risk_section"],e["uncertainty_sentences_at_least_12_tokens"]
    story += [
        P(f'<b>Q1. What is each measure actually made of?</b> The top ten words contribute {s["top10_negative_share"]:.1f}% of Negative '
          f'and {s["top10_uncertainty_share"]:.1f}% of Uncertainty occurrences. Uncertainty therefore measures much '
          'recurring conditional language, not just fresh managerial doubt. In PayPal\'s 2024-filed 10-K, '
          f'{matched}/{eligible} ({100*matched/eligible:.1f}%) uncertainty-containing sentences in Risk Factors also '
          'appear in its previous annual report after token normalization (minimum 12 words). Repeated warnings concern '
          'cyberattacks, fraud and business interruptions. This is direct evidence of retained risk disclosure in that case; '
          'it does not show that all uncertainty language across the sample is copied.'),
        P(f'<b>Q2. Are sentiment and uncertainty measuring different things?</b> Pooled correlations are {corr[("All","prop")]:.3f} (proportions) '
          f'and {corr[("All","tfidf")]:.3f} (TF-IDF); within 10-K they are {corr[("10-K","prop")]:.3f}/{corr[("10-K","tfidf")]:.3f}, '
          f'and within 10-Q {corr[("10-Q","prop")]:.3f}/{corr[("10-Q","tfidf")]:.3f}. These are largely overlapping '
          'disclosure measures, not two independent confirmations. '
          f'<link href="{case["doc_url"]}">PayPal\'s 10-K filed {case["filing_date"]}</link> (fiscal year ended '
          f'{case["report_date"]}) illustrates a difference: Negative is {100*case["negative_prop"]:.3f}% '
          f'(89th percentile of 10-Ks), Uncertainty {100*case["uncertainty_prop"]:.3f}% (25th). Its discussion of '
          'transaction losses, credit-loss provisions and fraud protection raises Negative counts; some words describe '
          'ordinary business risks, rather than new bad news. Its four-day SPY excess return is '
          f'{case["excess_return"]:.2f}%; annualized volatility falls from {100*case["pre_vol"]:.2f}% to '
          f'{100*case["post_vol"]:.2f}%. Those are descriptive case outcomes, not evidence that the wording caused them.'),
        PageBreak(),P("6. Trends, 2021-2025","Section"),
        P('Figure 1 separates report types and averages companies equally. Table 4 further adjusts for company identity '
          'and quarter-of-year seasonality. These corrections address changing form and company composition before interpreting trends.'),
        P("Figure 1. Negative and uncertainty measures by filing quarter; VIX on right axes","Note"),
        Image(str(RESULTS/"figure1.png"),width=w,height=w*7.2/11.5),
        P("Table 4. Time-trend coefficient and t-statistics","Section")]
    story.append(tab(["Form / measure","Aggregate / year","OLS t","NW t","Within / year","Within t","Within p"],
        [[r.form+" / "+labels[r.measure],f"{r.aggregate_beta:.3f}",f"{r.aggregate_ols_t:.2f}",
          f"{r.aggregate_hac_t:.2f}",f"{r.within_beta:.3f}",f"{r.within_t:.2f}",pv(r.within_p)] for _,r in t4.iterrows()],
        [164,68,43,43,74,56,67],True))
    story += [P('Dependent variable: the named language measure. Predictor: linear time in years. Proportional slopes '
                'are percentage points/year; TF-IDF slopes are term-weight units/year. OLS and NW t-statistics refer '
                'to the aggregate model; within t and p use company-clustered errors.','Note')]
    kn,knt,ku,kut,qn,qnt,qu,qut = [trend.loc[key] for key in [
        ("10-K","negative_prop"),("10-K","negative_tfidf"),("10-K","uncertainty_prop"),("10-K","uncertainty_tfidf"),
        ("10-Q","negative_prop"),("10-Q","negative_tfidf"),("10-Q","uncertainty_prop"),("10-Q","uncertainty_tfidf")]]
    story += [
        P(f'<b>Q3. Did either measure trend over 2021-2025?</b> I lead with the required within-company model because it removes '
          'stable differences between companies, not because it produces a preferred sign. Its similarity to the aggregate '
          'result supports the direction after that correction. Annual Negative rises '
          f'{kn.within_beta:.3f} percentage points/year (t={kn.within_t:.2f}) and {knt.within_beta:.3f} TF-IDF units/year '
          f'(t={knt.within_t:.2f}). Annual Uncertainty rises proportionally ({ku.within_beta:.3f} points/year, '
          f't={ku.within_t:.2f}) but not in TF-IDF (t={kut.within_t:.2f}). Quarterly Negative has no clear trend; '
          f'quarterly Uncertainty falls {qu.within_beta:.3f} points/year (t={qu.within_t:.2f}) and '
          f'{qut.within_beta:.3f} TF-IDF units/year (t={qut.within_t:.2f}). This supports some real within-company '
          'language change rather than a trend created entirely by composition; it does not prove management became '
          'more pessimistic or uncertain.'),
        PageBreak(), P("7. Uncertainty, volatility and returns","Section"),
        P("Table 5A. Does uncertainty predict subsequent volatility? Full sample","Section"),
        P('Dependent variable: log annualized volatility on [+4,+63]. Main independent variable: continuous uncertainty, '
          'computed separately as proportion or TF-IDF. Columns distinguish whether prior volatility is omitted or included. '
          'All columns include size, dollar volume, prior excess return, report type, company and calendar-quarter effects.','Note')]
    selected = [vol.loc[(m,c)] for m in ["uncertainty_prop","uncertainty_tfidf"]
                for c in ["without_pre_volatility","with_pre_volatility"]]
    def coefficient_cells(term, statistic):
        values=[]
        for model in selected:
            found=coefficients.loc[coefficients.model.eq(model.model)&coefficients.term.eq(term)]
            values.append("-" if found.empty else f"{found.iloc[0][statistic]:.4f}")
        return values
    def reported_scale(model):
        measure = model["measure"] if "measure" in model.index else model.name
        if isinstance(measure, tuple):
            measure = measure[0]
        return .01/model.score_sd if measure.endswith("_prop") else 1/model.score_sd
    def score_cells(models_to_show, statistic):
        return [f"{r[statistic]*reported_scale(r):.4f}" for r in models_to_show]
    rows=[["Uncertainty coefficient"]+score_cells(selected,"beta"),
          ["Uncertainty clustered SE"]+score_cells(selected,"se"),
          ["Prior-volatility coefficient"]+coefficient_cells("log_pre_vol","beta"),
          ["Prior-volatility clustered SE"]+coefficient_cells("log_pre_vol","se"),
          ["Uncertainty p-value"]+[pv(r.p) for r in selected],
          ["Filings / companies"]+[f"{r.n:,} / {r.firms}" for r in selected]]
    story.append(tab(["Variable / statistic","Proportion / Without prior-vol control","Proportion / With prior-vol control",
                      "TF-IDF / Without prior-vol control","TF-IDF / With prior-vol control"],rows,
                     [167,87,87,87,87]))
    story.append(P('Proportion coefficients are per 1 percentage point of all words; TF-IDF coefficients are per 1 '
                   'term-weight unit. Standard errors cluster by company.','Note'))
    a,b,c,d=selected
    ar,br,cr,dr=[r.beta*reported_scale(r) for r in selected]
    story.append(P(f'<b>Q4. Does uncertainty language predict volatility?</b> Adding prior volatility changes the proportional coefficient from {ar:.4f} to '
        f'{br:.4f} log points per percentage point, and TF-IDF from {cr:.4f} to {dr:.4f} log points per unit. The declines are '
        f'{100*(1-b.beta/a.beta):.1f}% and {100*(1-d.beta/c.beta):.1f}%, consistent with prior volatility capturing pre-existing '
        'risk. However, the no-prior-volatility coefficients are already imprecise after the other required controls and '
        'fixed effects, so this sample does not reproduce the anticipated large unadjusted relation; the controlled estimates '
        'show no incremental predictive content.'))
    story += [P("Table 6. Does negative language predict four-day excess returns?","Section"),
              P('Outcome: stock-minus-SPY buy-and-hold return on [0,+3], in percentage points. Predictor: continuous '
                'Negative proportion or TF-IDF. Controls: log size, log dollar volume, prior excess return and volatility, '
                'plus report type, company and quarter effects. Effects are per 1 percentage point or 1 TF-IDF unit.','Note')]
    story.append(tab(["Negative-language predictor","Coefficient","Clustered SE","t","p","80% MDE"],
        [[labels[r.measure]+(" (+1 pp)" if r.measure.endswith("_prop") else " (+1 unit)"),
          f"{r.beta*reported_scale(r):.3f}",f"{r.se*reported_scale(r):.3f}",f"{r.t:.2f}",pv(r.p),
          f"{r.mde80*reported_scale(r):.3f} pp"] for _,r in t6.iterrows()],
        [164,75,75,42,50,109]))
    r1,r2=ret.loc["negative_prop"],ret.loc["negative_tfidf"]
    story += [P(f'N={r1.n:,} filings and {r1.firms} company clusters. Approximate 80%-power minimum detectable effect '
        f'(MDE) = (t critical at 5%, two-sided + 0.842) x clustered SE: '
        f'{r1.mde80*reported_scale(r1):.3f} return percentage points per 1 proportion point and '
        f'{r2.mde80*reported_scale(r2):.3f} return percentage points per TF-IDF unit. '
        'These are precision diagnostics for detecting effects, not measured test power.','Note'),
        P('<b>Q6. Which of your results do you believe?</b> I have the most confidence in the direction of the annual-report '
          'Negative trend within this selected sample. Proportion and TF-IDF both rise inside companies, with t-statistics '
          f'of {kn.within_t:.2f} and {knt.within_t:.2f}, and the aggregate estimates point the same way. This supports a '
          'change in filing language among surviving ARK issuers. It does not establish that their underlying businesses '
          'became more negative, because dictionary counts also capture recurring legal and accounting language.'),
        P('I do not believe the evidence supports a general rise in Uncertainty. The annual proportion rises but annual '
          'TF-IDF does not, whereas both quarterly estimates fall; the measures are reacting differently to common hedging '
          'words and less common terms. For volatility, I believe the strong persistence in volatility and the absence of '
          'clear incremental information in the pooled language scores: after prior volatility is added, both uncertainty '
          f'estimates are imprecise, with 95% intervals of [{b.ci_low*reported_scale(b):.3f}, '
          f'{b.ci_high*reported_scale(b):.3f}] log points per proportion point and '
          f'[{d.ci_low*reported_scale(d):.3f}, {d.ci_high*reported_scale(d):.3f}] per TF-IDF unit. The isolated controlled '
          '10-K TF-IDF p-value in section 8 is exploratory because it is one of several form/weight specifications and no '
          'formal interaction test shows that 10-K and 10-Q effects differ. The return coefficients are negative, but their '
          'confidence intervals include zero and the MDEs are large. I therefore treat the return result as inconclusive, '
          'rather than evidence of no effect.'),
        P("8. 10-K versus 10-Q","Section"),
        P("<b>Table 5B. Uncertainty and subsequent volatility, by filing type.</b> Table 5A estimates one common slope "
          "from all filings; Table 5B estimates the same model separately for 10-K and 10-Q. Every row uses Uncertainty; "
          "headings state the weighting and prior-volatility choice. Other controls are unchanged, and IDF is recomputed "
          "within each form.","Note")]
    rows=[]
    for form in ["10-K","10-Q"]:
        for measure in ["uncertainty_prop","uncertainty_tfidf"]:
            sample=models.loc[models.outcome.eq("volatility")&models.variant.eq(form)&models.measure.eq(measure)].set_index("control_set")
            va,vb=sample.loc["without_pre_volatility"],sample.loc["with_pre_volatility"]
            rows.append([form,"Proportion (+1 pp)" if measure.endswith("prop") else "TF-IDF (+1 unit)",
                         f"{va.beta*reported_scale(va):.3f} / {pv(va.p)}",
                         f"{vb.beta*reported_scale(vb):.3f} / {pv(vb.p)}",f"{vb.n:,}"])
    story.append(tab(["Form","Uncertainty weighting","Without prior-vol control: coefficient / p",
                      "With prior-vol control: coefficient / p","N"],rows,[43,139,135,135,63]))
    fk,fq=e["forms"]["10-K"],e["forms"]["10-Q"]
    story += [
        P(f'<b>Q5. Do 10-Qs behave like 10-Ks?</b> The forms do not behave identically. Median length is {fq["median_words"]:,.0f} words for '
          f'10-Q versus {fk["median_words"]:,.0f} for 10-K. Negative-proportion SD is '
          f'{fq["negative_prop_sd_pp"]:.3f} versus {fk["negative_prop_sd_pp"]:.3f} percentage points; Uncertainty SD '
          f'is {fq["uncertainty_prop_sd_pp"]:.3f} versus {fk["uncertainty_prop_sd_pp"]:.3f}. A shorter denominator '
          'can make a proportion more sensitive to a few changed words; repeated templates can instead suppress '
          'within-company variation. The observed overall variance is higher for 10-Q, but length alone does not explain it.'),
        P('Annual reports contain a fuller discussion of business risks, so they are a plausible source of more '
          'company-specific text. That is a hypothesis, not a result of having more pages. Only annual Uncertainty '
          'TF-IDF is significant in the controlled form-specific volatility test; annual proportions and both quarterly '
          'measures are not. Different significance levels do not prove the forms differ. Table 4 similarly shows an '
          'annual Negative increase and a quarterly Uncertainty decline, not a common form-independent trend.'),
        P('A 10-Q can arrive close to an earnings release, which may reveal information first or fall within the event '
          'window. Earnings-release timestamps are not matched here. Therefore, even a significant filing-date return '
          'association would not isolate the incremental effect of the 10-Q text.'),
        P("9. Limitations","Section")]
    years=core.groupby("cik").filing_date.apply(lambda x:pd.to_datetime(x).dt.year.nunique())
    arkk=models.loc[models.outcome.eq("return")&models.variant.eq("ARKK")].set_index("measure")
    arkk_prop,arkk_tfidf=arkk.loc["negative_prop"],arkk.loc["negative_tfidf"]
    story += [P(f'The 2026 holdings snapshot selects survivors; failed or exited former holdings are missing, '
        f'and only {int(years.eq(5).sum())}/{s["core_firms"]} retained issuers appear in every filing year. Thus '
        'trends among survivors need not describe the historical ARK portfolio or the broader market. Only 20 filing '
        'quarters identify the aggregate time trend, so Newey-West inference is approximate in a short series.'),
        P('The dictionary does not read context, negation or whether a sentence is new. The concentration of Uncertainty '
          'counts and the PayPal repetition result show that template language can drive scores. TF-IDF uses the full '
          'analysis corpus to calculate document frequencies, so it is retrospective rather than investable in real time. '
          'Daily event timing cannot separate filing text from simultaneous earnings news, and the multi-class share '
          'aggregation used for size is an approximation.'),
        P('The current report includes aggregate and within-company trends; full-sample and form-specific volatility '
          'models with and without prior volatility; and SPY and ARKK return benchmarks. Multiple related tests raise '
          'the chance of an isolated small p-value. With ARKK, Negative coefficients are '
          f'{arkk_prop.beta*reported_scale(arkk_prop):.3f} per proportion point (p={pv(arkk_prop.p)}) and '
          f'{arkk_tfidf.beta*reported_scale(arkk_tfidf):.3f} per TF-IDF unit (p={pv(arkk_tfidf.p)}); the imprecise pooled '
          'return conclusion persists.'),
        P('Earlier exploratory work also ran no-control, size-only, prior-volatility-only and size-plus-volatility outcome '
          'models, an issuer/time-effects sensitivity, a shell-company screen, a temporary sample without the $3 cutoff, '
          'and a return-quintile plot. The September 7 instructions superseded those choices. They are disclosed in '
          'AI_USE.md and were not used to choose the reported conclusion. The PayPal repetition check remains one case, '
          'not a corpus-wide duplication estimate.'),
        P("10. What I would do next","Section"),
        P('The single change that would most improve the test is reconstructing point-in-time ARK membership from dated '
          'holdings archives, then including each company only during periods when an ARK fund actually held it. This '
          'would restore firms later sold, delisted or failed and directly test whether the conclusions survive outside '
          'today\'s selected survivors. The cost is reconciling ticker, name and CIK changes and recovering filings plus '
          'delisting-adjusted prices; missing archives may also shrink the usable sample.'),
        P('Sources: Loughran and McDonald (2011), Journal of Finance 66, 35-65; instructor assignment sheet and '
          '<link href="https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1">repository instructions</link>; '
          'SEC EDGAR; Yahoo Finance. Saved calculations, full regression coefficients and filing-text comparisons are in '
          'the notebook. AI assistance is disclosed in AI_USE.md.','Note')]
    target=DEST/"assignment1_report.pdf"
    footer=lambda canvas, doc: page_number(canvas,doc,author)
    SimpleDocTemplate(str(target),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=32,bottomMargin=40,
                      title="Uncertainty and Sentiment in ARK Company Filings",author=author).build(
                      story,onFirstPage=footer,onLaterPages=footer)
    print(target)

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--author",required=True)
    parser.add_argument("--netid",required=True)
    args=parser.parse_args()
    build(args.author,args.netid)
