"""High-level backtest runner: builds the price panel from the real data
layer, calls the engine, and formats the report."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from bursa_picker.backtest.engine import BacktestResult, run_backtest
from bursa_picker.config import get_settings
from bursa_picker.data.fundamentals import fetch_fundamentals_bulk, fundamentals_frame
from bursa_picker.data.prices import fetch_prices, fetch_prices_bulk
from bursa_picker.data.universe import load_ticker_map, filter_universe
from bursa_picker.logging_setup import get_logger

log = get_logger(__name__)


def run_from_config(
    *,
    start: str,
    end: str,
    top_n: int = 20,
    costs_bps: Optional[float] = None,
    min_fee_myr: Optional[float] = None,
    refresh: bool = False,
    max_workers: int = 8,
) -> BacktestResult:
    """Build the filtered universe, fetch its prices + benchmark, and run."""
    settings = get_settings()
    bt_cfg = settings.backtest
    cbps = costs_bps if costs_bps is not None else bt_cfg.costs_bps
    mfee = min_fee_myr if min_fee_myr is not None else bt_cfg.min_fee_myr

    mapping = load_ticker_map()
    uni = filter_universe(mapping, refresh=refresh, max_workers=max_workers)
    log.info("backtest universe: %d tickers", len(uni))

    sub_map = {t: mapping[t] for t in uni.index if t in mapping}

    prices = fetch_prices_bulk(
        sub_map, start=start, end=end, refresh=refresh, max_workers=max_workers
    )
    bench_df = fetch_prices(bt_cfg.benchmark, start, end, stock_code=None, refresh=refresh)
    if bench_df.empty:
        raise RuntimeError(
            f"benchmark {bt_cfg.benchmark} returned no price data for {start}..{end}"
        )
    col = "adj_close" if "adj_close" in bench_df.columns else "close"
    bench_close = pd.to_numeric(bench_df[col], errors="coerce")

    sectors = uni["sector"]

    return run_backtest(
        prices,
        bench_close,
        sectors,
        start=start,
        end=end,
        top_n=top_n,
        costs_bps=cbps,
        min_fee_myr=mfee,
        rf_annual=bt_cfg.risk_free,
    )
