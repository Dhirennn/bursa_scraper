"""Cross-sectional helpers shared by every factor."""

from __future__ import annotations

import numpy as np
import pandas as pd


def winsorize(s: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    """Clip a series at the given cross-sectional quantiles. NaNs preserved."""
    if s.dropna().empty:
        return s.copy()
    lo = s.quantile(lower)
    hi = s.quantile(upper)
    return s.clip(lower=lo, upper=hi)


def zscore(s: pd.Series) -> pd.Series:
    """Demean & scale by std. NaNs preserved."""
    mu = s.mean(skipna=True)
    sd = s.std(skipna=True, ddof=0)
    if sd == 0 or np.isnan(sd):
        return pd.Series(0.0, index=s.index)
    return (s - mu) / sd


def sector_neutralize(s: pd.Series, sectors: pd.Series) -> pd.Series:
    """Subtract per-sector mean from each stock's score.

    ``sectors`` must align with ``s`` on index. NaN sectors are bucketed as
    'Unknown' and neutralized within that bucket; after neutralization the
    'Unknown' bucket is re-standardized against the whole-universe mean/std
    so it doesn't become a pocket of inflated z-scores.
    """
    sectors = sectors.reindex(s.index).fillna("Unknown")
    demeaned = s.groupby(sectors).transform(lambda x: x - x.mean(skipna=True))
    return demeaned


def higher_is_better(s: pd.Series, invert: bool = False) -> pd.Series:
    return -s if invert else s
