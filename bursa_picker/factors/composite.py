"""Composite scorer: winsorize → z-score → sector-neutralize → weighted sum.

Returns (score, contributions) where:
  score         : pd.Series of total composite score per ticker
  contributions : pd.DataFrame indexed by ticker, columns are factor names,
                  values are w_f · zsn_{f,i}. Row sum equals score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from bursa_picker.factors import dividend, momentum, quality, sentiment, size, value
from bursa_picker.factors.base import sector_neutralize, winsorize, zscore


@dataclass(frozen=True)
class FactorSpec:
    name: str
    compute: Callable[[pd.DataFrame], pd.Series]
    weight: float


DEFAULT_SPECS: tuple[FactorSpec, ...] = (
    FactorSpec("quality", quality.compute, 0.35),
    FactorSpec("value", value.compute, 0.30),
    FactorSpec("dividend", dividend.compute, 0.10),
    # momentum is handled separately because it needs the price frame
    FactorSpec("size", size.compute, 0.05),
    FactorSpec("sentiment", sentiment.compute, 0.10),
)


def _prepare_factor(
    raw: pd.Series, sectors: pd.Series, lower: float, upper: float
) -> pd.Series:
    w = winsorize(raw, lower=lower, upper=upper)
    z = zscore(w)
    return sector_neutralize(z, sectors).fillna(0.0)


def score(
    fundamentals: pd.DataFrame,
    *,
    momentum_raw: pd.Series | None = None,
    weights: dict[str, float] | None = None,
    winsorize_bounds: tuple[float, float] = (0.01, 0.99),
    drop_if_missing_factors: int = 3,
) -> tuple[pd.Series, pd.DataFrame]:
    """Compute composite scores and per-factor contributions.

    ``fundamentals`` is the frame returned by ``fundamentals_frame``; must
    include a ``sector`` column. ``momentum_raw`` is an optional Series of
    per-ticker 12-1 returns (from ``momentum.compute_from_prices``). When
    None, momentum's contribution is 0 for everyone.

    ``weights`` overrides the built-in defaults; keys must be subset of
    {quality,value,dividend,momentum,size,sentiment}. Unrecognised keys
    raise. Weights are re-normalised to 1.0.
    """
    df = fundamentals.copy()
    sectors = df["sector"].fillna("Unknown")

    # Resolve weights
    w = {
        "quality": 0.35,
        "value": 0.30,
        "dividend": 0.10,
        "momentum": 0.10,
        "size": 0.05,
        "sentiment": 0.10,
    }
    if weights:
        unknown = set(weights) - set(w)
        if unknown:
            raise ValueError(f"Unknown factor keys: {sorted(unknown)}")
        w.update(weights)
    total = sum(w.values())
    if total <= 0:
        raise ValueError("weights sum to zero")
    w = {k: v / total for k, v in w.items()}

    lower, upper = winsorize_bounds
    contribs: dict[str, pd.Series] = {}

    for spec in DEFAULT_SPECS:
        raw = spec.compute(df).reindex(df.index)
        zsn = _prepare_factor(raw, sectors, lower, upper)
        contribs[spec.name] = zsn * w[spec.name]

    if momentum_raw is not None:
        mom_zsn = _prepare_factor(
            momentum_raw.reindex(df.index), sectors, lower, upper
        )
        contribs["momentum"] = mom_zsn * w["momentum"]
    else:
        contribs["momentum"] = pd.Series(0.0, index=df.index)

    # Count missing factors per ticker (using raw signals before z)
    raw_frame = pd.DataFrame(
        {
            "quality": quality.compute(df).reindex(df.index),
            "value": value.compute(df).reindex(df.index),
            "dividend": dividend.compute(df).reindex(df.index),
            "size": size.compute(df).reindex(df.index),
            "sentiment": sentiment.compute(df).reindex(df.index),
        }
    )
    if momentum_raw is not None:
        raw_frame["momentum"] = momentum_raw.reindex(df.index)
    else:
        raw_frame["momentum"] = pd.NA

    n_missing = raw_frame.isna().sum(axis=1)

    contributions = pd.DataFrame(contribs)
    contributions = contributions[list(w.keys())]  # column order matches weights
    scores = contributions.sum(axis=1)

    # Drop stocks with too many missing factors
    keep = n_missing < drop_if_missing_factors
    scores = scores.where(keep)
    contributions = contributions.where(keep, other=0.0)
    contributions["_n_missing"] = n_missing

    return scores, contributions
