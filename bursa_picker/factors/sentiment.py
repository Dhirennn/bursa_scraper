"""Analyst sentiment factor.

Raw = 0.5 * z(-recommendationMean) + 0.5 * z(targetMeanPrice/last_close - 1)
applied only when numberOfAnalystOpinions >= 3; else raw = 0 (neutral).

Citation: Womack (1996).
"""

from __future__ import annotations

import pandas as pd

from bursa_picker.factors.base import zscore
from bursa_picker.factors.citations import WOMACK_1996

CITATIONS = (WOMACK_1996,)

MIN_ANALYSTS = 3


def compute(df: pd.DataFrame) -> pd.Series:
    n = pd.to_numeric(df.get("numberOfAnalystOpinions"), errors="coerce").fillna(0)
    rec = pd.to_numeric(df.get("recommendationMean"), errors="coerce")
    tgt = pd.to_numeric(df.get("targetMeanPrice"), errors="coerce")
    last = pd.to_numeric(
        df.get("regularMarketPrice").fillna(df.get("previousClose"))
        if "regularMarketPrice" in df.columns
        else df.get("previousClose"),
        errors="coerce",
    )

    upside = (tgt / last) - 1.0
    z_rec = zscore(-rec)
    z_up = zscore(upside)
    raw = 0.5 * z_rec.fillna(0) + 0.5 * z_up.fillna(0)

    # Neutralize when coverage too thin
    raw = raw.where(n >= MIN_ANALYSTS, other=0.0)
    return raw
