"""Reproducible filing-level evidence for the report's Q1 and Q2 discussion."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.analysis_data import local_name, _text
from src.parse import tokenize, _numeric_share
from src.config import FILING_DIR
from src.lexicons import lm_word_lists


def narrative(row):
    root = html.fromstring((FILING_DIR / (row.accession.replace('-', '') + '.html')).read_bytes(),
                           parser=html.HTMLParser(encoding='utf-8'))
    for e in list(root.iter()):
        name = local_name(e)
        style = (e.get('style') or '').replace(' ', '').lower()
        if (name in {'script', 'style', 'ix:header', 'ix:hidden', 'ix:resources', 'ix:references'}
                or name.startswith(('xbrli:', 'xbrldi:', 'link:', 'xbrl:'))
                or 'display:none' in style or 'visibility:hidden' in style):
            if e.getparent() is not None:
                e.drop_tree()
    for e in list(root.iter('table')):
        if e.getparent() is not None and _numeric_share(_text(e)) > .15:
            e.drop_tree()
    return _text(root)


def risk_section(text):
    # PYPL's actual headings are uppercase; mixed-case mentions are cross-references.
    starts = list(re.finditer(r'\bITEM\s*1A\s*[.:]?\s*RISK\s+FACTORS\b', text))
    sections = []
    for start in starts:
        end = re.search(r'\bITEM\s*1B\b', text[start.end():])
        if end:
            sections.append(text[start.end():start.end()+end.start()])
    if not sections:
        raise ValueError('Risk Factors / Item 1B boundaries not found')
    return max(sections, key=len)


def main():
    dest = ROOT / 'outputs/analysis'
    core = pd.read_csv(ROOT / 'data/interim/analysis/scored_text_corpus.csv')
    rows = core.loc[core.ticker.eq('PYPL') & core.form.eq('10-K')].sort_values('filing_date')
    current = rows.loc[rows.filing_date.eq('2024-02-08')].iloc[0]
    prior = rows.loc[rows.filing_date.lt(current.filing_date)].iloc[-1]
    text, before = narrative(current), narrative(prior)
    # Confirm the reviewed text is the same text used by the regression scorer.
    assert len(tokenize(text)) == current.analysis_words
    section, old_section = risk_section(text), risk_section(before)
    unc = lm_word_lists()['Uncertainty']
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', section)
                 if len(tokenize(s)) >= 12 and any(w in unc for w in tokenize(s))]
    normalize = lambda s: ' '.join(tokenize(s))
    old_normalized = normalize(old_section)
    matches = [s for s in sentences if normalize(s) in old_normalized]
    all_counts = Counter(tokenize(text))
    risk_counts = Counter(tokenize(section))
    risk_unc = sum(risk_counts[w] for w in unc)
    total_unc = sum(all_counts[w] for w in unc)
    forms = {}
    for form in ['10-K', '10-Q']:
        d = core.loc[core.form.eq(form)]
        forms[form] = {'median_words': float(d.analysis_words.median()),
                       'negative_prop_sd_pp': float(100*d.negative_prop.std()),
                       'uncertainty_prop_sd_pp': float(100*d.uncertainty_prop.std())}
    evidence = {'case': {k: current[k] for k in ['ticker','filing_date','report_date','accession','doc_url',
                         'event_day','negative_prop','uncertainty_prop','negative_tfidf','uncertainty_tfidf',
                         'excess_return','excess_return_arkk','pre_vol','post_vol','analysis_words']},
                'prior_accession': prior.accession, 'prior_filing_date': prior.filing_date,
                'risk_uncertainty_occurrences': risk_unc, 'total_uncertainty_occurrences': total_unc,
                'risk_uncertainty_share': risk_unc/total_unc,
                'uncertainty_sentences_at_least_12_tokens': len(sentences),
                'sentences_reappearing_in_prior_risk_section': len(matches),
                'matched_examples': matches[:12],
                'negative_word_counts': sorted([(w,all_counts[w]) for w in lm_word_lists()['Negative']],
                                               key=lambda x: -x[1])[:12],
                'forms': forms,
                'match_definition': 'Uppercase tokenizer output, punctuation/whitespace normalized; at least 12 tokens. '
                                    'A current uncertainty-containing sentence must appear contiguously in the prior risk section.'}
    serialized = json.dumps(evidence, indent=2, default=lambda value: value.item())
    (dest/'report_evidence.json').write_text(serialized, encoding='utf-8')
    print(serialized)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
