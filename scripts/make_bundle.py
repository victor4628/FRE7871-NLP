"""Instructor utility: pack the downloaded corpus into one distributable file.

    python scripts/make_bundle.py

Produces `ark_filings_2021_2025.tar.gz` in the repository root, containing the
SEC-derived data only:

    data/interim/filings_meta.csv     one row per filing
    data/interim/text/*.txt.gz        extracted narrative text
    data/universe/universe.csv        the 124 holdings resolved to filers
    data/prices/shares.csv            point-in-time share counts from XBRL

Upload that file as a GitHub Release asset and put its URL in
`scripts/fetch_data.py`. Students then get the 25-minute download in about a
minute, and the SEC does not field 20 identical crawls in one week.

What is deliberately NOT in the bundle:

    Prices, volume and VIX      Sourced from Yahoo via yfinance, whose terms do
                                not permit redistribution. Students run
                                scripts/03_get_market_data.py themselves; it
                                takes three minutes.
    The LM Master Dictionary    Redistributing someone else's word list invites
                                version drift. scripts/00_get_lexicons.py pulls
                                it from Notre Dame in fifteen seconds.

SEC filings are US government public records, so the text and metadata are free
to redistribute.
"""

from __future__ import annotations

import hashlib
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ark_filings_2021_2025.tar.gz"

MEMBERS = [
    "data/interim/filings_meta.csv",
    "data/interim/text",
    "data/universe/universe.csv",
    "data/prices/shares.csv",
]


def main() -> int:
    missing = [m for m in MEMBERS if not (ROOT / m).exists()]
    if missing:
        print("Missing, run scripts 01-03 first:")
        for m in missing:
            print("   ", m)
        return 1

    if OUT.exists():
        OUT.unlink()

    print(f"packing -> {OUT.name}")
    with tarfile.open(OUT, "w:gz", compresslevel=9) as tar:
        for m in MEMBERS:
            tar.add(ROOT / m, arcname=m)

    size = OUT.stat().st_size
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    n_text = len(list((ROOT / "data/interim/text").glob("*.txt.gz")))

    print(f"  {n_text} filings")
    print(f"  {size / 1e6:.1f} MB")
    print(f"  sha256 {digest}")
    print()
    print("Next: create a GitHub Release, attach this file, and paste its download")
    print("URL and the sha256 above into scripts/fetch_data.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
