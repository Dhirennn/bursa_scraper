"""Momentum factor: 12-minus-1 month price return.

Raw = close(t-21) / close(t-252) - 1

Soft weight. Carhart 4F study on Bursa 2011-2021 finds momentum NOT
significant in size-sorted Bursa portfolios — we keep this as a tiebreaker.
Citations: Jegadeesh-Titman (1993); Bursa Carhart caveat.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bursa_picker.factors.citations import (
    CARHART_BURSA_2011_2021,
    JEGADEESH_TITMAN_1993,
)

CITATIONS = (JEGADEESH_TITMAN_1993, CARHART_BURSA_2011_2021)


def compute_from_prices(
    prices: dict[str, pd.DataFrame],
    as_of: pd.Timestamp,
    skip_days: int = 21,
    window_days: int = 252,
) -> pd.Series:
    """Return per-ticker 12-1 month log-price return, indexed by ticker.

    ``prices`` maps ticker → DataFrame (indexed by date) with at least a
    ``close`` column. Uses adj_close when present.
    """
    out: dict[str, float] = {}
    for t, df in prices.items():
        if df is None or df.empty:
            out[t] = float("nan")
            continue
        col = "adj_close" if "adj_close" in df.columns else "close"
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) < window_days + 1:
            out[t] = float("nan")
            continue
        s = s[s.index <= as_of]
        if len(s) < window_days + 1:
            out[t] = float("nan")
            continue
        p_recent = s.iloc[-skip_days] if skip_days <= len(s) else s.iloc[-1]
        p_old = s.iloc[-window_days]
        if p_old <= 0:
            out[t] = float("nan")
            continue
        out[t] = float(p_recent / p_old - 1.0)
    return pd.Series(out, name="momentum")
