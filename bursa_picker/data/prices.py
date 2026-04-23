"""SQLite-cached price fetcher for Bursa tickers (+ KLCI benchmark)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd
import yfinance as yf

from bursa_picker.config import get_settings
from bursa_picker.data.ratelimit import throttle, with_retry
from bursa_picker.logging_setup import get_logger, incr

log = get_logger(__name__)

_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


def _yf_symbol(ticker: str, stock_code: str | None = None) -> str:
    """Map an internal ticker to its yfinance symbol.

    For KLSE equities, the yfinance symbol is ``<stock_code>.KL``. Benchmarks
    pass through as-is (e.g. ``^KLSE``).
    """
    if ticker.startswith("^"):
        return ticker
    if stock_code is None:
        raise ValueError(f"stock_code required for equity ticker {ticker!r}")
    return f"{stock_code}.KL"


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
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT NOT NULL,
            date   TEXT NOT NULL,
            open   REAL, high REAL, low REAL, close REAL, adj_close REAL, volume REAL,
            PRIMARY KEY(ticker, date)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS price_meta (
            ticker TEXT PRIMARY KEY,
            last_refresh_utc TEXT NOT NULL
        )
        """
    )


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ttl_ok(last_refresh_utc: str, ttl_hours: float) -> bool:
    last = datetime.fromisoformat(last_refresh_utc)
    return (_now_utc() - last).total_seconds() < ttl_hours * 3600


@throttle("yfinance", rps=2.0)
@with_retry(max_attempts=4, backoff_base=1.5)
def _download(symbol: str, start: str, end: str) -> pd.DataFrame:
    df = yf.Ticker(symbol).history(
        start=start,
        end=end,
        auto_adjust=False,
        actions=False,
        raise_errors=False,
    )
    return df


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", *_COLUMNS])
    df = df.copy()
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    if "adj_close" not in df.columns and "close" in df.columns:
        df["adj_close"] = df["close"]
    df.index.name = "date"
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    keep = ["date", *_COLUMNS]
    for col in keep:
        if col not in df.columns:
            df[col] = pd.NA
    return df[keep]


def _upsert(c: sqlite3.Connection, ticker: str, df: pd.DataFrame) -> None:
    if df.empty:
        return
    rows = [
        (ticker, r.date, r.open, r.high, r.low, r.close, r.adj_close, r.volume)
        for r in df.itertuples(index=False)
    ]
    c.executemany(
        "INSERT OR REPLACE INTO prices(ticker,date,open,high,low,close,adj_close,volume)"
        " VALUES (?,?,?,?,?,?,?,?)",
        rows,
    )
    c.execute(
        "INSERT OR REPLACE INTO price_meta(ticker,last_refresh_utc) VALUES (?,?)",
        (ticker, _now_utc().isoformat()),
    )


def _read_range(
    c: sqlite3.Connection, ticker: str, start: str, end: str
) -> pd.DataFrame:
    q = (
        "SELECT date, open, high, low, close, adj_close, volume "
        "FROM prices WHERE ticker = ? AND date >= ? AND date <= ? ORDER BY date"
    )
    df = pd.read_sql_query(q, c, params=(ticker, start, end))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def _meta(c: sqlite3.Connection, ticker: str) -> str | None:
    cur = c.execute(
        "SELECT last_refresh_utc FROM price_meta WHERE ticker = ?", (ticker,)
    )
    row = cur.fetchone()
    return row[0] if row else None


def _db_path() -> Path:
    return get_settings().paths.cache_dir / "prices.sqlite"


def fetch_prices(
    ticker: str,
    start: str,
    end: str,
    stock_code: str | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Cache-first OHLCV fetch.

    Returns a DataFrame indexed by ``date`` (Timestamp) with columns
    ``[open, high, low, close, adj_close, volume]``.
    """
    settings = get_settings()
    ttl_hours = settings.cache.prices_ttl_hours
    symbol = _yf_symbol(ticker, stock_code)
    with _conn(_db_path()) as c:
        _init_schema(c)
        last = _meta(c, ticker)
        if refresh or last is None or not _ttl_ok(last, ttl_hours):
            try:
                raw = _download(symbol, start, end)
                norm = _normalize(raw)
                _upsert(c, ticker, norm)
                incr("cache_misses")
            except Exception as e:
                log.warning("price fetch failed for %s: %s", symbol, e)
        else:
            incr("cache_hits")

        df = _read_range(c, ticker, start, end)
    return df.set_index("date") if not df.empty else df


def fetch_prices_bulk(
    ticker_to_code: dict[str, str | None],
    start: str,
    end: str,
    refresh: bool = False,
    max_workers: int = 8,
) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    tickers = list(ticker_to_code.keys())
    log.info(
        "fetch_prices_bulk: %d tickers, start=%s end=%s refresh=%s",
        len(tickers),
        start,
        end,
        refresh,
    )

    def _one(t: str) -> tuple[str, pd.DataFrame]:
        code = ticker_to_code[t]
        return t, fetch_prices(t, start, end, stock_code=code, refresh=refresh)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_one, t) for t in tickers]
        for fut in as_completed(futures):
            t, df = fut.result()
            out[t] = df
    return out


def trailing_adv(
    ticker: str, as_of: str, window_days: int = 30, stock_code: str | None = None
) -> float | None:
    """Average daily value traded over trailing ``window_days`` ending at ``as_of``."""
    as_of_dt = pd.Timestamp(as_of)
    start = (as_of_dt - pd.Timedelta(days=window_days * 2)).strftime("%Y-%m-%d")
    df = fetch_prices(ticker, start, as_of_dt.strftime("%Y-%m-%d"), stock_code=stock_code)
    if df.empty:
        return None
    df = df.tail(window_days)
    if df.empty:
        return None
    values = (df["close"].astype(float) * df["volume"].astype(float)).dropna()
    return float(values.mean()) if len(values) else None
