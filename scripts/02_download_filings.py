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
                if text_path.exists():
                    with gzip.open(text_path, "rt", encoding="utf-8") as fh:
                        text = fh.read()
                else:
                    raw = client.fetch_document(f["doc_url"], f["accession"])
                    text = html_to_text(raw)
                    with gzip.open(text_path, "wt", encoding="utf-8") as fh:
                        fh.write(text)
                    if args.drop_html:
                        (FILING_DIR / f"{acc}.html").unlink(missing_ok=True)
                tokens = tokenize(text)
            except Exception as exc:  # noqa: BLE001
                failures.append((firm["ticker"], f["accession"], str(exc)))
                continue

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
    out.to_csv(META_PATH, index=False)
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
