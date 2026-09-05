"""Download the two word lists into data/lexicons/.

    python scripts/00_get_lexicons.py

Sources
  Loughran-McDonald Master Dictionary  https://sraf.nd.edu/loughranmcdonald-master-dictionary/
  Harvard General Inquirer (inqtabs)   https://inquirer.sites.fas.harvard.edu/

Both are free. If a link has rotted since this was written, go to the pages above,
download by hand, and drop the files in data/lexicons/ under the names in
src/config.py. Do not silently substitute a different word list.
"""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import (  # noqa: E402
    HARVARD_GI_PATH, HARVARD_GI_URL, LM_MASTER_DICT_PATH, LM_MASTER_DICT_URL,
)

TARGETS = [
    ("Loughran-McDonald Master Dictionary", LM_MASTER_DICT_URL, LM_MASTER_DICT_PATH),
    ("Harvard General Inquirer (inqtabs.txt)", HARVARD_GI_URL, HARVARD_GI_PATH),
]


def main() -> int:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (course assignment)"})
    failures = 0
    for name, url, path in TARGETS:
        if path.exists() and path.stat().st_size > 10_000:
            print(f"[skip] {name} already at {path} ({path.stat().st_size/1e6:.1f} MB)")
            continue
        print(f"[get ] {name}")
        try:
            resp = session.get(url, timeout=180)
            resp.raise_for_status()
            path.write_bytes(resp.content)
            print(f"[ok  ] {path} ({len(resp.content)/1e6:.1f} MB)")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"[FAIL] {name}: {exc}\n       Download it by hand and save it to {path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
