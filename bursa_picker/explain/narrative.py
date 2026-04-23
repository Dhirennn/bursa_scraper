"""Plain-English per-pick narrative builder.

Deliberately template-assembled (not LLM) so the output is deterministic,
auditable, and cheap. Every sentence is backed by a factor contribution.
"""

from __future__ import annotations

import pandas as pd

from bursa_picker.factors.citations import (
    ARNOTT_ASNESS_2003,
    ASNESS_MOSKOWITZ_PEDERSEN_2013,
    CARHART_BURSA_2011_2021,
    FAMA_FRENCH_1992,
    GORDON_2013_EM_QUALITY,
    HOU_XUE_ZHANG_2020,
    JEGADEESH_TITMAN_1993,
    NOVY_MARX_2013,
    WOMACK_1996,
)

DISCLAIMER = (
    "Literature suggests these factors have historically been associated with "
    "excess returns in Malaysian / EM equities. This is not a forecast; it is a "
    "systematic ranking based on publicly available data as of {date}."
)


def _quintile(rank: int, n: int) -> str:
    q = max(1, min(5, 1 + rank * 5 // max(1, n)))
    return {1: "top", 2: "upper", 3: "mid", 4: "lower", 5: "bottom"}[q]


def _quality_sentence(contrib: float, row: pd.Series, fund: pd.Series) -> str:
    if contrib > 0.05:
        roe = fund.get("returnOnEquity")
        roe_str = f"ROE {roe * 100:.1f}%" if pd.notna(roe) else "strong profitability"
        return f"Quality: {roe_str} and positive gross-profitability proxy contribute +{contrib:.2f}."
    if contrib < -0.05:
        return f"Quality: below-sector profitability drags {contrib:+.2f}."
    return f"Quality: neutral ({contrib:+.2f})."


def _value_sentence(contrib: float, row: pd.Series, fund: pd.Series) -> str:
    if contrib > 0.05:
        pb = fund.get("priceToBook")
        pe = fund.get("trailingPE")
        pieces = []
        if pd.notna(pb):
            pieces.append(f"P/B {pb:.2f}")
        if pd.notna(pe) and pe > 0:
            pieces.append(f"P/E {pe:.1f}")
        tail = ", ".join(pieces) if pieces else "cheap on multiple metrics"
        return f"Value: {tail}; sector-adjusted cheapness contributes +{contrib:.2f}."
    if contrib < -0.05:
        return f"Value: richly priced relative to peers, drags {contrib:+.2f}."
    return f"Value: neutral ({contrib:+.2f})."


def _dividend_sentence(contrib: float, row: pd.Series, fund: pd.Series) -> str:
    y = fund.get("dividendYield")
    if pd.isna(y) or y == 0:
        return f"Dividend: none or unreported ({contrib:+.2f})."
    y_pct = y * 100 if abs(y) <= 1 else y
    p = fund.get("payoutRatio")
    payout_str = f", payout {p * 100:.0f}%" if pd.notna(p) else ""
    return f"Dividend: trailing yield {y_pct:.2f}%{payout_str} contributes {contrib:+.2f}."


def _momentum_sentence(contrib: float) -> str:
    caveat = " (weak Bursa evidence — used as tiebreaker)"
    if abs(contrib) < 0.02:
        return f"Momentum: flat 12-1m return, neutral ({contrib:+.2f}){caveat}."
    direction = "positive" if contrib > 0 else "negative"
    return f"Momentum: {direction} 12-1m trend contributes {contrib:+.2f}{caveat}."


def _size_sentence(contrib: float, row: pd.Series) -> str:
    mcap = row.get("mcap")
    if pd.isna(mcap):
        return f"Size: unknown market cap ({contrib:+.2f})."
    size_label = "mega-cap" if mcap > 5e10 else "large-cap" if mcap > 1e10 else "mid-cap" if mcap > 2e9 else "small-cap"
    return f"Size: {size_label} (RM {mcap / 1e6:,.0f}m); tilt contribution {contrib:+.2f}."


def _sentiment_sentence(contrib: float, fund: pd.Series) -> str:
    n = fund.get("numberOfAnalystOpinions")
    if pd.isna(n) or n < 3:
        return f"Analyst coverage: thin or none; sentiment neutralised ({contrib:+.2f})."
    rec = fund.get("recommendationMean")
    tgt = fund.get("targetMeanPrice")
    last = fund.get("regularMarketPrice")
    bits = []
    if pd.notna(rec):
        bits.append(f"consensus {rec:.1f}/5")
    if pd.notna(tgt) and pd.notna(last) and last > 0:
        bits.append(f"{((tgt / last) - 1) * 100:+.1f}% to target")
    tail = ", ".join(bits) if bits else ""
    return f"Analyst ({int(n)}): {tail}; contribution {contrib:+.2f}."


_CITATION_BY_FACTOR = {
    "quality": (NOVY_MARX_2013, GORDON_2013_EM_QUALITY),
    "value": (FAMA_FRENCH_1992, ASNESS_MOSKOWITZ_PEDERSEN_2013, CARHART_BURSA_2011_2021),
    "dividend": (ARNOTT_ASNESS_2003,),
    "momentum": (JEGADEESH_TITMAN_1993, CARHART_BURSA_2011_2021),
    "size": (FAMA_FRENCH_1992,),
    "sentiment": (WOMACK_1996,),
}


def citations_footer(active_factors: list[str]) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for f in active_factors:
        for cit in _CITATION_BY_FACTOR.get(f, ()):
            key = cit.short()
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"• {cit.full()}")
    lines.append(f"• {HOU_XUE_ZHANG_2020.full()}")
    return "\n".join(lines)


def render_pick(
    ticker: str,
    row: pd.Series,
    contribs: pd.Series,
    fund: pd.Series,
    *,
    rank: int,
    total: int,
) -> str:
    parts = []
    parts.append(
        f"{ticker} ({row['sector']}) — composite score {row['score']:+.2f}, "
        f"ranked #{rank} of {total}."
    )
    parts.append(_quality_sentence(contribs["quality"], row, fund))
    parts.append(_value_sentence(contribs["value"], row, fund))
    parts.append(_dividend_sentence(contribs["dividend"], row, fund))
    parts.append(_momentum_sentence(contribs["momentum"]))
    parts.append(_size_sentence(contribs["size"], row))
    parts.append(_sentiment_sentence(contribs["sentiment"], fund))
    adv = row.get("adv30")
    if pd.notna(adv):
        parts.append(f"Liquidity: 30d ADV RM {adv / 1e3:,.0f}k.")
    return "\n".join(parts)
