"""Loading the two word lists the paper compares.

Fin-Neg and friends come straight from the Loughran-McDonald Master Dictionary.
H4N-Inf has to be rebuilt, because the Harvard General Inquirer is distributed as
root words only. LM expanded 2,005 Harvard roots into 4,187 inflected forms by
hand. We approximate that with conservative morphological rules, keeping only
forms that actually occur in 10-X filings (the master dictionary's vocabulary).

You will get roughly 5,000 forms, not 4,187. That is a real deviation from the
paper and you are expected to say so in your report.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .config import HARVARD_GI_PATH, LM_CATEGORIES, LM_MASTER_DICT_PATH


def load_master_dictionary(path: Path | None = None) -> pd.DataFrame:
    path = Path(path or LM_MASTER_DICT_PATH)
    if not path.exists():
        raise FileNotFoundError(f"{path} missing - run: python scripts/00_get_lexicons.py")
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    df["Word"] = df["Word"].astype(str).str.upper()
    return df


def lm_word_lists(master: pd.DataFrame | None = None) -> dict[str, set[str]]:
    """{'Negative': {...}, 'Positive': {...}, ...} from the master dictionary.

    A non-zero entry in a category column is the year the word entered that
    category, so 'non-zero' means 'is in the list'.
    """
    master = master if master is not None else load_master_dictionary()
    out = {}
    for cat in LM_CATEGORIES:
        out[cat] = set(master.loc[master[cat].fillna(0) != 0, "Word"])
    return out


def lm_vocabulary(master: pd.DataFrame | None = None) -> set[str]:
    """Every word the LM team observed in 10-X filings. Used to filter inflections."""
    master = master if master is not None else load_master_dictionary()
    return set(master["Word"])


def harvard_negative_roots(path: Path | None = None) -> set[str]:
    """The Harvard-IV-4 'Negativ' tag, one entry per root word.

    inqtabs.txt is sense-disambiguated: TAX#1 is neutral, TAX#2 is Negativ. Any
    sense tagged Negativ puts the root on the list, which is exactly the
    behaviour that makes the Harvard list misfire on financial text.
    """
    path = Path(path or HARVARD_GI_PATH)
    if not path.exists():
        raise FileNotFoundError(f"{path} missing - run: python scripts/00_get_lexicons.py")
    lines = path.read_text(encoding="latin-1").splitlines()
    header = lines[0].split("\t")
    idx = header.index("Negativ")
    roots = set()
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) <= idx or not parts[idx].strip():
            continue
        word = parts[0].split("#")[0].strip().upper()
        if re.fullmatch(r"[A-Z'\-]+", word):
            roots.add(word)
    return roots


def inflections(word: str) -> set[str]:
    """Plural, third person, past and progressive forms of one root word."""
    forms = {word}
    if word.endswith("Y") and len(word) > 2 and word[-2] not in "AEIOU":
        forms |= {word[:-1] + "IES", word[:-1] + "IED"}
    elif word.endswith("E"):
        forms |= {word + "S", word + "D", word[:-1] + "ING"}
    elif word.endswith(("S", "X", "Z", "CH", "SH")):
        forms |= {word + "ES", word + "ED", word + "ING"}
    else:
        forms |= {word + "S", word + "ED", word + "ING"}
        if (len(word) > 3 and word[-1] not in "AEIOUWXY"
                and word[-2] in "AEIOU" and word[-3] not in "AEIOU"):
            forms |= {word + word[-1] + "ED", word + word[-1] + "ING"}
    return forms


def h4n_inflected(master: pd.DataFrame | None = None) -> set[str]:
    """The H4N-Inf list: Harvard Negativ roots plus inflections seen in filings."""
    vocab = lm_vocabulary(master)
    out = set()
    for root in harvard_negative_roots():
        out |= {f for f in inflections(root) if f in vocab}
    return out


def load_all() -> dict[str, set[str]]:
    """Every word list the assignment needs, in one dictionary."""
    master = load_master_dictionary()
    lists = lm_word_lists(master)
    lists["H4N_Inf"] = h4n_inflected(master)
    return lists
