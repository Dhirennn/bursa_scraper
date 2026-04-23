from __future__ import annotations

BENCHMARK = "^KLSE"

FACTOR_NAMES = ("quality", "value", "dividend", "momentum", "size", "sentiment")

UNKNOWN_SECTOR = "Unknown"

# yfinance returns MYR prices for .KL tickers.
CURRENCY = "MYR"

# Trading-day conventions
DAYS_PER_YEAR = 252
MONTH_LOOKBACK_DAYS = 21
YEAR_LOOKBACK_DAYS = 252
