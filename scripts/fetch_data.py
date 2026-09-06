"""Download the prepared filing corpus instead of crawling EDGAR yourself.

    python scripts/fetch_data.py

This is the fast path. It pulls one archive containing all ~1,700 filings as
extracted text, the filing metadata, the resolved universe and the point-in-time
share counts, and unpacks it into data/. About a minute instead of twenty-five.

You still need to run, separately:

    python scripts/00_get_lexicons.py      # the word lists,  ~15 s
    python scripts/03_get_market_data.py   # prices and VIX,  ~3 min

Neither is in the archive: the word list belongs to Notre Dame and the price data
comes from Yahoo, whose terms do not allow us to redistribute it.

The slow path still works and is worth doing once if you want to see what the
crawler does:

    python scripts/01_build_universe.py
    python scripts/02_download_filings.py

The two produce the same files. If you use this script, say so in your report;
if you built the corpus yourself and your filing count differs from the archive's,
say that too, and explain why.
"""

from __future__ import annotations

import hashlib
import sys
import tarfile
import tempfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]

# Set these once the release is published; see scripts/make_bundle.py.
BUNDLE_URL = ""
BUNDLE_SHA256 = ""


def main() -> int:
    if not BUNDLE_URL:
        print("No bundle URL configured yet.\n")
        print("Your instructor has not published the prepared archive, or you are")
        print("working from a fork that predates it. Build the corpus yourself:\n")
        print("    python scripts/01_build_universe.py")
        print("    python scripts/02_download_filings.py")
        return 1

    print(f"downloading {BUNDLE_URL}")
    with requests.get(BUNDLE_URL, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        digest = hashlib.sha256()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tar.gz") as tmp:
            done = 0
            for chunk in resp.iter_content(chunk_size=1 << 20):
                tmp.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {done / 1e6:6.1f} / {total / 1e6:.1f} MB", end="")
            path = Path(tmp.name)
    print()

    if BUNDLE_SHA256 and digest.hexdigest() != BUNDLE_SHA256:
        print("Checksum mismatch. Refusing to unpack.")
        print(f"  expected {BUNDLE_SHA256}")
        print(f"  got      {digest.hexdigest()}")
        path.unlink(missing_ok=True)
        return 1

    print("unpacking into data/")
    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            # Never write outside the repository.
            target = (ROOT / member.name).resolve()
            if not str(target).startswith(str(ROOT.resolve())):
                print(f"  skipping suspicious path: {member.name}")
                continue
            tar.extract(member, ROOT)
    path.unlink(missing_ok=True)

    meta = ROOT / "data/interim/filings_meta.csv"
    n_text = len(list((ROOT / "data/interim/text").glob("*.txt.gz")))
    print(f"done: {n_text} filings, metadata at {meta.relative_to(ROOT)}")
    print("\nStill to run:")
    print("    python scripts/00_get_lexicons.py")
    print("    python scripts/03_get_market_data.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
