import numpy as np
import pandas as pd
import pytest
from lxml import html

from src.analysis_models import clustered_fit
from src.analysis_data import cover_share_facts


def test_redundant_fixed_effects_keep_identified_slope():
    rng=np.random.default_rng(42)
    data=pd.DataFrame({'cik':np.repeat(['a','b','c','d'],10),'time':np.tile(np.arange(10),4)})
    data['quarter_of_year']=np.repeat([1,2,3,4],10)  # Exactly nested in firm effects.
    data['y']=2*data.time+np.repeat([0,10,20,30],10)+rng.normal(0,.1,len(data))
    r=clustered_fit('y ~ time + C(cik) + C(quarter_of_year)',data)
    plain=clustered_fit('y ~ time + C(cik)',data)
    assert r.params['time']==pytest.approx(plain.params['time'])
    assert r.analysis_dropped_terms
    assert np.isfinite(r.bse['time'])


def test_common_classes_are_summed_only_without_total():
    raw='''<html><xbrli:context id="a"><xbrli:period><xbrli:instant>2022-01-01</xbrli:instant></xbrli:period>
    <xbrldi:explicitmember dimension="us-gaap:StatementClassOfStockAxis">ClassA</xbrldi:explicitmember></xbrli:context>
    <xbrli:context id="b"><xbrli:period><xbrli:instant>2022-01-01</xbrli:instant></xbrli:period>
    <xbrldi:explicitmember dimension="us-gaap:StatementClassOfStockAxis">ClassB</xbrldi:explicitmember></xbrli:context>
    <ix:nonfraction name="dei:EntityCommonStockSharesOutstanding" contextref="a" scale="3">100</ix:nonfraction>
    <ix:nonfraction name="dei:EntityCommonStockSharesOutstanding" contextref="b" scale="3">25</ix:nonfraction></html>'''
    assert cover_share_facts(html.fromstring(raw),pd.Timestamp('2022-01-05'))[0]==125000
    total='''<xbrli:context id="total"><xbrli:period><xbrli:instant>2022-01-01</xbrli:instant></xbrli:period></xbrli:context>
    <ix:nonfraction name="dei:EntityCommonStockSharesOutstanding" contextref="total" scale="3">125</ix:nonfraction>'''
    assert cover_share_facts(html.fromstring(raw.replace('</html>',total+'</html>')),pd.Timestamp('2022-01-05'))[0]==125000
