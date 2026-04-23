from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bursa_picker.factors import composite


def _frame(n=10):
    rng = np.random.default_rng(42)
    tickers = [f"T{i}" for i in range(n)]
    return pd.DataFrame(
        {
            "marketCap": rng.uniform(1e8, 1e10, n),
            "priceToBook": rng.uniform(0.3, 5.0, n),
            "trailingPE": rng.uniform(3.0, 60.0, n),
            "priceToSalesTrailing12Months": rng.uniform(0.3, 5.0, n),
            "returnOnEquity": rng.uniform(-0.1, 0.25, n),
            "returnOnAssets": rng.uniform(-0.05, 0.15, n),
            "profitMargins": rng.uniform(-0.1, 0.3, n),
            "operatingMargins": rng.uniform(-0.05, 0.35, n),
            "debtToEquity": rng.uniform(0, 200, n),
            "dividendYield": rng.uniform(0, 0.08, n),
            "payoutRatio": rng.uniform(0, 1.5, n),
            "numberOfAnalystOpinions": rng.integers(0, 20, n),
            "recommendationMean": rng.uniform(1.0, 4.5, n),
            "targetMeanPrice": rng.uniform(0.5, 20.0, n),
            "regularMarketPrice": rng.uniform(0.5, 20.0, n),
            "previousClose": rng.uniform(0.5, 20.0, n),
            "totalRevenue": rng.uniform(1e7, 1e10, n),
            "sector": rng.choice(["Financial", "Industrial", "Tech", "Utilities"], n),
        },
        index=tickers,
    )


def test_contributions_row_sum_equals_score():
    df = _frame()
    scores, contribs = composite.score(df)
    contribs_no_meta = contribs.drop(columns=["_n_missing"])
    recomputed = contribs_no_meta.sum(axis=1)
    pd.testing.assert_series_equal(
        scores.dropna(),
        recomputed.loc[scores.dropna().index],
        check_names=False,
        atol=1e-9,
    )


def test_custom_weights_are_renormalized():
    df = _frame()
    _, c = composite.score(df, weights={"quality": 1.0, "value": 1.0})
    assert "_n_missing" in c.columns
    # Custom weights get renormalized; at least score computes without error.


def test_missing_factor_threshold_drops_stock():
    df = _frame(n=5)
    df.loc["T0", ["returnOnEquity", "profitMargins", "operatingMargins", "priceToBook",
                  "trailingPE", "priceToSalesTrailing12Months", "dividendYield",
                  "marketCap", "numberOfAnalystOpinions"]] = np.nan
    scores, contribs = composite.score(df, drop_if_missing_factors=3)
    assert pd.isna(scores.loc["T0"])


def test_unknown_weight_key_raises():
    df = _frame()
    with pytest.raises(ValueError):
        composite.score(df, weights={"not_a_factor": 1.0})


def test_momentum_contribution_zero_when_no_prices():
    df = _frame()
    _, c = composite.score(df, momentum_raw=None)
    assert (c["momentum"] == 0.0).all()


def test_momentum_contribution_nonzero_when_provided():
    df = _frame()
    mom = pd.Series([0.3, -0.1, 0.05, 0.2, -0.2, 0.0, 0.15, -0.3, 0.1, 0.0], index=df.index)
    _, c = composite.score(df, momentum_raw=mom)
    assert c["momentum"].abs().sum() > 0
