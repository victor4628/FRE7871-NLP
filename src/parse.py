"""Filing HTML -> a bag of words.

This module is finished. It handles the two things that silently ruin a
dictionary study if you get them wrong:

1. Inline XBRL. Since ~2019 every 10-K and 10-Q is an inline-XBRL document.
   If you strip tags naively you get thousands of tokens like
   "us-gaap MoneyMarketFundsMember" mixed into the text, which inflates the
   denominator of every proportional measure. We drop the XBRL scaffolding.

2. Tables. Loughran and McDonald exclude tables and exhibits, because tables are
   mostly numbers and boilerplate. But in a modern filing, tables are also used
   for page layout, so dropping every <table> throws away real narrative. We use
   the standard compromise: drop a table only if more than 15% of its non-space
   characters are digits.

Both choices are defensible and both are choices. If you change the thresholds,
say so in your report and show what it does to your results.
"""

from __future__ import annotations

import html
import re
import warnings
from collections import Counter

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

NUMERIC_TABLE_THRESHOLD = 0.15
_XBRL_PREFIXES = ("ix:", "xbrli:", "xbrldi:", "link:", "xsi:", "xbrl:")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _numeric_share(text: str) -> float:
    text = re.sub(r"\s+", "", text)
    if not text:
        return 1.0
    return sum(c.isdigit() for c in text) / len(text)


def html_to_text(raw_html: str, drop_numeric_tables: bool = True) -> str:
    """Extract readable narrative text from a filing's primary document."""
    soup = BeautifulSoup(raw_html, "lxml")

    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    for tag in list(soup.find_all(True)):
        if tag.decomposed:
            continue
        name = (tag.name or "").lower()
        if name.startswith(_XBRL_PREFIXES) or name in ("ix", "xbrl"):
            tag.decompose()
            continue
        style = (tag.attrs.get("style") or "").replace(" ", "").lower()
        if "display:none" in style:
            tag.decompose()

    if drop_numeric_tables:
        for table in list(soup.find_all("table")):
            if table.decomposed:
                continue
            if _numeric_share(table.get_text(" ")) > NUMERIC_TABLE_THRESHOLD:
                table.decompose()

    text = html.unescape(soup.get_text(" ")).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str, min_length: int = 2) -> list[str]:
    """Uppercase alphabetic tokens. Numbers are dropped; the word lists have none.

    Uppercasing matters: the Loughran-McDonald master dictionary and the Harvard
    General Inquirer are both distributed in uppercase.
    """
    return [w.upper() for w in _TOKEN_RE.findall(text) if len(w) >= min_length]


def word_counts(tokens: list[str]) -> Counter:
    return Counter(tokens)


def parse_filing(raw_html: str) -> dict:
    """One filing -> {'n_words', 'counts'} ready for scoring."""
    tokens = tokenize(html_to_text(raw_html))
    return {"n_words": len(tokens), "counts": word_counts(tokens)}
