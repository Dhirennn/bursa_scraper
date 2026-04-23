"""Size tilt factor: -log(marketCap).

Small-cap premium (Fama-French 1992) exists on Bursa but microcaps are
filtered by the universe liquidity gate *before* this factor is scored.
Winsorized at the 20th percentile within-universe so the smallest survivors
don't dominate.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bursa_picker.factors.citations import FAMA_FRENCH_1992

CITATIONS = (FAMA_FRENCH_1992,)


def compute(df: pd.DataFrame) -> pd.Series:
    mcap = pd.to_numeric(df.get("marketCap"), errors="coerce")
    log_mcap = np.log(mcap.where(mcap > 0))
    raw = -log_mcap
    if not raw.dropna().empty:
        lo = raw.quantile(0.20)
        raw = raw.clip(lower=lo)
    return raw
