from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from bursa_picker.backtest import costs, engine, metrics


def _ramp(start_price, slope, days=1200, start="2019-01-01"):
    idx = pd.bdate_range(start=start, periods=days)
    vals = [start_price * (1 + slope * i) for i in range(days)]
    return pd.DataFrame(
        {"adj_close": vals, "close": vals, "volume": [1e6] * days}, index=idx
    )


def test_cost_fraction_zero_turnover_zero_cost():
    assert costs.cost_fraction(0.0, 50.0) == 0.0


def test_cost_fraction_100pct_turnover_50bps():
    assert abs(costs.cost_fraction(1.0, 50.0) - 0.005) < 1e-12


def test_cagr_sharpe_maxdd_on_monotonic_curve():
    idx = pd.date_range("2020-01-31", periods=60, freq="ME")
    nav = pd.Series(np.linspace(100, 200, 60), index=idx)
    c = metrics.cagr(nav)
    assert 0.14 < c < 0.16  # ~15% compounded
    monthly_rets = nav.pct_change().dropna()
    s = metrics.sharpe(monthly_rets)
    assert s > 0
    assert metrics.max_drawdown(nav) == pytest.approx(0.0, abs=1e-9)


def test_backtest_strategy_beats_flat_and_declining_peers():
    # 4 tickers: A ramps up (best momentum/trend), B down, C flat, D noisy
    up = _ramp(5, 0.001, days=1200)
    down = _ramp(20, -0.0005, days=1200)
    flat = _ramp(10, 0.0, days=1200)
    rng = np.random.default_rng(0)
    noisy_vals = [10 * (1 + rng.normal(0, 0.02)) for _ in range(1200)]
    idx = pd.bdate_range(start="2019-01-01", periods=1200)
    noisy = pd.DataFrame(
        {"adj_close": noisy_vals, "close": noisy_vals, "volume": [1e6] * 1200}, index=idx
    )

    prices = {"A": up, "B": down, "C": flat, "D": noisy}
    sectors = pd.Series({"A": "S1", "B": "S1", "C": "S2", "D": "S2"})
    bench = pd.Series(np.linspace(1000, 1100, 1200), index=idx)

    res = engine.run_backtest(
        prices,
        bench,
        sectors,
        start="2020-01-01",
        end="2023-06-30",
        top_n=1,
        costs_bps=10,
        min_fee_myr=0,
    )

    assert res.report["N_rebalances"] >= 12
    # Final NAV > initial: ramp-up stock should dominate picks
    assert res.report["NAV_final"] > 100_000
    # Picks should prominently feature A
    pick_counts: dict[str, int] = {}
    for ts, picks in res.picks_log.items():
        for p in picks:
            pick_counts[p] = pick_counts.get(p, 0) + 1
    assert pick_counts.get("A", 0) > pick_counts.get("B", 0)
