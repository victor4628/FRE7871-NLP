"""Central configuration. Change things here, not scattered through the notebook."""

import os
from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LEXICON_DIR = DATA / "lexicons"
FILING_DIR = DATA / "filings"
PRICE_DIR = DATA / "prices"
UNIVERSE_DIR = DATA / "universe"
INTERIM_DIR = DATA / "interim"
OUTPUT_DIR = ROOT / "outputs"

for _d in (LEXICON_DIR, FILING_DIR, PRICE_DIR, UNIVERSE_DIR, INTERIM_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# SEC EDGAR
# ----------------------------------------------------------------------------
# The SEC requires a declared User-Agent with a real contact address, and rate
# limits to 10 requests/second. Set SEC_USER_AGENT in your environment:
#     Windows PowerShell:  $env:SEC_USER_AGENT = "Your Name your.netid@nyu.edu"
#     macOS / Linux:       export SEC_USER_AGENT="Your Name your.netid@nyu.edu"
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "")
SEC_MAX_REQUESTS_PER_SEC = 6.0  # below the SEC's limit of 10, on purpose

# ----------------------------------------------------------------------------
# Sample definition  (Section 3 of the assignment)
# ----------------------------------------------------------------------------
ARK_FUNDS = ["ARKK", "ARKQ", "ARKW", "ARKF", "ARKG", "ARKX"]

SAMPLE_START = "2021-01-01"          # filing date, inclusive
SAMPLE_END = "2025-12-31"            # filing date, inclusive
FORMS = ["10-K", "10-Q"]             # amendments (10-K/A, 10-Q/A) are excluded

BENCHMARK = "SPY"                    # stands in for the CRSP value-weighted index
ALT_BENCHMARK = "ARKK"               # thematic-peer benchmark, robustness check

EVENT_WINDOW = (0, 3)                # LM's day [0,+3] filing-period window
PREEVENT_WINDOW = (-60, -6)          # used for the momentum / liquidity controls
POSTEVENT_WINDOW = (4, 63)           # realised volatility after the filing is absorbed

MIN_PRICE = 3.00                     # price on day -1 must be at least this
MIN_WORDS_10K = 2000                 # LM's filter
MIN_WORDS_10Q = 1000                 # scaled down: 10-Qs are shorter
MIN_TRADING_DAYS_BEFORE = 60
MIN_TRADING_DAYS_AFTER = 60

# ----------------------------------------------------------------------------
# Word-list downloads (verified working 2026-09-05; if a link rots, see README)
# ----------------------------------------------------------------------------
LM_MASTER_DICT_URL = (
    "https://drive.usercontent.google.com/download"
    "?id=1iq2RUf8qGFEAk1g8wQntP3habOnR3fXF&export=download&confirm=t"
)
LM_MASTER_DICT_PATH = LEXICON_DIR / "LoughranMcDonald_MasterDictionary.csv"

HARVARD_GI_URL = "https://inquirer.sites.fas.harvard.edu/inqtabs.txt"
HARVARD_GI_PATH = LEXICON_DIR / "inqtabs.txt"

LM_CATEGORIES = [
    "Negative", "Positive", "Uncertainty",
    "Litigious", "Strong_Modal", "Weak_Modal",
]
