"""Download and parse every 10-K and 10-Q for the universe.

    python scripts/02_download_filings.py                 # everything
    python scripts/02_download_filings.py --limit 5       # first 5 filers, for a trial run
    python scripts/02_download_filings.py --drop-html     # delete raw HTML after parsing

Expect roughly 1,700 filings, 25-40 minutes, and 2-3 GB of raw HTML if you keep it.
Run it once, go and read the paper properly while it works, and do not delete
data/ afterwards.

Writes:
    data/interim/filings_meta.csv       one row per filing (metadata + word count)
    data/interim/text/<accession>.txt.gz  extracted narrative text
    data/filings/<accession>.html       raw primary document (the cache)
"""

from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import (  # noqa: E402
    FILING_DIR, FORMS, INTERIM_DIR, SAMPLE_END, SAMPLE_START, SEC_USER_AGENT,
    UNIVERSE_DIR,
)
from src.edgar import EdgarClient  # noqa: E402
from src.parse import html_to_text, tokenize  # noqa: E402

TEXT_DIR = INTERIM_DIR / "text"
META_PATH = INTERIM_DIR / "filings_meta.csv"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only the first N filers")
    ap.add_argument("--drop-html", action="store_true",
                    help="delete the raw HTML after parsing, to save disk")
    args = ap.parse_args()

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    universe = pd.read_csv(UNIVERSE_DIR / "universe.csv", dtype={"cik": str})
    universe = universe[universe["status"] == "domestic_filer"]
    if args.limit:
        universe = universe.head(args.limit)
    print(f"{len(universe)} filers")

    client = EdgarClient(SEC_USER_AGENT or None)
    rows, failures = [], []

    for i, (_, firm) in enumerate(universe.iterrows(), 1):
        try:
            filings = client.list_filings(firm["cik"], FORMS, SAMPLE_START, SAMPLE_END)
        except Exception as exc:  # noqa: BLE001
            failures.append((firm["ticker"], "list_filings", str(exc)))
            continue

        for _, f in filings.iterrows():
            acc = f["accession"].replace("-", "")
            text_path = TEXT_DIR / f"{acc}.txt.gz"
            try:
                text = ""
                if text_path.exists():
                    with gzip.open(text_path, "rt", encoding="utf-8") as fh:
                        text = fh.read()
                # An empty read means the cache is a stub, was truncated by an
                # interrupted run, or is an unhydrated cloud-sync placeholder.
                # Never trust it; fetch again.
                if not text.strip():
                    raw = client.fetch_document(f["doc_url"], f["accession"])
                    text = html_to_text(raw)
                    tmp = text_path.with_suffix(".tmp")
                    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
                        fh.write(text)
                    tmp.replace(text_path)
                tokens = tokenize(text)
            except Exception as exc:  # noqa: BLE001
                failures.append((firm["ticker"], f["accession"], str(exc)))
                continue

            # Cleanup is best-effort and must never discard a good filing.
            # On Windows, OneDrive and antivirus both hold brief locks on files
            # that were just written, which raises WinError 32 here.
            if args.drop_html:
                try:
                    (FILING_DIR / f"{acc}.html").unlink(missing_ok=True)
                except OSError:
                    pass

            rows.append({
                "ticker": firm["ticker"],
                "cik": firm["cik"],
                "company": f["company"],
                "sic": f["sic"],
                "sic_desc": f["sic_desc"],
                "form": f["form"],
                "filing_date": f["filing_date"].date(),
                "report_date": f["report_date"].date() if pd.notna(f["report_date"]) else None,
                "acceptance_datetime": f["acceptance_datetime"],
                "accession": f["accession"],
                "doc_url": f["doc_url"],
                "n_words": len(tokens),
                "n_distinct": len(set(tokens)),
                "text_path": str(text_path.relative_to(Path(__file__).resolve().parents[1])),
            })

        print(f"[{i:3d}/{len(universe)}] {firm['ticker']:6s} {len(filings):3d} filings "
              f"(running total {len(rows)})")

    out = pd.DataFrame(rows)
    # EDGAR company names and SIC descriptions occasionally carry stray newlines,
    # and a half-flushed CSV is worse than no CSV, so clean the text fields and
    # write through a temporary file.
    for col in ("company", "sic_desc"):
        if col in out.columns:
            out[col] = out[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    tmp_meta = META_PATH.with_suffix(".tmp")
    out.to_csv(tmp_meta, index=False, lineterminator="\n")
    tmp_meta.replace(META_PATH)

    check = pd.read_csv(META_PATH)
    if len(check) != len(out):
        print(f"WARNING: wrote {len(out)} rows but read back {len(check)}. "
              f"Inspect {META_PATH} before using it.")

    print(f"\nWrote {META_PATH}: {len(out)} filings, "
          f"{out['n_words'].sum() / 1e6:.1f}M words")
    print(out.groupby("form")["n_words"].describe()[["count", "mean", "50%", "min", "max"]])
    if failures:
        print(f"\n{len(failures)} failures (investigate before you report a sample size):")
        for f in failures[:20]:
            print("   ", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
