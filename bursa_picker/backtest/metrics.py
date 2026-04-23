"""Backtest performance metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def cagr(nav: pd.Series) -> float:
    if len(nav) < 2 or nav.iloc[0] <= 0:
        return float("nan")
    years = (nav.index[-1] - nav.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return float((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1)


def sharpe(returns: pd.Series, rf_annual: float = 0.03, periods_per_year: int = 12) -> float:
    if returns.empty:
        return float("nan")
    rf_period = (1 + rf_annual) ** (1 / periods_per_year) - 1
    excess = returns - rf_period
    sd = excess.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return float(excess.mean() / sd * np.sqrt(periods_per_year))


def max_drawdown(nav: pd.Series) -> float:
    if nav.empty:
        return float("nan")
    peak = nav.cummax()
    dd = nav / peak - 1.0
    return float(dd.min())


def hit_rate(strat_returns: pd.Series, bench_returns: pd.Series) -> float:
    aligned = pd.concat({"s": strat_returns, "b": bench_returns}, axis=1).dropna()
    if aligned.empty:
        return float("nan")
    wins = (aligned["s"] > aligned["b"]).sum()
    return float(wins / len(aligned))
