"""Auditable text, point-in-time share counts, and filing-event market variables."""
from __future__ import annotations

import gzip
import json
import re
from collections import Counter
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
from lxml import html

from .config import ROOT, INTERIM_DIR, FILING_DIR, PRICE_DIR, OUTPUT_DIR
from .lexicons import load_master_dictionary, lm_word_lists
from .parse import tokenize, _numeric_share

ANALYSIS = INTERIM_DIR / "analysis"
PARSER_VERSION = "visible-ix-v2"
COVER_VERSION = 3
SHARE_TAG = "dei:entitycommonstocksharesoutstanding"


def local_name(element):
    return str(element.tag).lower() if isinstance(element.tag, str) else ""


def _text(element):
    return re.sub(r"\s+", " ", " ".join(element.itertext())).strip()


def cover_share_facts(root, filing_date):
    """Read current cover-page common shares, retaining dated provenance.

    A consolidated fact wins over component facts. Otherwise only distinct
    common-share-class contexts at the latest date are summed.
    """
    contexts = {e.get("id"): e for e in root.iter() if local_name(e).endswith(":context")}
    facts = []
    for e in root.iter():
        if (e.get("name") or "").lower() != SHARE_TAG:
            continue
        ctx = contexts.get(e.get("contextref"))
        if ctx is None:
            continue
        instants = [_text(n) for n in ctx.iter() if local_name(n).endswith(":instant")]
        if not instants:
            continue
        date = pd.to_datetime(instants[0], errors="coerce")
        if pd.isna(date) or not 0 <= (filing_date - date).days <= 120:
            continue
        members = [n for n in ctx.iter() if local_name(n).endswith(":explicitmember")]
        # Avoid adding unrelated consolidation, geography, or legal-entity facts.
        if any(not any(s in n.get("dimension", "").lower() for s in
                       ["classofstock", "classesofshare", "classofshare", "stockclass"])
               for n in members):
            continue
        member_key = "|".join(sorted(_text(n) for n in members))
        value_text = re.sub(r"[,\s]", "", _text(e))
        if not re.fullmatch(r"\d+(?:\.\d+)?", value_text):
            continue
        value = float(value_text) * 10 ** int(e.get("scale", "0"))
        if value > 0:
            facts.append((date, member_key, value))
    if facts:
        latest = max(f[0] for f in facts)
        current = {(member, value) for date, member, value in facts if date == latest}
        totals = {value for member, value in current if not member}
        if len(totals) == 1:
            return next(iter(totals)), latest, "cover_xbrl_total", ""
        if not totals:
            by_member = {}
            for member, value in current:
                by_member.setdefault(member, set()).add(value)
            if all(len(v) == 1 for v in by_member.values()):
                return sum(next(iter(v)) for v in by_member.values()), latest, "cover_xbrl_class_sum", ""
    return np.nan, pd.NaT, "unresolved", ""


def plain_cover_shares(text, filing_date):
    """Conservative dated cover-sentence fallback for pre-inline-XBRL reports.

    Only 'As of Month DD, YYYY' statements near the front with numeric counts
    explicitly followed by 'shares of ... common stock' are accepted. Every
    accepted sentence is retained for human review. Par values are not counts.
    """
    month = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    for match in re.finditer(rf"(?i)\bas of ({month}\s+\d{{1,2}},?\s+\d{{4}})", text[:18000]):
        date = pd.to_datetime(match.group(1), errors="coerce")
        if pd.isna(date) or not 0 <= (filing_date - date).days <= 120:
            continue
        # The cover sentence ends at the next sentence or the table of contents.
        sentence = re.split(r"(?<!\d)\.(?=\s+[A-Z])|TABLE OF CONTENTS", text[match.end():match.end()+1300],
                            maxsplit=1, flags=re.I)[0]
        if "outstanding" not in sentence.lower():
            continue
        normalized = re.sub(r"(?i)\bc\s+ommon\b", "common", sentence)
        matches = re.findall(
            r"(?i)(\d{1,3}(?:,\d{3})+|\d{6,})\s+(?:shares\s+)?of\s+([^.;]{0,130}?common\s+stock)", normalized
        )
        matches += re.findall(
            r"(?i)(\d{1,3}(?:,\d{3})+|\d{6,})\s+((?:Class\s+[A-Z0-9-]+\s+)?ordinary\s+shares)", normalized
        )
        if matches:
            counts = [int(n.replace(",", "")) for n, _ in matches]
            if all(n > 0 for n in counts):
                return sum(counts), date, "cover_sentence", text[match.start():match.end()] + sentence
    return np.nan, pd.NaT, "unresolved", ""


def shell_status(root, text):
    for e in root.iter():
        if (e.get("name") or "").lower() == "dei:entityshellcompany":
            value, fmt = _text(e).lower(), e.get("format", "").lower()
            if value in {"true", "false"}:
                return value == "true"
            if fmt.endswith("boolballotbox") and value and value in "☒☑⌧☐◻":
                return value in "☒☑⌧"
            if fmt.endswith(("fixed-true", "booleantrue")):
                return True
            if fmt.endswith(("fixed-false", "booleanfalse")):
                return False
    match = re.search(r"(?is)is a shell company.{0,250}?Yes\s*([☒☑⌧☐◻x¨])\s*No\s*([☒☑⌧☐◻x¨])", text[:18000])
    if match:
        yes, no = (v.lower() in "☒☑⌧x" for v in match.groups())
        if yes != no:
            return yes
    return None


def parse_document(raw, filing_date):
    root = html.fromstring(raw, parser=html.HTMLParser(encoding="utf-8"))
    cover_text = _text(root)
    shares = cover_share_facts(root, filing_date)
    if not np.isfinite(shares[0]):
        shares = plain_cover_shares(cover_text, filing_date)
    shell = shell_status(root, cover_text)
    for e in list(root.iter()):
        name = local_name(e)
        style = (e.get("style") or "").replace(" ", "").lower()
        remove = (name in {"script", "style", "ix:header", "ix:hidden", "ix:resources", "ix:references"}
                  or name.startswith(("xbrli:", "xbrldi:", "link:", "xbrl:"))
                  or "display:none" in style or "visibility:hidden" in style)
        if remove and e.getparent() is not None:
            e.drop_tree()
    for e in list(root.iter("table")):
        if e.getparent() is not None and _numeric_share(_text(e)) > 0.15:
            e.drop_tree()
    # itertext preserves visible IX content without retaining markup tokens.
    tokens = tokenize(_text(root))
    return Counter(tokens), shares, shell


def build_text_data(force=False):
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    manifest = ANALYSIS / "text_manifest.json"
    if manifest.exists() and not force:
        saved = json.loads(manifest.read_text())
        if saved["parser_version"] == PARSER_VERSION:
            if saved.get("cover_version") != COVER_VERSION:
                cached, matrix, words = load_text_data()
                review = cached.cover_shares_source.isin(["cover_sentence","unresolved"]) | cached.shell_company.isna()
                for i,row in cached.loc[review].iterrows():
                    root = html.fromstring((FILING_DIR/(row.accession.replace("-","")+".html")).read_bytes(),
                                           parser=html.HTMLParser(encoding="utf-8"))
                    cover_text = _text(root)
                    value, date, source, sentence = plain_cover_shares(cover_text,pd.Timestamp(row.filing_date))
                    if np.isfinite(value) and row.cover_shares_source in ["cover_sentence","unresolved"]:
                        cached.at[i,"cover_shares"] = value
                        cached.at[i,"cover_shares_date"] = date.date().isoformat()
                        cached.at[i,"cover_shares_source"] = source
                        cached.at[i,"cover_sentence"] = sentence
                    cached.at[i,"shell_company"] = shell_status(root, cover_text)
                cached.to_csv(ANALYSIS/"text_metadata.csv",index=False)
                saved["cover_version"] = COVER_VERSION
                manifest.write_text(json.dumps(saved,indent=2))
                return cached,matrix,words
            return load_text_data()
    meta = pd.read_csv(INTERIM_DIR / "filings_meta.csv", dtype={"cik": str, "accession": str})
    # One security per issuer-filing. The explicit Alphabet convention is fixed.
    meta = meta.loc[~meta.ticker.eq("GOOG")].drop_duplicates("accession").reset_index(drop=True)
    meta["filing_date"] = pd.to_datetime(meta.filing_date)
    master = load_master_dictionary()
    lists = lm_word_lists(master)
    vocabulary = sorted(lists["Negative"] | lists["Uncertainty"])
    lookup = {w: i for i, w in enumerate(vocabulary)}
    counts = np.zeros((len(meta), len(vocabulary)), dtype=np.int32)
    rows = []
    for i, row in enumerate(meta.itertuples()):
        source = FILING_DIR / (row.accession.replace("-", "") + ".html")
        counter, shares, shell = parse_document(source.read_bytes(), row.filing_date)
        for word in counter.keys() & lookup.keys():
            counts[i, lookup[word]] = counter[word]
        rows.append({"analysis_words": sum(counter.values()), "analysis_distinct": len(counter),
                     "cover_shares": shares[0], "cover_shares_date": shares[1],
                     "cover_shares_source": shares[2], "cover_sentence": shares[3],
                     "shell_company": shell})
        if (i+1) % 100 == 0:
            print(f"Reparsed text and cover shares: {i+1}/{len(meta)}", flush=True)
    meta = pd.concat([meta, pd.DataFrame(rows)], axis=1)
    meta["text_row"] = np.arange(len(meta))
    meta.to_csv(ANALYSIS / "text_metadata.csv", index=False)
    np.savez_compressed(ANALYSIS / "term_counts.npz", counts=counts, vocabulary=np.array(vocabulary))
    manifest.write_text(json.dumps({"parser_version": PARSER_VERSION, "cover_version": COVER_VERSION,"documents": len(meta),
                                    "words": len(vocabulary)}, indent=2))
    return meta, counts, vocabulary


def load_text_data():
    meta = pd.read_csv(ANALYSIS / "text_metadata.csv", dtype={"cik": str, "accession": str})
    arrays = np.load(ANALYSIS / "term_counts.npz")
    return meta, arrays["counts"], arrays["vocabulary"].tolist()


def score_corpus(meta, counts, vocabulary, active_only=False):
    """Re-estimate IDF using only the specified, unique filing corpus."""
    if not meta.accession.is_unique:
        raise ValueError("TF-IDF corpus must contain unique accessions")
    matrix = counts[meta.text_row.to_numpy(dtype=int)]
    n = len(meta)
    if not n:
        raise ValueError("Empty scoring corpus")
    df = (matrix > 0).sum(axis=0)
    idf = np.zeros(len(vocabulary), dtype=float)
    np.log(np.divide(n, df, out=np.ones(len(df), dtype=float), where=df > 0), out=idf)
    logtf = np.zeros_like(matrix, dtype=float)
    np.log(matrix, out=logtf, where=matrix > 0)
    logtf = np.where(matrix > 0, 1+logtf, 0)
    average = meta.analysis_words.to_numpy() / meta.analysis_distinct.to_numpy()
    weighted = logtf * idf / (1+np.log(average))[:, None]
    master = load_master_dictionary()
    out = meta.copy()
    for category, prefix in [("Negative", "negative"), ("Uncertainty", "uncertainty")]:
        flags = master[category].fillna(0)
        words = set(master.loc[flags.gt(0) if active_only else flags.ne(0), "Word"])
        mask = np.array([w in words for w in vocabulary])
        out[prefix+"_count"] = matrix[:, mask].sum(axis=1)
        out[prefix+"_prop"] = out[prefix+"_count"] / out.analysis_words
        out[prefix+"_tfidf"] = weighted[:, mask].sum(axis=1)
    return out


def nominal_market_data(close, volume, splits):
    """Undo all subsequent splits; the split-date observation is post-split."""
    ratios = splits.reindex(index=close.index, columns=close.columns).fillna(0).replace(0, 1)
    future = ratios.iloc[::-1].cumprod().iloc[::-1] / ratios
    return close * future, volume.reindex_like(close) / future, ratios


def event_position(acceptance, schedule):
    ts = pd.Timestamp(acceptance)
    if ts.tzinfo is None:
        raise ValueError("Acceptance timestamp must be timezone aware")
    ts = ts.tz_convert("UTC")
    # Strict comparison handles a release exactly at close conservatively.
    return int(schedule["close"].searchsorted(ts, side="right"))


def buy_hold(values):
    x = np.asarray(values, dtype=float)
    return float(np.prod(1+x)-1) if len(x) and np.isfinite(x).all() else np.nan


def annual_vol(values):
    x = np.asarray(values, dtype=float)
    return float(np.std(x, ddof=1)*np.sqrt(252)) if len(x) == 63 and np.isfinite(x).all() else np.nan


def build_market_features(meta):
    cal = xcals.get_calendar("XNYS", start="2020-08-01", end="2026-10-01")
    schedule = cal.schedule
    sessions = schedule.index
    prices = pd.read_csv(PRICE_DIR / "prices.csv", index_col=0, parse_dates=True).reindex(sessions)
    returns = prices.pct_change(fill_method=None)
    close = pd.read_csv(PRICE_DIR / "close_split_adjusted.csv", index_col=0, parse_dates=True)
    volume = pd.read_csv(PRICE_DIR / "volume_split_adjusted.csv", index_col=0, parse_dates=True)
    splits = pd.read_csv(PRICE_DIR / "stock_splits.csv", index_col=0, parse_dates=True)
    nominal, actual_volume, ratios = nominal_market_data(close, volume, splits)
    nominal = nominal.reindex(sessions)
    actual_volume = actual_volume.reindex(sessions)
    # Ratios include retrieval-period events for reversing Yahoo's normalization.
    ratios = ratios.reindex(sessions).fillna(1)
    supplied = pd.read_csv(PRICE_DIR / "shares.csv", dtype={"cik": str, "accession": str}).set_index("accession")
    rows = []
    for row in meta.itertuples():
        j = event_position(row.acceptance_datetime, schedule)
        if j < 64 or j+66 >= len(sessions):
            raise ValueError("Calendar range does not cover requested windows")
        day = sessions[j]
        ticker = row.ticker
        stock = returns[ticker]
        pre = stock.iloc[j-63:j]
        post = stock.iloc[j+4:j+67]
        event = stock.iloc[j:j+4]
        pre_vol, post_vol = annual_vol(pre), annual_vol(post)
        stock_event = buy_hold(event)
        shares, asof, source = row.cover_shares, pd.to_datetime(row.cover_shares_date), row.cover_shares_source
        if not np.isfinite(shares) and row.accession in supplied.index:
            f = supplied.loc[row.accession]
            stamp = pd.to_datetime(f.shares_as_of, errors="coerce")
            if (pd.notna(stamp) and 0 <= (pd.Timestamp(row.filing_date)-stamp).days <= 120
                    and "WeightedAverage" not in str(f.shares_tag)
                    and f.shares_outstanding > 0):
                shares, asof, source = f.shares_outstanding, stamp, "same_accession_instant_fact"
        prior_date = sessions[j-1]
        prior_price = nominal.at[prior_date, ticker]
        size = np.nan
        if np.isfinite(shares) and pd.notna(asof) and asof <= pd.Timestamp(row.filing_date):
            # Translate the reported share unit to each price/volume date.
            r = ratios[ticker]
            def shares_on(date):
                if date >= asof:
                    return shares * r.loc[(r.index > asof) & (r.index <= date)].prod()
                return shares / r.loc[(r.index > date) & (r.index <= asof)].prod()
            size = prior_price * shares_on(prior_date)
        filing_date = pd.Timestamp(row.filing_date)
        q = filing_date.to_period("Q")
        rows.append({
            "accession": row.accession, "event_day": day.date().isoformat(),
            "event_shifted": day != filing_date, "quarter": str(q),
            "quarter_of_year": q.quarter, "time": (q.year-2021)*4+q.quarter-1,
            "industry": str(int(row.sic)//100) if pd.notna(row.sic) else "unknown",
            "pre_vol": pre_vol, "post_vol": post_vol,
            "excess_return": 100*(stock_event-buy_hold(returns.SPY.iloc[j:j+4])),
            "excess_return_arkk": 100*(stock_event-buy_hold(returns.ARKK.iloc[j:j+4])),
            "prior_price": prior_price, "market_value": size,
            "shares_used": shares, "shares_date": asof, "shares_source": source,
        })
    out = meta.merge(pd.DataFrame(rows), on="accession", validate="one_to_one")
    for c in ["pre_vol", "post_vol", "market_value"]:
        out["log_"+c] = np.log(out[c].where(out[c] > 0))
    out.to_csv(ANALYSIS / "filing_features.csv", index=False)
    return out
