"""SQLite-cached fundamentals (.info snapshot) fetcher for KLSE tickers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yfinance as yf

from bursa_picker.config import get_settings
from bursa_picker.constants import UNKNOWN_SECTOR
from bursa_picker.data.ratelimit import throttle, with_retry
from bursa_picker.logging_setup import get_logger, incr

log = get_logger(__name__)

# Fields we actually use downstream. Anything else in .info is also stored
# (we persist the full blob) but these are the canonical accessors.
FIELDS: tuple[str, ...] = (
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "priceToSalesTrailing12Months",
    "returnOnEquity",
    "returnOnAssets",
    "profitMargins",
    "operatingMargins",
    "grossMargins",
    "debtToEquity",
    "marketCap",
    "sector",
    "industry",
    "dividendYield",
    "trailingAnnualDividendYield",
    "payoutRatio",
    "totalRevenue",
    "totalDebt",
    "totalCash",
    "operatingCashflow",
    "numberOfAnalystOpinions",
    "targetMeanPrice",
    "targetMedianPrice",
    "recommendationMean",
    "recommendationKey",
    "sharesOutstanding",
    "beta",
    "revenueGrowth",
    "earningsGrowth",
    "trailingEps",
    "bookValue",
    "revenuePerShare",
    "netIncomeToCommon",
    "previousClose",
    "regularMarketPrice",
)


@contextmanager
def _conn(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db_path)
    c.execute("PRAGMA journal_mode=WAL")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _init_schema(c: sqlite3.Connection) -> None:
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS fundamentals (
            ticker TEXT PRIMARY KEY,
            fetched_at_utc TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ttl_ok(fetched_at_utc: str, ttl_hours: float) -> bool:
    last = datetime.fromisoformat(fetched_at_utc)
    return (_now_utc() - last).total_seconds() < ttl_hours * 3600


@throttle("yfinance", rps=2.0)
@with_retry(max_attempts=4, backoff_base=1.5)
def _download(symbol: str) -> dict[str, Any]:
    info = yf.Ticker(symbol).info
    return dict(info) if info else {}


def _db_path() -> Path:
    return get_settings().paths.cache_dir / "fundamentals.sqlite"


def fetch_fundamentals(
    ticker: str,
    stock_code: str,
    refresh: bool = False,
) -> dict[str, Any]:
    """Cache-first fundamentals fetch. Returns the full .info blob."""
    settings = get_settings()
    ttl = settings.cache.fundamentals_ttl_hours
    symbol = f"{stock_code}.KL"
    with _conn(_db_path()) as c:
        _init_schema(c)
        row = c.execute(
            "SELECT fetched_at_utc, payload_json FROM fundamentals WHERE ticker = ?",
            (ticker,),
        ).fetchone()

        if not refresh and row and _ttl_ok(row[0], ttl):
            incr("cache_hits")
            try:
                return json.loads(row[1])
            except json.JSONDecodeError:
                pass  # fall through to re-fetch

        try:
            payload = _download(symbol)
            c.execute(
                "INSERT OR REPLACE INTO fundamentals(ticker, fetched_at_utc, payload_json)"
                " VALUES (?,?,?)",
                (ticker, _now_utc().isoformat(), json.dumps(payload)),
            )
            incr("cache_misses")
            return payload
        except Exception as e:
            log.warning("fundamentals fetch failed for %s: %s", symbol, e)
            if row:
                try:
                    return json.loads(row[1])
                except json.JSONDecodeError:
                    return {}
            return {}


def fetch_fundamentals_bulk(
    ticker_to_code: dict[str, str],
    refresh: bool = False,
    max_workers: int = 8,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    tickers = list(ticker_to_code.keys())
    log.info("fetch_fundamentals_bulk: %d tickers refresh=%s", len(tickers), refresh)

    def _one(t: str) -> tuple[str, dict[str, Any]]:
        return t, fetch_fundamentals(t, ticker_to_code[t], refresh=refresh)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_one, t) for t in tickers]
        for fut in as_completed(futures):
            t, payload = fut.result()
            out[t] = payload
    return out


def fundamentals_frame(
    payloads: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Flatten per-ticker payloads into a DataFrame keyed by ticker."""
    rows = []
    for ticker, p in payloads.items():
        row: dict[str, Any] = {"ticker": ticker}
        for f in FIELDS:
            row[f] = p.get(f)
        row["sector"] = p.get("sector") or UNKNOWN_SECTOR
        row["industry"] = p.get("industry")
        rows.append(row)
    df = pd.DataFrame(rows).set_index("ticker")
    return df
