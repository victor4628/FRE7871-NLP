"""A polite, cached SEC EDGAR client.

This module is finished — you should not need to change it. It exists so that
nobody in the class spends their week debugging rate limits and 403s instead of
doing the actual analysis. Read it anyway: you are responsible for every line
you submit, and the point-in-time fields it returns (acceptanceDateTime in
particular) are the ones the rest of the assignment depends on.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

from .config import (
    FILING_DIR,
    SEC_MAX_REQUESTS_PER_SEC,
    SEC_USER_AGENT,
)

_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
_COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"
_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{doc}"


class EdgarClient:
    """Rate-limited EDGAR session with an on-disk cache of every document."""

    def __init__(self, user_agent: str | None = None, cache_dir: Path | None = None):
        ua = user_agent or SEC_USER_AGENT
        if not ua or "@" not in ua:
            raise RuntimeError(
                "Set a real SEC_USER_AGENT, e.g.\n"
                '    $env:SEC_USER_AGENT = "Jane Doe jd123@nyu.edu"   (PowerShell)\n'
                '    export SEC_USER_AGENT="Jane Doe jd123@nyu.edu"   (bash)\n'
                "The SEC blocks unidentified traffic and it is their site, not ours."
            )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": ua, "Accept-Encoding": "gzip, deflate"})
        self.cache_dir = Path(cache_dir or FILING_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._min_interval = 1.0 / SEC_MAX_REQUESTS_PER_SEC
        self._last_call = 0.0

    # -- low level -----------------------------------------------------------
    def _get(self, url: str, timeout: int = 60) -> requests.Response:
        wait = self._min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(4):
            resp = self.session.get(url, timeout=timeout)
            self._last_call = time.monotonic()
            if resp.status_code == 200:
                return resp
            if resp.status_code in (403, 429, 500, 502, 503):
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
        resp.raise_for_status()
        return resp

    # -- metadata ------------------------------------------------------------
    def ticker_to_cik(self) -> dict[str, str]:
        """{TICKER: 10-digit zero-padded CIK} for every SEC-registered filer."""
        payload = self._get(_COMPANY_TICKERS).json()
        return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in payload.values()}

    def submissions(self, cik: str) -> dict:
        """Full submission history for one CIK, including the older paged files."""
        cik = str(cik).zfill(10)
        payload = self._get(_SUBMISSIONS.format(cik=cik)).json()
        recent = payload["filings"]["recent"]
        frames = [pd.DataFrame(recent)]
        for extra in payload["filings"].get("files", []):
            url = f"https://data.sec.gov/submissions/{extra['name']}"
            frames.append(pd.DataFrame(self._get(url).json()))
        frames = [f.dropna(axis=1, how="all") for f in frames if not f.empty]
        if not frames:
            payload["_filings"] = pd.DataFrame()
        elif len(frames) == 1:
            payload["_filings"] = frames[0]
        else:
            payload["_filings"] = pd.concat(frames, ignore_index=True)
        return payload

    def list_filings(
        self,
        cik: str,
        forms: list[str],
        start: str,
        end: str,
        include_amendments: bool = False,
    ) -> pd.DataFrame:
        """Filing metadata for one CIK, filtered to `forms` and the date window.

        Columns: cik, company, sic, sic_desc, form, filing_date, report_date,
                 acceptance_datetime, accession, primary_document, doc_url.

        `acceptance_datetime` is UTC and is the timestamp EDGAR actually received
        the document. You need it: a filing accepted at 21:30 UTC on a Friday was
        not tradable on that Friday.
        """
        payload = self.submissions(cik)
        df = payload["_filings"].copy()
        if df.empty:
            return df

        if include_amendments:
            keep = df["form"].str.split("/").str[0].isin(forms)
        else:
            keep = df["form"].isin(forms)
        df = df[keep]
        df = df[(df["filingDate"] >= start) & (df["filingDate"] <= end)]
        if df.empty:
            return pd.DataFrame()

        cik_int = int(cik)
        out = pd.DataFrame({
            "cik": str(cik).zfill(10),
            "company": payload.get("name"),
            "sic": payload.get("sic"),
            "sic_desc": payload.get("sicDescription"),
            "form": df["form"].values,
            "filing_date": pd.to_datetime(df["filingDate"].values),
            "report_date": pd.to_datetime(df["reportDate"].values, errors="coerce"),
            "acceptance_datetime": pd.to_datetime(df["acceptanceDateTime"].values, errors="coerce", utc=True),
            "accession": df["accessionNumber"].values,
            "primary_document": df["primaryDocument"].values,
        })
        out["doc_url"] = [
            _ARCHIVE.format(cik_int=cik_int, acc_nodash=a.replace("-", ""), doc=d)
            for a, d in zip(out["accession"], out["primary_document"])
        ]
        return out.sort_values("filing_date").reset_index(drop=True)

    # -- documents -----------------------------------------------------------
    def fetch_document(self, url: str, accession: str) -> str:
        """Download a filing's primary document, caching it under data/filings/."""
        path = self.cache_dir / f"{accession.replace('-', '')}.html"
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
        text = self._get(url, timeout=180).text
        path.write_text(text, encoding="utf-8", errors="replace")
        return text
