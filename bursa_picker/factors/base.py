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


def sector_neutralize(
    s: pd.Series, sectors: pd.Series, min_sector_size: int = 3
) -> pd.Series:
    """Subtract per-sector mean from each stock's score.

    Sectors with fewer than ``min_sector_size`` stocks are demeaned against
    the *global* mean instead. This avoids degenerate cases where a
    single-stock sector would subtract itself and produce an exact-zero
    z-score.
    """
    sectors = sectors.reindex(s.index).fillna("Unknown")
    counts = sectors.value_counts()
    small_sectors = set(counts[counts < min_sector_size].index)

    effective = sectors.where(~sectors.isin(small_sectors), other="__GLOBAL__")
    demeaned = s.groupby(effective).transform(lambda x: x - x.mean(skipna=True))
    return demeaned


def higher_is_better(s: pd.Series, invert: bool = False) -> pd.Series:
    return -s if invert else s
