"""Dividend factor with payout-sustainability guard.

Raw = dividendYield * min(1.0, (1 - payoutRatio) + 0.5)
so payouts above 100% get linearly penalised; floor at 0.5.

Citations: Lintner (1956); Arnott-Asness (2003).
"""

from __future__ import annotations

import pandas as pd

from bursa_picker.factors.citations import ARNOTT_ASNESS_2003

CITATIONS = (ARNOTT_ASNESS_2003,)


def compute(df: pd.DataFrame) -> pd.Series:
    yield_ = pd.to_numeric(df.get("dividendYield"), errors="coerce")
    if yield_ is None:
        yield_ = pd.Series(dtype=float, index=df.index)

    # yfinance reports dividendYield as a fraction (e.g. 0.05) in newer
    # versions. If values are absurdly large (>1) assume the older percent
    # representation and divide by 100.
    yield_ = yield_.where(yield_.abs() <= 1.0, yield_ / 100.0)

    payout = pd.to_numeric(df.get("payoutRatio"), errors="coerce")
    penalty = (1.0 - payout).clip(lower=-0.5) + 0.5
    penalty = penalty.clip(upper=1.0)
    # If payout is null, leave yield un-penalised.
    penalty = penalty.fillna(1.0)

    raw = yield_.fillna(0.0) * penalty
    return raw
