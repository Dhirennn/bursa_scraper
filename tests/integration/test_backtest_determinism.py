"""Backtest must be deterministic given identical inputs (no stochastic ops)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from bursa_picker.backtest.engine import run_backtest


def _sample_universe(n=6, days=1000, seed=7):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start="2019-01-01", periods=days)
    prices = {}
    for i in range(n):
        drift = rng.uniform(-0.0004, 0.0008)
        noise = rng.normal(0, 0.01, days)
        vals = [10 * (1 + drift * j) * (1 + noise[j]) for j in range(days)]
        prices[f"T{i}"] = pd.DataFrame(
            {"adj_close": vals, "close": vals, "volume": [1e6] * days},
            index=idx,
        )
    bench = pd.Series(np.linspace(1000, 1050, days), index=idx)
    sectors = pd.Series(
        {f"T{i}": "SecA" if i % 2 == 0 else "SecB" for i in range(n)}
    )
    return prices, bench, sectors


def test_backtest_is_deterministic():
    prices, bench, sectors = _sample_universe()
    r1 = run_backtest(
        prices, bench, sectors,
        start="2020-01-01", end="2022-12-31",
        top_n=3, costs_bps=50, min_fee_myr=0,
    )
    r2 = run_backtest(
        prices, bench, sectors,
        start="2020-01-01", end="2022-12-31",
        top_n=3, costs_bps=50, min_fee_myr=0,
    )
    pd.testing.assert_series_equal(r1.nav, r2.nav)
    assert r1.report == r2.report
    assert r1.picks_log == r2.picks_log
