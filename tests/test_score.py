"""Unit tests for the scoring functions.

Run:  pytest -q

These must pass before you submit. They are a worked example of equation (1),
computed by hand on a three-document corpus, so if your tf.idf disagrees with
them your tf.idf is wrong -- not the test.

    d1 = LOSS LOSS RISK GAIN      d2 = LOSS GAIN GAIN      d3 = RISK RISK RISK GAIN
    N = 3,  df(LOSS) = 2,  df(RISK) = 2,  df(GAIN) = 3
    word list = {LOSS, RISK}
"""

from collections import Counter

import pytest

from src.score import (
    average_word_count,
    document_frequency,
    proportional_score,
    tfidf_score,
)

D1 = Counter({"LOSS": 2, "RISK": 1, "GAIN": 1})
D2 = Counter({"LOSS": 1, "GAIN": 2})
D3 = Counter({"RISK": 3, "GAIN": 1})
CORPUS = [D1, D2, D3]
WORD_LIST = {"LOSS", "RISK"}


def test_document_frequency():
    df = document_frequency(CORPUS)
    assert df["LOSS"] == 2
    assert df["RISK"] == 2
    assert df["GAIN"] == 3
    assert df["NOTAWORD"] == 0


@pytest.mark.parametrize("counts,expected", [(D1, 4 / 3), (D2, 1.5), (D3, 2.0)])
def test_average_word_count(counts, expected):
    assert average_word_count(counts) == pytest.approx(expected)


@pytest.mark.parametrize("counts,n_words,expected", [
    (D1, 4, 0.75),
    (D2, 3, 1 / 3),
    (D3, 4, 0.75),
])
def test_proportional_score(counts, n_words, expected):
    assert proportional_score(counts, WORD_LIST, n_words) == pytest.approx(expected)


@pytest.mark.parametrize("counts,expected", [
    (D1, 0.8480177181),
    (D2, 0.2884917639),
    (D3, 0.5025635505),
])
def test_tfidf_score(counts, expected):
    df = document_frequency(CORPUS)
    assert tfidf_score(counts, WORD_LIST, df, len(CORPUS)) == pytest.approx(expected, rel=1e-6)


def test_tfidf_uses_natural_log():
    """A base-10 implementation gives a different number. Catch it early."""
    df = document_frequency(CORPUS)
    got = tfidf_score(D1, WORD_LIST, df, len(CORPUS))
    assert got != pytest.approx(0.8480177181 / 2.302585, rel=1e-3), "looks like log base 10"


def test_word_absent_scores_zero():
    df = document_frequency(CORPUS)
    assert tfidf_score(Counter({"GAIN": 5}), WORD_LIST, df, len(CORPUS)) == pytest.approx(0.0)
