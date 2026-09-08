"""Render the short assignment report directly from computed outputs."""
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
RESULTS = ROOT / "outputs" / "analysis"
DEST = ROOT / "output" / "pdf"
NAVY = colors.HexColor("#193b58")
GRAY = colors.HexColor("#52616d")
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="ReportTitle", fontName="Helvetica-Bold", fontSize=20,
                          leading=24, textColor=NAVY, spaceAfter=8))
styles.add(ParagraphStyle(name="Section", fontName="Helvetica-Bold", fontSize=12.5,
                          leading=15, textColor=NAVY, spaceBefore=7, spaceAfter=6))
styles.add(ParagraphStyle(name="Prose", fontName="Helvetica", fontSize=8.7,
                          leading=11.2, spaceAfter=6))
styles.add(ParagraphStyle(name="SmallNote", fontName="Helvetica", fontSize=7.25,
                          leading=9.2, textColor=GRAY, spaceAfter=5))
styles.add(ParagraphStyle(name="TableCell", fontName="Helvetica", fontSize=7.25, leading=8.7))
styles.add(ParagraphStyle(name="TableHead", fontName="Helvetica-Bold", fontSize=7.25,
                          leading=8.7, textColor=colors.white))


def P(text, style="Prose"):
    return Paragraph(text, styles[style])


def f(x, digits=3):
    return "NA" if pd.isna(x) else f"{x:,.{digits}f}"


def pv(x):
    return "NA" if pd.isna(x) else ("&lt;0.001" if x < .001 else f"{x:.3f}")


def tab(headers, rows, widths):
    body = [[P(escape(str(h)), "TableHead") for h in headers]]
    body += [[P(str(c), "TableCell") for c in row] for row in rows]
    table = Table(body, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#eef3f6"), colors.white]),
        ("LINEBELOW", (0, -1), (-1, -1), .4, colors.HexColor("#c4cdd4")),
    ]))
    return table


def page_number(canvas, doc):
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(43, 25, "FRE-GY 7871 A  |  Assignment 1")
    canvas.drawRightString(A4[0] - 43, 25, str(doc.page))


def score_cell(row):
    return f"{row.beta:.4f}<br/>({row.se:.4f})"


def build(author, netid):
    DEST.mkdir(parents=True, exist_ok=True)
    s = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    table2 = pd.read_csv(RESULTS / "table2.csv")
    table3 = pd.read_csv(RESULTS / "table3.csv")
    table4 = pd.read_csv(RESULTS / "table4.csv")
    table5 = pd.read_csv(RESULTS / "table5.csv")
    table6 = pd.read_csv(RESULTS / "table6.csv")
    models = pd.read_csv(RESULTS / "all_outcome_models.csv")
    coefs = pd.read_csv(RESULTS / "all_regression_coefficients.csv")
    flows = pd.read_csv(RESULTS / "table1_filings.csv")
    universe = pd.read_csv(RESULTS / "table1_universe.csv")
    core = pd.read_csv(ROOT / "data/interim/analysis/scored_text_corpus.csv", dtype={"cik": str})
    candidates = pd.read_csv(RESULTS / "measure_contrast_candidates.csv")
    width = 509
    story = []

    story += [P("Uncertainty and Sentiment<br/>in ARK Company Filings", "ReportTitle"),
              P(f"{escape(author)} | NetID {escape(netid)} | Fall 2026", "SmallNote"),
              P('Repository: <link href="https://github.com/victor4628/FRE7871-NLP">github.com/victor4628/FRE7871-NLP</link>', "SmallNote"),
              P(f'I measure negative language and uncertainty in {s["core_filings"]:,} 10-K/10-Q filings from '
                f'{s["core_firms"]} ARK-universe issuers during 2021-2025. I compare proportional counts with '
                'Loughran-McDonald TF-IDF, test form-specific trends, then relate uncertainty to subsequent '
                'volatility and negative language to the four-day filing return.'),
              P("Table 1  Sample construction", "Section")]
    story.append(tab(["Security and issuer screen", "Removed", "Remain"],
                     [[escape(r["filter"]), str(r.removed), str(r.remaining)] for _, r in universe.iterrows()],
                     [369, 65, 75]))
    story.append(Spacer(1, 6))
    story.append(tab(["Unique-filing screen", "Removed", "Remain"],
                     [[escape(r["filter"]), str(r.removed), str(r.remaining)] for _, r in flows.iterrows()],
                     [369, 65, 75]))
    story += [Spacer(1, 5),
              P('The 1,702 security-filing records include 20 duplicate Alphabet records; retaining GOOGL leaves '
                '1,682 unique filings. The form-specific word thresholds remove none. The company-quarter rule removes '
                '14, the $3 price rule removes 108, the 60-day history rule removes 23, and one JOBY filing lacks a '
                'usable filing-date share count. No filing failed parsing.', "SmallNote"),
              P(f'Day 0 is the first exchange session on or after the later of the filing date and the SEC acceptance '
                f'date, shifted one day when acceptance is at or after 16:00 Eastern. This moves {s["shifted_event_days"]:,} '
                'retained filings. Shares come from the same filing; common classes are summed only when no consolidated '
                'total exists. Visible inline-XBRL text is retained, hidden material is removed, and tables above 15% '
                'digits are stripped.', "SmallNote")]

    story.append(PageBreak())
    story += [P("Word lists and method", "Section"),
              P(f'The LM lists contain 2,355 Negative and 297 Uncertainty words, overlapping on {s["lexicon_overlap"]} '
                'words. Proportions divide list-word occurrences by all tokens. For term i in document j, equation (1) is:<br/>'
                '<b>w<sub>ij</sub> = [(1 + ln tf<sub>ij</sub>) / (1 + ln a<sub>j</sub>)] ln(N / df<sub>i</sub>)</b> for tf &gt; 0; '
                'otherwise zero, where a<sub>j</sub> is total tokens divided by distinct tokens. Category TF-IDF is the '
                'sum of its term weights. Natural logs are used.'),
              P('The repository self-check gives TF-IDF values 0.8480, 0.2885 and 0.5026 for documents d1-d3. '
                'IDF is recomputed on each regression corpus. The quarterly chart first averages within issuer, form '
                'and filing quarter, then weights issuers equally. Table 4 adds seasonal effects; its preferred '
                'within-company model also adds issuer effects and clusters standard errors by issuer. Aggregate '
                'Newey-West errors use four lags because quarterly residuals may be serially correlated.', "SmallNote"),
              P('Tables 5-6 include log filing-date market value, log average dollar volume and SPY excess return over '
                '[-60,-6], a 10-K indicator, company effects and calendar-quarter effects. Table 5 compares models '
                'without and with log pre-filing volatility. Volatility is annualized from [-60,-6] before and [+4,+63] '
                'after. Table 6 uses stock minus SPY buy-and-hold return over [0,+3], measured from the day -1 close. '
                'Outcome-model standard errors cluster by company.', "SmallNote"),
              P("Table 2  Summary statistics by form", "Section")]
    labels = {"negative_prop": "Negative %", "negative_tfidf": "Negative TF-IDF",
              "uncertainty_prop": "Uncertainty %", "uncertainty_tfidf": "Uncertainty TF-IDF"}
    t2_indexed = table2.set_index(["form", "measure"])
    t4_indexed = table4.set_index(["form", "measure"])
    story.append(tab(["Form / measure", "N", "Mean", "SD", "P25", "Median", "P75"],
                     [[r.form + " / " + labels[r.measure], f(r.n, 0), f(r["mean"]), f(r.sd),
                       f(r.p25), f(r["median"]), f(r.p75)] for _, r in table2.iterrows()],
                     [161, 43, 61, 61, 61, 61, 61]))
    form_corr = {(x["form"], x["weight"]): x["correlation"] for x in s["correlations"]}
    story.append(P('Negative-uncertainty correlations are 10-K: '
                   f'{form_corr[("10-K", "prop")]:.3f} proportional and {form_corr[("10-K", "tfidf")]:.3f} TF-IDF; '
                   f'10-Q: {form_corr[("10-Q", "prop")]:.3f} and {form_corr[("10-Q", "tfidf")]:.3f}.', "SmallNote"))

    story.append(PageBreak())
    story += [P("Table 3  Words driving each measure", "Section"),
              P('Each share divides a word count by all occurrences on its own list. The two lists appear side by side.', "SmallNote")]
    neg = table3.loc[table3.category.eq("Negative")].reset_index(drop=True)
    unc = table3.loc[table3.category.eq("Uncertainty")].reset_index(drop=True)
    rows = [[str(i + 1), escape(neg.iloc[i].word), f(neg.iloc[i].share_pct, 2) + "%",
             escape(unc.iloc[i].word), f(unc.iloc[i].share_pct, 2) + "%"] for i in range(30)]
    story.append(tab(["Rank", "Negative word", "List share", "Uncertainty word", "List share"],
                     rows, [35, 175, 65, 169, 65]))
    may = float(unc.loc[unc.word.eq("MAY"), "share_pct"].iloc[0])
    could = float(unc.loc[unc.word.eq("COULD"), "share_pct"].iloc[0])
    q2 = candidates.loc[(candidates.weight.eq("prop"))
                        & (candidates.direction.eq("high negative / low uncertainty"))].iloc[0]
    story += [Spacer(1, 5),
              P(f'<b>Q1. What is each measure actually made of?</b> The ten leading words supply '
                f'{s["top10_negative_share"]:.1f}% of Negative counts and {s["top10_uncertainty_share"]:.1f}% of '
                f'Uncertainty counts; the top 30 supply {s["top30_negative_share"]:.1f}% and '
                f'{s["top30_uncertainty_share"]:.1f}%. MAY and COULD alone supply {may + could:.1f}%. Together with '
                'RISK/RISKS, this looks mainly like recurring risk-factor language rather than filing-specific managerial '
                'hedging. I did not estimate sentence-level duplication, so “copied forward unchanged” remains an interpretation.', "SmallNote"),
              P(f'<b>Q2. Are sentiment and uncertainty measuring different things?</b> Pooled correlations are '
                f'{form_corr[("All", "prop")]:.3f} for proportions and {form_corr[("All", "tfidf")]:.3f} for TF-IDF. '
                f'{q2.ticker}\'s {str(q2.filing_date)[:4]} 10-K is a contrast: its Negative proportion is at the '
                f'{100*q2.negative_prop_percentile:.0f}th percentile but Uncertainty at the '
                f'{100*q2.uncertainty_prop_percentile:.0f}th, driven by losses, fraud, regulatory penalties and litigation. '
                'The high correlations mean much of the report is one shared disclosure-intensity result; differing trends '
                'and outcome coefficients show the measures are related, not identical.', "SmallNote")]

    story.append(PageBreak())
    story += [P("Figure 1  Language scores and VIX", "Section"),
              P('Annual and quarterly reports remain separate; issuer weighting prevents frequent filers from dominating. '
                'VIX is a market comparison, not the firm-volatility outcome.', "SmallNote"),
              Image(str(RESULTS / "figure1.png"), width=width, height=width * 7.2 / 11.5),
              P("Table 4  Trends, aggregate and within company", "Section")]
    rows = []
    for _, r in table4.iterrows():
        rows.append([r.form, labels[r.measure], f(r.aggregate_beta, 3), f(r.aggregate_ols_t, 2),
                     f(r.aggregate_hac_t, 2), f(r.within_beta, 3), f(r.within_t, 2), pv(r.within_p)])
    story.append(tab(["Form", "Measure", "Overall change/year", "OLS t", "NW t",
                      "Within-company change/year", "Within t", "Within p"],
                     rows, [35, 105, 72, 43, 43, 83, 50, 56]))
    story += [P('Proportional changes are percentage points per year; TF-IDF changes are term-weight units per year. '
                'Aggregate regressions include seasonal effects. Within-company regressions include issuer and seasonal '
                'effects and issuer-clustered errors.', "SmallNote"),
              P(f'<b>Q3. Did either measure trend over 2021-2025?</b> I trust the within-company model because it removes '
                f'stable company differences and accounts for repeated filings. In 10-Ks, Negative rises '
                f'{t4_indexed.loc[("10-K", "negative_prop"), "within_beta"]:.3f} percentage points/year '
                f'(t={t4_indexed.loc[("10-K", "negative_prop"), "within_t"]:.2f}) and '
                f'{t4_indexed.loc[("10-K", "negative_tfidf"), "within_beta"]:.3f} TF-IDF units/year '
                f'(t={t4_indexed.loc[("10-K", "negative_tfidf"), "within_t"]:.2f}). Negative does not trend in 10-Qs '
                f'({t4_indexed.loc[("10-Q", "negative_prop"), "within_beta"]:.3f} points/year, '
                f't={t4_indexed.loc[("10-Q", "negative_prop"), "within_t"]:.2f}; TF-IDF '
                f't={t4_indexed.loc[("10-Q", "negative_tfidf"), "within_t"]:.2f}). 10-K Uncertainty rises proportionally '
                f'({t4_indexed.loc[("10-K", "uncertainty_prop"), "within_beta"]:.3f} points/year, '
                f't={t4_indexed.loc[("10-K", "uncertainty_prop"), "within_t"]:.2f}) but not with TF-IDF '
                f'(t={t4_indexed.loc[("10-K", "uncertainty_tfidf"), "within_t"]:.2f}), while 10-Q Uncertainty falls '
                f'most clearly under TF-IDF ({t4_indexed.loc[("10-Q", "uncertainty_tfidf"), "within_beta"]:.3f} '
                f'units/year, t={t4_indexed.loc[("10-Q", "uncertainty_tfidf"), "within_t"]:.2f}). '
                'The evidence supports within-company change for 10-K '
                'negative language and 10-Q uncertainty, rather than a single pooled trend.', "SmallNote")]

    story.append(PageBreak())
    story += [P("Table 5  Uncertainty and subsequent volatility", "Section"),
              P('The dependent variable is log annualized volatility on [+4,+63]. Both columns contain all controls '
                'listed on page 2; the second additionally includes log volatility on [-60,-6]. Scores are standardized '
                f'within the same {s["core_filings"]:,}-filing sample. Parentheses contain company-clustered standard errors.')]
    for weight, title in [("prop", "Proportion"), ("tfidf", "TF-IDF")]:
        d = table5.loc[table5.measure.eq("uncertainty_" + weight)].set_index("control_set")
        without = d.loc["without_pre_volatility"]
        with_pre = d.loc["with_pre_volatility"]
        prior = coefs.loc[(coefs.model.eq(with_pre.model)) & coefs.term.eq("log_pre_vol")].iloc[0]
        story += [P(title, "SmallNote"),
                  tab(["Variable / statistic", "Without prior volatility", "With prior volatility"],
                      [["Uncertainty score (+1 standard deviation)", score_cell(without), score_cell(with_pre)],
                       ["Prior volatility (log)", "-", f"{prior.beta:.4f}<br/>({prior.se:.4f})"],
                       ["Score p-value", pv(without.p), pv(with_pre.p)],
                       ["Number of filings", f(without.n, 0), f(with_pre.n, 0)]],
                      [225, 142, 142]), Spacer(1, 6)]
    prop = table5.loc[table5.measure.eq("uncertainty_prop")].set_index("control_set")
    tfidf = table5.loc[table5.measure.eq("uncertainty_tfidf")].set_index("control_set")
    story += [P(f'<b>Q4. Does uncertainty language predict volatility?</b> Adding prior volatility changes the '
                f'proportional coefficient from {prop.loc["without_pre_volatility", "beta"]:.4f} to '
                f'{prop.loc["with_pre_volatility", "beta"]:.4f}, a '
                f'{100*(1-prop.loc["with_pre_volatility", "beta"]/prop.loc["without_pre_volatility", "beta"]):.1f}% '
                f'attenuation. TF-IDF falls from {tfidf.loc["without_pre_volatility", "beta"]:.4f} to '
                f'{tfidf.loc["with_pre_volatility", "beta"]:.4f}, a '
                f'{100*(1-tfidf.loc["with_pre_volatility", "beta"]/tfidf.loc["without_pre_volatility", "beta"]):.1f}% '
                'attenuation. Neither controlled coefficient is precise. Existing volatility explains most of the '
                'proportional association and much of the TF-IDF association; uncertainty does not robustly predict '
                'a change in volatility.', "SmallNote"),
              P("Q5. Do 10-Qs behave like 10-Ks?", "Section")]
    form_vol = models.loc[(models.outcome.eq("volatility")) & models.variant.isin(["10-K", "10-Q"])]
    rows = []
    for form in ["10-K", "10-Q"]:
        for weight, title in [("prop", "Proportion"), ("tfidf", "TF-IDF")]:
            d = form_vol.loc[(form_vol.variant.eq(form)) & form_vol.measure.eq("uncertainty_" + weight)].set_index("control_set")
            a, b = d.loc["without_pre_volatility"], d.loc["with_pre_volatility"]
            rows.append([form, title, f"{a.beta:.3f} / {pv(a.p)}", f"{b.beta:.3f} / {pv(b.p)}"])
    story += [tab(["Form", "Weight", "Without prior vol: coefficient / p", "With prior vol: coefficient / p"],
                  rows, [48, 75, 193, 193]),
              P(f'10-Q proportional scores vary more despite shorter, more templated reports: Negative SD is '
                f'{t2_indexed.loc[("10-Q", "negative_prop"), "sd"]:.3f}% versus '
                f'{t2_indexed.loc[("10-K", "negative_prop"), "sd"]:.3f}% for 10-K, and Uncertainty SD is '
                f'{t2_indexed.loc[("10-Q", "uncertainty_prop"), "sd"]:.3f}% versus '
                f'{t2_indexed.loc[("10-K", "uncertainty_prop"), "sd"]:.3f}%. A shorter denominator makes '
                'proportions more sensitive to section mix and episodic wording. Because a 10-Q usually follows an '
                'earnings release by only days, daily filing returns cannot separately identify the report from earnings '
                'news. Longer 10-Ks should carry richer textual signal, but Table 5 is mixed: only 10-K TF-IDF is '
                'significant with prior volatility, while its proportional counterpart and both 10-Q estimates are not. '
                'That isolated result is insufficient to establish a form difference.', "SmallNote")]

    story.append(PageBreak())
    story += [P("Table 6  Negative language and four-day excess returns", "Section"),
              P('The dependent variable is stock minus SPY buy-and-hold return over [0,+3], in percentage points. '
                'Controls and fixed effects are those listed on page 2; standard errors cluster by company.')]
    rows = [["Proportion", f(r.beta, 3), f(r.se, 3), f(r.t, 2), pv(r.p), f(r.mde80, 2), f(r.n, 0)]
            for _, r in table6.loc[table6.measure.eq("negative_prop")].iterrows()]
    rows += [["TF-IDF", f(r.beta, 3), f(r.se, 3), f(r.t, 2), pv(r.p), f(r.mde80, 2), f(r.n, 0)]
             for _, r in table6.loc[table6.measure.eq("negative_tfidf")].iterrows()]
    story.append(tab(["Weight", "Coefficient", "SE", "t", "p", "80% MDE", "N"],
                     rows, [120, 75, 65, 55, 55, 85, 54]))
    arkk = models.loc[(models.outcome.eq("return")) & models.variant.eq("ARKK")].set_index("measure")
    ret = table6.set_index("measure")
    story += [P(f'Replacing SPY with ARKK gives {arkk.loc["negative_prop", "beta"]:.3f} (p='
                f'{pv(arkk.loc["negative_prop", "p"])}) and {arkk.loc["negative_tfidf", "beta"]:.3f} '
                f'(p={pv(arkk.loc["negative_tfidf", "p"])}).', "SmallNote"),
              P(f'<b>Q6. Which results do I believe?</b> I believe the 10-K Negative trend because both weights agree '
                f'and the preferred within-company t-statistics are '
                f'{t4_indexed.loc[("10-K", "negative_prop"), "within_t"]:.2f} and '
                f'{t4_indexed.loc[("10-K", "negative_tfidf"), "within_t"]:.2f}. I give less weight to Uncertainty '
                'trends because 10-K proportion and TF-IDF disagree; the 10-Q decline is more credible under TF-IDF '
                'but only borderline under proportions. I believe the volatility comparison: adding prior volatility '
                'materially shrinks both coefficients, and the remaining pooled estimates are imprecise. I do not treat '
                'the isolated 10-K TF-IDF result as robust. The return coefficients are negative under both weights, but '
                f'p-values are {ret.loc["negative_prop", "p"]:.3f} and {ret.loc["negative_tfidf", "p"]:.3f} and the '
                f'approximate 80%-power minimum detectable effects are {ret.loc["negative_prop", "mde80"]:.2f} and '
                f'{ret.loc["negative_tfidf", "mde80"]:.2f} percentage points per SD. This test is underpowered, so it '
                'supports neither return predictability '
                'nor a zero effect.', "SmallNote"),
              P("Limitations and next step", "Section")]
    years = core.groupby("cik").filing_date.apply(lambda x: pd.to_datetime(x).dt.year.nunique())
    story += [P(f'The universe is selected from 2026 holdings snapshots. Only {int(years.eq(5).sum())} of '
                f'{s["core_firms"]} retained issuers appear in every filing year; firms that failed, disappeared or '
                'left ARK before the snapshot cannot enter. Twenty aggregate quarters limit time-series inference. '
                'Full-corpus IDF is retrospective, daily timing cannot separate nearby news, and SPY is an imperfect '
                'benchmark; the ARKK check does not change the return conclusion.', "SmallNote"),
              P('The single best improvement is to reconstruct historical ARK membership and evaluate scores out of '
                'sample. It would require dated holdings archives and rebuilding every filing-level sample by the '
                'company\'s actual inclusion date.', "SmallNote"),
              P('Sources: Loughran and McDonald (2011), Journal of Finance 66(1), 35-65; Fall 2026 assignment brief; '
                '<link href="https://github.com/anmolsingh0219/FRE-GY-7871A-Assignment1">instructor repository</link>; '
                'LM dictionary; Yahoo Finance; exchange_calendars; statsmodels. AI assistance is disclosed in '
                'AI_USE.md.', "SmallNote")]

    target = DEST / "assignment1_report.pdf"
    doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=43, leftMargin=43,
                            topMargin=36, bottomMargin=40,
                            title="Uncertainty and Sentiment in ARK Company Filings", author=author)
    doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--author", required=True)
    parser.add_argument("--netid", required=True)
    args = parser.parse_args()
    build(args.author, args.netid)
