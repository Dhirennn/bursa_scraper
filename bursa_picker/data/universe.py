"""Ticker universe: load + dedup + liquidity/mcap filter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from bursa_picker.config import get_settings
from bursa_picker.constants import UNKNOWN_SECTOR
from bursa_picker.data.fundamentals import fetch_fundamentals_bulk, fundamentals_frame
from bursa_picker.data.prices import fetch_prices
from bursa_picker.logging_setup import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class TickerRow:
    ticker: str
    stock_code: str
    suspicious: bool  # True when code == "4715" but ticker != "GENM"


def load_ticker_map(path: Path | None = None) -> dict[str, str]:
    """Load ticker_map.txt into ``{TICKER: STOCK_CODE}`` with duplicates removed.

    Duplicate ``TICKER : CODE`` lines collapse to the first occurrence. Lines
    that can't be parsed are skipped with a warning (no exceptions raised;
    the file is user-maintained).
    """
    if path is None:
        path = get_settings().paths.ticker_map
    mapping: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(" : ")
            if len(parts) != 2:
                log.debug("ticker_map.txt line %d unparseable: %r", i, line)
                continue
            t, code = parts[0].strip(), parts[1].strip()
            if t in mapping:
                continue  # keep first
            mapping[t] = code
    log.info("loaded %d unique tickers from %s", len(mapping), path)
    return mapping


def flag_suspicious(mapping: dict[str, str]) -> list[str]:
    """Return the tickers that inherited the 4715 regex-fallback (except GENM)."""
    return [t for t, c in mapping.items() if c == "4715" and t != "GENM"]


def filter_universe(
    mapping: dict[str, str],
    *,
    as_of: str | None = None,
    min_mcap_myr: float | None = None,
    min_adv_myr: float | None = None,
    min_price_myr: float | None = None,
    exclude_sectors: list[str] | None = None,
    refresh: bool = False,
    max_workers: int = 8,
) -> pd.DataFrame:
    """Apply liquidity + size filters and return a DataFrame of survivors.

    Columns: ``[stock_code, sector, mcap, last_close, adv30]`` indexed by ticker.

    ``adv30`` is computed from the cached price SQLite; if the price cache is
    cold for a ticker, its ADV is set to NaN (it will be filtered out when a
    ``min_adv_myr`` is specified).
    """
    cfg = get_settings().universe
    min_mcap = cfg.min_mcap_myr if min_mcap_myr is None else min_mcap_myr
    min_adv = cfg.min_adv_myr if min_adv_myr is None else min_adv_myr
    min_price = cfg.min_price_myr if min_price_myr is None else min_price_myr
    exclude = exclude_sectors if exclude_sectors is not None else cfg.exclude_sectors

    as_of_ts = pd.Timestamp(as_of) if as_of else pd.Timestamp.today().normalize()

    # 1. Fetch fundamentals for everyone (cached)
    payloads = fetch_fundamentals_bulk(mapping, refresh=refresh, max_workers=max_workers)
    f = fundamentals_frame(payloads).copy()
    f["stock_code"] = pd.Series(mapping)
    f["mcap"] = pd.to_numeric(f["marketCap"], errors="coerce")
    f["last_close"] = pd.to_numeric(
        f["regularMarketPrice"].fillna(f["previousClose"]), errors="coerce"
    )

    # 2. Compute 30-day ADV from the price cache (no extra downloads — just reads)
    start = (as_of_ts - pd.Timedelta(days=90)).strftime("%Y-%m-%d")
    end = as_of_ts.strftime("%Y-%m-%d")
    adv: dict[str, float] = {}
    for ticker, code in mapping.items():
        try:
            df = fetch_prices(ticker, start, end, stock_code=code)
        except Exception:
            df = pd.DataFrame()
        if df.empty:
            adv[ticker] = float("nan")
            continue
        tail = df.tail(30)
        values = (tail["close"].astype(float) * tail["volume"].astype(float)).dropna()
        adv[ticker] = float(values.mean()) if len(values) else float("nan")
    f["adv30"] = pd.Series(adv)

    # 3. Apply filters
    mask = pd.Series(True, index=f.index)
    mask &= f["mcap"].fillna(-1) >= min_mcap
    mask &= f["adv30"].fillna(-1) >= min_adv
    mask &= f["last_close"].fillna(-1) >= min_price
    if exclude:
        mask &= ~f["sector"].isin(exclude)

    out = f.loc[mask, ["stock_code", "sector", "mcap", "last_close", "adv30"]].copy()
    out["sector"] = out["sector"].fillna(UNKNOWN_SECTOR)
    log.info(
        "universe filter: %d / %d survived (mcap>=%s, adv>=%s, price>=%s)",
        len(out),
        len(f),
        min_mcap,
        min_adv,
        min_price,
    )
    return out.sort_values("mcap", ascending=False)
