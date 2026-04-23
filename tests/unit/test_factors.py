from __future__ import annotations

import numpy as np
import pandas as pd

from bursa_picker.factors import base, dividend, momentum, quality, sentiment, size, value


def _frame(**col_overrides) -> pd.DataFrame:
    tickers = ["A", "B", "C", "D"]
    base_row = {
        "marketCap": [1e9, 2e9, 3e9, 5e8],
        "priceToBook": [1.0, 2.0, 0.5, 3.0],
        "trailingPE": [10.0, 20.0, 5.0, -5.0],
        "priceToSalesTrailing12Months": [1.0, 2.0, 0.5, 3.0],
        "returnOnEquity": [0.10, 0.05, 0.20, -0.02],
        "returnOnAssets": [0.05, 0.02, 0.12, -0.01],
        "profitMargins": [0.15, 0.08, 0.25, -0.05],
        "operatingMargins": [0.18, 0.10, 0.28, -0.04],
        "debtToEquity": [50.0, 100.0, 20.0, 150.0],
        "dividendYield": [0.04, 0.02, 0.05, 0.0],
        "payoutRatio": [0.5, 0.3, 0.6, 0.0],
        "numberOfAnalystOpinions": [10, 5, 2, 0],
        "recommendationMean": [1.8, 2.5, 3.0, 3.5],
        "targetMeanPrice": [11.0, 9.0, 5.5, 0.5],
        "regularMarketPrice": [10.0, 10.0, 5.0, 1.0],
        "previousClose": [10.0, 10.0, 5.0, 1.0],
        "totalRevenue": [5e8, 2e8, 8e8, 1e8],
        "sector": ["Financial", "Industrials", "Financial", "Industrials"],
    }
    for k, v in col_overrides.items():
        base_row[k] = v
    return pd.DataFrame(base_row, index=tickers)


def test_winsorize_clips_both_tails():
    s = pd.Series([1, 2, 3, 4, 100])
    w = base.winsorize(s, 0.0, 0.80)
    assert w.max() < 100


def test_zscore_is_standardized():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    z = base.zscore(s)
    assert abs(z.mean()) < 1e-9
    assert abs(z.std(ddof=0) - 1.0) < 1e-9


def test_zscore_handles_zero_variance():
    s = pd.Series([3.0, 3.0, 3.0])
    z = base.zscore(s)
    assert (z == 0).all()


def test_sector_neutralize_subtracts_group_mean():
    s = pd.Series([1.0, 3.0, 2.0, 4.0], index=list("ABCD"))
    sectors = pd.Series(["X", "X", "Y", "Y"], index=list("ABCD"))
    out = base.sector_neutralize(s, sectors)
    # sector X mean = 2, sector Y mean = 3
    assert out["A"] == -1.0
    assert out["B"] == 1.0
    assert out["C"] == -1.0
    assert out["D"] == 1.0


def test_quality_higher_for_more_profitable():
    df = _frame()
    q = quality.compute(df)
    # C (ROE 0.20, margin 0.25) should be the highest
    assert q.idxmax() == "C"
    assert q["C"] > q["A"] > q["B"] > q["D"]


def test_value_higher_for_cheaper_stocks():
    df = _frame()
    v = value.compute(df)
    # C has P/B 0.5, P/E 5, P/S 0.5 → cheapest
    assert v.idxmax() == "C"
    # D has negative P/E → E/P ignored, but B/M and S/P still penalise it
    assert v["D"] < v["C"]


def test_dividend_penalizes_excessive_payout():
    df = _frame(payoutRatio=[0.5, 0.5, 1.5, 0.0])  # C is paying out 150%
    d = dividend.compute(df)
    # A has yield 0.04 payout 0.5 → penalty = (1-0.5)+0.5 = 1.0
    # C has yield 0.05 payout 1.5 → penalty = max(-0.5, 1-1.5) + 0.5 = 0.0, floored by clip
    assert d["A"] > d["C"] or d["C"] == 0  # either penalised significantly or zeroed


def test_size_rewards_smaller_mcap_after_winsorize():
    df = _frame()
    sz = size.compute(df)
    # D (5e8) is smallest → highest pre-winsorize, but also may be clipped
    assert sz.idxmax() == "D"


def test_sentiment_zeroes_below_min_analysts():
    df = _frame()
    st = sentiment.compute(df)
    # C has 2 analysts (below MIN_ANALYSTS=3); D has 0 → both zeroed
    assert st["C"] == 0.0
    assert st["D"] == 0.0
    # A has 10 analysts, low (bullish) rec, decent upside → positive
    assert st["A"] > 0


def test_momentum_from_prices():
    idx = pd.bdate_range(end=pd.Timestamp("2024-12-31"), periods=300)
    up = pd.DataFrame({"adj_close": np.linspace(5, 10, 300)}, index=idx)  # +100%
    flat = pd.DataFrame({"adj_close": [10.0] * 300}, index=idx)
    down = pd.DataFrame({"adj_close": np.linspace(10, 5, 300)}, index=idx)
    prices = {"UP": up, "FLAT": flat, "DOWN": down}
    mom = momentum.compute_from_prices(prices, pd.Timestamp("2024-12-31"))
    assert mom["UP"] > 0
    assert abs(mom["FLAT"]) < 1e-9
    assert mom["DOWN"] < 0
