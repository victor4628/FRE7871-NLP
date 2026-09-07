"""Audit downloaded inputs without dropping or changing any observations.

Run after scripts 00 through 03. Outputs stay under the ignored outputs/ folder.
This audits acquisition, not the regression sample or the final event-day rule.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import (  # noqa: E402
    FORMS, INTERIM_DIR, LM_MASTER_DICT_PATH, OUTPUT_DIR, PRICE_DIR,
    ROOT, SAMPLE_END, SAMPLE_START, UNIVERSE_DIR,
)
from src.lexicons import load_master_dictionary  # noqa: E402
from src.parse import tokenize  # noqa: E402


def main() -> int:
    meta = pd.read_csv(INTERIM_DIR / "filings_meta.csv",
                       dtype={"cik": str, "accession": str})
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    prices = pd.read_csv(PRICE_DIR / "prices.csv", index_col=0, parse_dates=True)
    volume = pd.read_csv(PRICE_DIR / "volume.csv", index_col=0, parse_dates=True)
    shares = pd.read_csv(PRICE_DIR / "shares.csv",
                         dtype={"cik": str, "accession": str})
    dictionary = load_master_dictionary()
    eligible = universe.loc[universe.status.eq("domestic_filer")]
    expected = int(eligible.n_10k.sum() + eligible.n_10q.sum())
    errors: list[str] = []
    warnings: list[str] = []

    if len(meta) != expected:
        errors.append(f"Expected {expected} filings, downloaded {len(meta)}.")
    if meta.duplicated(["ticker", "accession"]).any():
        errors.append("Duplicate ticker-accession rows.")
    duplicate_accessions = int(meta.accession.duplicated().sum())
    if duplicate_accessions:
        warnings.append(
            f"{duplicate_accessions} repeated filing accessions across securities; "
            "multiple share classes must not duplicate issuer-level text in the analysis."
        )
    meta.loc[meta.accession.duplicated(keep=False)].to_csv(
        OUTPUT_DIR / "repeated_filing_accessions.csv", index=False
    )
    if shares.accession.duplicated().any():
        errors.append("Duplicate share-count accessions.")
    dates = pd.to_datetime(meta.filing_date, errors="coerce")
    acceptance = pd.to_datetime(meta.acceptance_datetime, utc=True, errors="coerce")
    if not dates.between(SAMPLE_START, SAMPLE_END).all():
        errors.append("Missing or out-of-window filing dates.")
    if acceptance.isna().any():
        errors.append("Missing or invalid acceptance timestamps.")
    if not meta.form.isin(FORMS).all():
        errors.append("Unexpected filing form.")
    if not set(meta.ticker).issubset(set(eligible.ticker)):
        errors.append("Downloaded ticker outside the eligible universe.")

    counts = meta.groupby(["ticker", "form"]).size().unstack(fill_value=0)
    coverage = eligible[["ticker", "n_10k", "n_10q"]].set_index("ticker").join(counts)
    for form, expected_col in [("10-K", "n_10k"), ("10-Q", "n_10q")]:
        if form not in coverage:
            coverage[form] = 0
        coverage[form] = coverage[form].fillna(0).astype(int)
        if not coverage[form].eq(coverage[expected_col]).all():
            errors.append(f"Per-company {form} counts disagree with the universe.")
    coverage.to_csv(OUTPUT_DIR / "filing_coverage.csv")

    text_failures = []
    for number, row in enumerate(meta.itertuples(), 1):
        try:
            with gzip.open(ROOT / row.text_path, "rt", encoding="utf-8") as stream:
                tokens = tokenize(stream.read())
            if not tokens or len(tokens) != row.n_words or len(set(tokens)) != row.n_distinct:
                raise ValueError("Empty text or word counts disagree with metadata")
        except Exception as exc:
            text_failures.append({"accession": row.accession, "error": str(exc)})
        if number % 250 == 0:
            print(f"Text counts checked: {number}/{len(meta)}", flush=True)
    if text_failures:
        errors.append(f"{len(text_failures)} text files failed verification.")

    for name, frame in [("prices", prices), ("volume", volume)]:
        if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
            errors.append(f"{name}: duplicate or unsorted dates.")
    if ((prices <= 0) & prices.notna()).any().any():
        errors.append("Observed nonpositive prices.")
    if ((volume < 0) & volume.notna()).any().any():
        errors.append("Observed negative volumes.")
    market_rows = []
    for ticker in sorted(set(eligible.ticker) | {"SPY", "ARKK", "^VIX"}):
        p = prices[ticker].dropna() if ticker in prices else pd.Series(dtype=float)
        v = volume[ticker].dropna() if ticker in volume else pd.Series(dtype=float)
        market_rows.append({
            "ticker": ticker, "price_observations": len(p), "volume_observations": len(v),
            "first_price_date": p.index.min() if len(p) else None,
            "last_price_date": p.index.max() if len(p) else None,
        })
        if p.empty:
            warnings.append(f"{ticker}: no observed prices.")
        if v.empty and ticker != "^VIX":
            warnings.append(f"{ticker}: no observed volume.")
    pd.DataFrame(market_rows).to_csv(OUTPUT_DIR / "market_coverage.csv", index=False)
    for benchmark in ["SPY", "ARKK", "^VIX"]:
        if benchmark not in prices or not prices[benchmark].notna().any():
            errors.append(f"Required benchmark missing: {benchmark}.")

    if shares.accession.duplicated().any():
        share_audit = pd.DataFrame()
    else:
        share_audit = meta[["ticker", "cik", "accession", "filing_date"]].merge(
            shares, on=["cik", "accession"], how="left", validate="many_to_one"
        )
        share_audit["missing_or_invalid_shares"] = (
            share_audit.shares_outstanding.isna() | share_audit.shares_outstanding.le(0)
        )
        share_audit["shares_date_after_filing"] = (
            pd.to_datetime(share_audit.shares_as_of, errors="coerce")
            > pd.to_datetime(share_audit.filing_date)
        )
        share_audit["missing_shares_date"] = pd.to_datetime(
            share_audit.shares_as_of, errors="coerce"
        ).isna()
        share_audit["weighted_average_share_proxy"] = share_audit.shares_tag.fillna("").str.contains(
            "WeightedAverage", regex=False
        )
        share_audit.to_csv(OUTPUT_DIR / "filing_share_audit.csv", index=False)
        if share_audit.shares_date_after_filing.any():
            errors.append("Share-count observation date after filing date.")
        for flag in ["missing_or_invalid_shares", "missing_shares_date", "weighted_average_share_proxy"]:
            count = int(share_audit[flag].sum())
            if count:
                warnings.append(f"{count} filings: {flag}.")

    removed_negative = dictionary.loc[dictionary.Negative.lt(0), ["Word", "Negative"]]
    removed_negative.to_csv(OUTPUT_DIR / "negative_dictionary_removed_entries.csv", index=False)
    if len(removed_negative):
        warnings.append(
            f"Starter's nonzero Negative flag includes {len(removed_negative)} removed words; "
            "retained for the assignment's stated list size, pending analysis disclosure."
        )
    snapshot = pd.read_csv(UNIVERSE_DIR / "ark_holdings_raw.csv")
    snapshot_dates = sorted(snapshot.date.astype(str).unique().tolist())
    if len(snapshot_dates) > 1:
        warnings.append("Instructor's frozen holdings file contains multiple snapshot dates.")

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Input acquisition only; no sample exclusions or regression estimates applied.",
        "expected_ticker_filing_rows": expected, "downloaded_ticker_filing_rows": len(meta),
        "unique_filings": int(meta.accession.nunique()),
        "companies": int(meta.cik.nunique()), "securities": int(meta.ticker.nunique()),
        "forms_by_ticker_filing_row": meta.form.value_counts().to_dict(),
        "forms_by_unique_filing": meta.drop_duplicates("accession").form.value_counts().to_dict(),
        "filing_years": dates.dt.year.value_counts().sort_index().to_dict(),
        "total_words": int(meta.n_words.sum()), "text_failures": text_failures,
        "unique_filing_total_words": int(meta.drop_duplicates("accession").n_words.sum()),
        "price_shape": list(prices.shape), "price_start": str(prices.index.min().date()),
        "price_end": str(prices.index.max().date()),
        "matched_share_filings": int((~share_audit.missing_or_invalid_shares).sum()) if len(share_audit) else 0,
        "share_tag_counts": share_audit.shares_tag.fillna("missing").value_counts().to_dict() if len(share_audit) else {},
        "lexicon_counts": {c: int(dictionary[c].fillna(0).ne(0).sum()) for c in ["Negative", "Uncertainty"]},
        "dictionary_sha256": hashlib.sha256(LM_MASTER_DICT_PATH.read_bytes()).hexdigest(),
        "holdings_snapshot_dates": snapshot_dates,
        "errors": errors, "warnings": warnings,
    }
    target = OUTPUT_DIR / "download_validation.json"
    target.write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, allow_nan=False))
    print(f"Saved audit: {target}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
