"""Value factor: mean of z(1/P/B), z(1/P/E), z(1/P/S).

Higher = cheaper. Negative-earnings tickers get E/P = NaN (ignored in mean).
Citations: Fama-French (1992); Asness-Moskowitz-Pedersen (2013); Bursa
Carhart 4F study (2011-2021).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bursa_picker.factors.base import zscore
from bursa_picker.factors.citations import (
    ASNESS_MOSKOWITZ_PEDERSEN_2013,
    CARHART_BURSA_2011_2021,
    FAMA_FRENCH_1992,
)

CITATIONS = (FAMA_FRENCH_1992, ASNESS_MOSKOWITZ_PEDERSEN_2013, CARHART_BURSA_2011_2021)


def _inv(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    return 1.0 / s.where(s > 0)


def compute(df: pd.DataFrame) -> pd.Series:
    b_over_p = _inv(df.get("priceToBook"))
    e_over_p = _inv(df.get("trailingPE"))
    s_over_p = _inv(df.get("priceToSalesTrailing12Months"))

    parts = pd.concat(
        {
            "bm": zscore(b_over_p),
            "ep": zscore(e_over_p),
            "sp": zscore(s_over_p),
        },
        axis=1,
    )
    return parts.mean(axis=1, skipna=True)
