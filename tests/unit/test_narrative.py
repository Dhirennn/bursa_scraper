from __future__ import annotations

import pandas as pd

from bursa_picker.explain.narrative import (
    citations_footer,
    render_pick,
)


def test_render_pick_contains_key_sections():
    row = pd.Series(
        {
            "sector": "Financial Services",
            "score": 1.42,
            "mcap": 2.0e10,
            "adv30": 21_000_000,
            "last_close": 11.2,
        }
    )
    contribs = pd.Series(
        {
            "quality": 0.28,
            "value": 0.42,
            "dividend": 0.11,
            "momentum": -0.03,
            "size": -0.11,
            "sentiment": 0.08,
        }
    )
    fund = pd.Series(
        {
            "returnOnEquity": 0.11,
            "priceToBook": 1.2,
            "trailingPE": 10.0,
            "dividendYield": 0.04,
            "payoutRatio": 0.5,
            "numberOfAnalystOpinions": 14,
            "recommendationMean": 2.0,
            "targetMeanPrice": 12.5,
            "regularMarketPrice": 11.2,
        }
    )
    text = render_pick("MAYBANK", row, contribs, fund, rank=3, total=20)
    assert "MAYBANK" in text
    assert "Financial Services" in text
    assert "+1.42" in text
    assert "Quality" in text
    assert "Value" in text
    assert "Momentum" in text
    assert "weak Bursa evidence" in text  # the committed caveat
    assert "Liquidity" in text


def test_citations_footer_is_deterministic_and_dedups():
    active = ["quality", "value", "quality"]
    footer = citations_footer(active)
    # Novy-Marx appears once even though quality appears twice
    assert footer.count("Novy-Marx") == 1
    # Value citations included
    assert "Fama, E. F." in footer
    # Replication-crisis citation always appended
    assert "Hou, K." in footer
