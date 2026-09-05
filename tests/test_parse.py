"""Tests for the parser. These pass out of the box -- they document what it does.

If you change NUMERIC_TABLE_THRESHOLD or the tokenizer, these tests tell you what
you changed.
"""

from src.parse import html_to_text, parse_filing, tokenize

NUMERIC_TABLE = """
<html><body>
  <p>The Company recorded a material weakness in internal control.</p>
  <table><tr><td>2024</td><td>1,234</td><td>5,678</td></tr>
         <tr><td>2023</td><td>9,012</td><td>3,456</td></tr></table>
</body></html>
"""

TEXT_TABLE = """
<html><body>
  <table><tr><td>We depend on a small number of suppliers for critical components,
  and the loss of any one of them would harm our business.</td></tr></table>
</body></html>
"""

IXBRL = """
<html><body>
  <ix:header><ix:hidden><ix:nonNumeric name="dei:EntityRegistrantName">
    us-gaap MoneyMarketFundsMember</ix:nonNumeric></ix:hidden></ix:header>
  <div style="display:none">hidden boilerplate</div>
  <p>Revenue declined during the quarter.</p>
</body></html>
"""


def test_drops_numeric_table_keeps_narrative():
    text = html_to_text(NUMERIC_TABLE)
    assert "material weakness" in text
    assert "1,234" not in text


def test_keeps_table_that_is_mostly_words():
    text = html_to_text(TEXT_TABLE)
    assert "small number of suppliers" in text


def test_strips_inline_xbrl_scaffolding():
    text = html_to_text(IXBRL)
    assert "Revenue declined" in text
    assert "MoneyMarketFundsMember" not in text
    assert "hidden boilerplate" not in text


def test_tokenize_uppercases_and_drops_numbers():
    tokens = tokenize("Net loss of $3.4 million in 2024, a decline.")
    assert tokens == ["NET", "LOSS", "OF", "MILLION", "IN", "DECLINE"]


def test_parse_filing_shape():
    out = parse_filing(NUMERIC_TABLE)
    assert out["n_words"] > 0
    assert out["counts"]["WEAKNESS"] == 1
