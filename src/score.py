"""Turning word counts into the two tone measures the paper compares.

The paper uses two weighting schemes and finds they disagree, which is the
whole point of its Table IV. You implement both.

  Proportional  score = (count of category words) / (total words in document)

  tf.idf        equation (1) of Loughran and McDonald (2011):

                          (1 + log(tf_ij))        N
                w_ij  =  ------------------ * log ---     if tf_ij >= 1
                          (1 + log(a_j))          df_i

                w_ij  =  0                                 otherwise

                tf_ij = raw count of word i in document j
                a_j   = average word count in document j
                        = (total words in j) / (distinct words in j)
                N     = number of documents in the corpus
                df_i  = number of documents containing word i at least once

The document score is the sum of w_ij over the words i that are on the word list.

Two things the paper leaves ambiguous. Decide, then say what you decided in your
report:
  - "average word count in the document" (a_j). The reading above -- mean count
    per distinct word within document j -- is the standard pivoted-length scheme
    and the one we intend. If you read it as the mean document length across the
    corpus, your numbers will differ; that is a defensible alternative, not a bug,
    as long as you disclose it.
  - Whether the summed weights are normalised by document length. We do not
    normalise; the length adjustment is already inside a_j.

Use natural logs throughout, and keep tf.idf statistics (N, df_i, a_j) computed
on YOUR corpus, not borrowed from anywhere else.
"""

from __future__ import annotations

import math
from collections import Counter

import pandas as pd


# ---------------------------------------------------------------------------
# Proportional measure  -- worked example, nothing to do here
# ---------------------------------------------------------------------------
def proportional_score(counts: Counter, word_list: set[str], n_words: int) -> float:
    """Share of the document's words that are on `word_list`."""
    if not n_words:
        return float("nan")
    return sum(c for w, c in counts.items() if w in word_list) / n_words


# ---------------------------------------------------------------------------
# tf.idf measure -- YOUR CODE
# ---------------------------------------------------------------------------
def document_frequency(all_counts: list[Counter]) -> Counter:
    """df_i: how many documents contain each word at least once.

    TODO(student): return a Counter mapping word -> number of documents in
    `all_counts` where that word appears with count >= 1.
    """
    raise NotImplementedError("implement document_frequency")


def average_word_count(counts: Counter) -> float:
    """a_j: average count per distinct word in one document.

    TODO(student): total tokens in the document divided by the number of
    distinct tokens. Return nan for an empty document.
    """
    raise NotImplementedError("implement average_word_count")


def tfidf_score(
    counts: Counter,
    word_list: set[str],
    doc_freq: Counter,
    n_docs: int,
) -> float:
    """Sum of equation (1) weights over the words in `word_list`.

    TODO(student): implement equation (1) exactly as written in the module
    docstring. Skip words with df_i == 0 (they cannot occur -- if one does, your
    doc_freq was built on a different corpus than the document you are scoring).
    """
    raise NotImplementedError("implement tfidf_score")


# ---------------------------------------------------------------------------
# Corpus-level driver -- YOUR CODE
# ---------------------------------------------------------------------------
def score_corpus(
    docs: pd.DataFrame,
    word_lists: dict[str, set[str]],
    counts_column: str = "counts",
    n_words_column: str = "n_words",
) -> pd.DataFrame:
    """Add one proportional and one tf.idf column per word list.

    Expected output columns, for each list name L:
        prop_L    proportional score
        tfidf_L   tf.idf score

    TODO(student): compute df_i and N once over the whole corpus, then score
    every document. Watch the corpus definition: N and df_i must come from the
    same set of filings you run the regressions on. If you compute them on all
    filings and then drop some in the panel filters, your weights no longer match
    your sample -- decide which you want and be consistent.
    """
    raise NotImplementedError("implement score_corpus")
