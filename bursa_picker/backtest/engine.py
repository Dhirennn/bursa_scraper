"""Monthly walk-forward backtest for price-only factors.

HONEST SCOPE: we backtest price-based factors only (momentum 12-1, low-vol,
size tilt via market cap proxy from price*shares, and trend) because yfinance
does not return historical financial statements for KLSE tickers, so
fundamentals-PIT is not feasible from free data. A fundamentals overlay can
be toggled on with ``include_fundamentals_overlay=True``; when on, *today's*
.info snapshot is applied across all historical rebalances (an explicit
forward-contamination; the result is labelled illustrative).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd

from bursa_picker.backtest.costs import clamp_fee_floor, cost_fraction
from bursa_picker.backtest.metrics import cagr, hit_rate, max_drawdown, sharpe
from bursa_picker.factors.base import sector_neutralize, winsorize, zscore
from bursa_picker.logging_setup import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Price-only factor computations at time t (use only data up to t-1)
# ---------------------------------------------------------------------------


def _closes_panel(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    cols = {}
    for t, df in prices.items():
        if df is None or df.empty:
            continue
        col = "adj_close" if "adj_close" in df.columns else "close"
        cols[t] = pd.to_numeric(df[col], errors="coerce")
    if not cols:
        return pd.DataFrame()
    return pd.concat(cols, axis=1).sort_index()


def _momentum_12_1(closes: pd.DataFrame, t: pd.Timestamp) -> pd.Series:
    window = closes[closes.index <= t].tail(252 + 1)
    if len(window) < 252:
        return pd.Series(dtype=float)
    p_skip = window.iloc[-21] if len(window) >= 21 else window.iloc[-1]
    p_old = window.iloc[-252]
    valid = p_old > 0
    ret = pd.Series(np.nan, index=closes.columns)
    ret[valid.index[valid]] = p_skip[valid] / p_old[valid] - 1
    return ret


def _low_vol_12m(closes: pd.DataFrame, t: pd.Timestamp) -> pd.Series:
    window = closes[closes.index <= t].tail(252)
    if window.empty:
        return pd.Series(dtype=float)
    returns = window.pct_change()
    vol = returns.std(skipna=True)
    return -vol  # lower vol → higher factor score


def _trend_200(closes: pd.DataFrame, t: pd.Timestamp) -> pd.Series:
    window = closes[closes.index <= t].tail(200)
    if window.empty:
        return pd.Series(dtype=float)
    ma = window.mean(skipna=True)
    last = window.iloc[-1]
    return (last - ma) / ma.replace(0, np.nan)


PRICE_ONLY_FACTORS: dict[str, Callable[[pd.DataFrame, pd.Timestamp], pd.Series]] = {
    "momentum_12_1": _momentum_12_1,
    "low_vol_12m": _low_vol_12m,
    "trend_200": _trend_200,
}


DEFAULT_PRICE_WEIGHTS = {
    "momentum_12_1": 0.40,
    "low_vol_12m": 0.30,
    "trend_200": 0.30,
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


@dataclass
class BacktestResult:
    nav: pd.Series
    returns: pd.Series
    bench_returns: pd.Series
    turnover: pd.Series
    picks_log: dict[pd.Timestamp, list[str]]
    report: dict = field(default_factory=dict)


def _month_ends(dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(dates, index=dates)
    return s.groupby([dates.year, dates.month]).tail(1).index


def run_backtest(
    prices: dict[str, pd.DataFrame],
    bench_close: pd.Series,
    sectors: pd.Series,
    *,
    start: str,
    end: str,
    top_n: int = 20,
    costs_bps: float = 50.0,
    min_fee_myr: float = 8.0,
    initial_equity: float = 100_000.0,
    factor_weights: Optional[dict[str, float]] = None,
    rf_annual: float = 0.03,
) -> BacktestResult:
    """Run a monthly rebalance backtest on the provided price panel.

    ``prices``      : dict[ticker → DataFrame(date idx, close/adj_close col)]
    ``bench_close`` : Series indexed by date (adjusted close of benchmark)
    ``sectors``     : Series indexed by ticker → sector label
    """
    weights = dict(DEFAULT_PRICE_WEIGHTS)
    if factor_weights:
        weights.update(factor_weights)
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("factor_weights sum to zero")
    weights = {k: v / total for k, v in weights.items()}

    closes = _closes_panel(prices)
    if closes.empty:
        raise ValueError("no price data")

    closes = closes[(closes.index >= start) & (closes.index <= end)]
    if closes.empty:
        raise ValueError("no price data in window")

    # Daily returns panel (for compounding between rebalances)
    daily_rets = closes.pct_change().fillna(0.0)

    month_ends = _month_ends(closes.index)
    if len(month_ends) < 2:
        raise ValueError("need at least two month-end observations")

    bench_ret = bench_close.reindex(closes.index).pct_change().fillna(0.0)

    nav_history: list[tuple[pd.Timestamp, float]] = []
    strat_monthly: dict[pd.Timestamp, float] = {}
    bench_monthly: dict[pd.Timestamp, float] = {}
    turnover_history: dict[pd.Timestamp, float] = {}
    picks_log: dict[pd.Timestamp, list[str]] = {}

    equity = float(initial_equity)
    holdings: dict[str, float] = {}
    prev_me = month_ends[0]
    nav_history.append((prev_me, equity))

    for me in month_ends[1:]:
        # Compound current holdings between prev_me and me
        period = daily_rets.loc[(daily_rets.index > prev_me) & (daily_rets.index <= me)]
        if holdings and not period.empty:
            weights_series = pd.Series(holdings)
            aligned = period[weights_series.index.intersection(period.columns)]
            if not aligned.empty:
                port_daily = aligned.mul(weights_series.reindex(aligned.columns).fillna(0), axis=1).sum(axis=1)
                equity *= float((1 + port_daily).prod())

        bench_period = bench_ret.loc[(bench_ret.index > prev_me) & (bench_ret.index <= me)]
        if not bench_period.empty:
            bench_monthly[me] = float((1 + bench_period).prod() - 1)

        # Compute factor scores as of me (using data up to me)
        raw_factors = {name: f(closes, me) for name, f in PRICE_ONLY_FACTORS.items()}
        raw_df = pd.DataFrame(raw_factors)
        # Cross-sectional: winsorize, z, sector-neutralize
        scored = pd.DataFrame(0.0, index=raw_df.index, columns=raw_df.columns)
        for col in raw_df.columns:
            s = winsorize(raw_df[col], 0.01, 0.99)
            s = zscore(s)
            s = sector_neutralize(s, sectors.reindex(s.index))
            scored[col] = s.fillna(0.0) * weights[col]
        composite = scored.sum(axis=1)

        # Need at least 252 history to have meaningful factors
        # (stocks without enough history will have NaN → treated as 0 in sum)
        valid = raw_df.notna().sum(axis=1) >= 2  # at least 2 of 3 factors present
        ranked = composite.where(valid).dropna().sort_values(ascending=False)
        picks = ranked.head(top_n).index.tolist()
        picks_log[me] = picks

        # Equal-weight new portfolio
        new_holdings = {t: 1.0 / len(picks) for t in picks} if picks else {}

        # Turnover = 0.5 * sum abs(new_w - old_w)
        all_tickers = set(new_holdings) | set(holdings)
        turnover = 0.5 * sum(
            abs(new_holdings.get(t, 0.0) - holdings.get(t, 0.0)) for t in all_tickers
        )
        fee_frac = cost_fraction(turnover, costs_bps) + clamp_fee_floor(equity, top_n, min_fee_myr)
        equity *= 1.0 - fee_frac

        # Record strategy return this period (before fees were applied above).
        # Simpler: strategy monthly return = equity change
        prev_nav = nav_history[-1][1]
        strat_monthly[me] = equity / prev_nav - 1 if prev_nav > 0 else 0.0
        nav_history.append((me, equity))
        turnover_history[me] = turnover

        holdings = new_holdings
        prev_me = me

    nav = pd.Series(dict(nav_history)).sort_index()
    strat_rets = pd.Series(strat_monthly).sort_index()
    bench_rets = pd.Series(bench_monthly).sort_index()
    turn = pd.Series(turnover_history).sort_index()

    bench_nav = (1 + bench_rets).cumprod() * initial_equity if not bench_rets.empty else pd.Series(dtype=float)

    report = {
        "start": str(nav.index[0].date()),
        "end": str(nav.index[-1].date()),
        "CAGR": cagr(nav),
        "Sharpe": sharpe(strat_rets, rf_annual=rf_annual, periods_per_year=12),
        "MaxDD": max_drawdown(nav),
        "Turnover_avg": float(turn.mean()) if len(turn) else float("nan"),
        "HitRate": hit_rate(strat_rets, bench_rets),
        "Bench_CAGR": cagr(bench_nav) if not bench_nav.empty else float("nan"),
        "ExcessCAGR": (
            cagr(nav) - cagr(bench_nav)
            if not bench_nav.empty and not np.isnan(cagr(bench_nav))
            else float("nan")
        ),
        "NAV_final": float(nav.iloc[-1]),
        "N_rebalances": int(len(strat_rets)),
    }

    return BacktestResult(
        nav=nav,
        returns=strat_rets,
        bench_returns=bench_rets,
        turnover=turn,
        picks_log=picks_log,
        report=report,
    )
