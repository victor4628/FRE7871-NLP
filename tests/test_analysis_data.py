import numpy as np
import pandas as pd
import pytest
from lxml import html

from src.analysis_data import (event_position, nominal_market_data, buy_hold,
                               annual_vol, parse_document, cover_share_facts,
                               plain_cover_shares, score_corpus)
from src.analysis_data import shell_status


def test_event_day_handles_early_close_and_utc():
    schedule = pd.DataFrame({"close": pd.to_datetime([
        "2021-11-24T21:00Z", "2021-11-26T18:00Z", "2021-11-29T21:00Z"
    ])})
    assert event_position("2021-11-26T17:59:59Z", schedule) == 1
    assert event_position("2021-11-26T18:00:00Z", schedule) == 2
    assert event_position("2021-11-27T12:00:00Z", schedule) == 2
    assert event_position("2021-11-25T10:00:00Z", schedule) == 1
    with pytest.raises(ValueError):
        event_position("2021-11-26", schedule)


def test_nominal_units_exclude_split_on_current_day():
    dates = pd.date_range("2022-01-01", periods=3)
    close = pd.DataFrame({"X": [10., 11., 12.]}, index=dates)
    volume = pd.DataFrame({"X": [200., 220., 240.]}, index=dates)
    splits = pd.DataFrame({"X": [0., 2., 0.]}, index=dates)
    price, vol, _ = nominal_market_data(close, volume, splits)
    assert price.X.tolist() == [20, 11, 12]
    assert vol.X.tolist() == [100, 220, 240]
    assert np.allclose(price.X*vol.X, close.X*volume.X)


def test_compounding_and_missing_are_not_sum_or_zero():
    assert buy_hold([.1, -.1]) == pytest.approx(-.01)
    assert np.isnan(buy_hold([.1, np.nan]))
    assert np.isnan(annual_vol(np.zeros(62)))
    assert annual_vol(np.arange(63)/1000) == pytest.approx(np.std(np.arange(63)/1000, ddof=1)*np.sqrt(252))


def test_visible_inline_text_survives_hidden_xbrl_does_not():
    raw = b'''<html><body><ix:header><ix:hidden>SECRET LOSS</ix:hidden></ix:header>
    <p>Results <ix:nonnumeric>may fluctuate</ix:nonnumeric> materially.</p>
    <table><tr><td>123456789 123456789 LOSS</td></tr></table>
    <div style="display:none">SECRET</div></body></html>'''
    counts, _, _ = parse_document(raw, pd.Timestamp("2022-01-01"))
    assert counts["MAY"] == counts["FLUCTUATE"] == 1
    assert not counts["SECRET"] and not counts["LOSS"]


def test_shell_boolean_ballot_box():
    for char, expected in [("☒",True),("☐",False)]:
        root=html.fromstring(f'<ix:nonnumeric name="dei:EntityShellCompany" format="ixt-sec:boolballotbox">{char}</ix:nonnumeric>')
        assert shell_status(root, "") is expected


def test_dated_plain_share_statement_does_not_count_par_value():
    text = ('As of March 5, 2021, there were 50,000,000 shares of the Class A common stock, '
            'par value $0.0001 per share, and 12,500,000 shares of the Class B common stock '
            'issued and outstanding. TABLE OF CONTENTS')
    shares, date, source, _ = plain_cover_shares(text, pd.Timestamp("2021-03-08"))
    assert shares == 62500000 and date == pd.Timestamp("2021-03-05")
    assert source == "cover_sentence"
    assert np.isnan(plain_cover_shares(text, pd.Timestamp("2020-03-08"))[0])
    text2=('As of May 7, 2021, 516,244,161 shares of Class A common stock and '
           '53,587,302 of Class B common stock, par value $0.0001, were outstanding.')
    assert plain_cover_shares(text2,pd.Timestamp("2021-05-10"))[0] == 569831463
    text3=('As of March 8, 2021, 27,500,000 shares of Class A common stock and '
           '6,875,000 shares of Class B c ommon stock were outstanding.')
    assert plain_cover_shares(text3,pd.Timestamp("2021-03-10"))[0] == 34375000


def test_tfidf_matches_hand_calculation_and_changes_with_corpus(monkeypatch):
    import src.analysis_data as module
    master = pd.DataFrame({"Word": ["LOSS", "MAY"], "Negative": [2011, 0], "Uncertainty": [0, 2011]})
    monkeypatch.setattr(module, "load_master_dictionary", lambda: master)
    meta = pd.DataFrame({"accession": ["a", "b"], "text_row": [0,1],
                         "analysis_words": [4,4], "analysis_distinct": [2,2]})
    matrix = np.array([[2,1],[0,2]])
    scored = score_corpus(meta, matrix, ["LOSS","MAY"])
    assert scored.negative_prop.iloc[0] == .5
    assert scored.negative_tfidf.iloc[0] == pytest.approx(np.log(2))
    assert scored.uncertainty_tfidf.eq(0).all()
    # The restricted corpus must recompute df/N, not reuse the full-sample IDF.
    assert score_corpus(meta.iloc[:1], matrix, ["LOSS","MAY"]).negative_tfidf.iloc[0] == 0
