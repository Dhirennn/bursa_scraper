# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BURSA Malaysia stock screener. Scrapes the full Bursa ticker list, fetches price history via Yahoo Finance, and flags stocks whose EMA18 just crossed above EMA50 (a bullish crossover signal).

## Commands

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the screener (must be run from the `src/` directory — see "Working directory" below):
```bash
cd src
python main.py
```

Individual modules have `__main__` blocks for ad-hoc testing, also run from `src/`:
```bash
cd src
python scraper.py                     # Test ticker-code + analyst-projection scraping for PETGAS
python ticker_data_retrieval.py       # Fetch GENM price history
python exponential_moving_average.py  # Compute EMA columns for GENM
python rsi.py                         # Compute RSI for PETGAS
```

There are no tests, linter config, or build system in this repo.

## Architecture

Pipeline in `src/main.py`:

1. `scraper.get_stock_list()` scrapes the ticker list from `malaysiastock.biz/Stock-Screener.aspx`.
2. `ThreadPoolExecutor.map(process_ema, stock_list)` fans out one worker per ticker.
3. For each ticker, `exponential_moving_average.process_ema` calls `ticker_data_retrieval.get_stock_price`, which:
   - Loads `../data/ticker_map.txt` into a `{TICKER: CODE}` dict.
   - Appends `.KL` to the code and fetches OHLC via `yfinance.Ticker(...).history(start, end)`.
4. EMA18/50/100/200 are added as DataFrame columns; `check_EMA_crossing` returns `True` when `EMA18 > EMA50` today **and** `EMA18 < EMA50` yesterday **and** the series has ≥51 rows.
5. Surviving tickers are printed with their stock codes.

`scraper.py` also exposes unused-by-main helpers (`get_ticker_code`, `update_tickers_number`, `get_price_target`, `get_analyst_projections`) that scrape `i3investor.com`. `rsi.py` implements RSI but is not wired into the main pipeline.

## Repository Conventions & Gotchas

- **Working directory.** All file paths are hardcoded relative (`"../data/ticker_map.txt"`, `"data"`). Scripts assume CWD is `src/`. Running `python src/main.py` from the repo root will fail.
- **Mixed import style in `main.py`.** `main.py` mixes flat imports (`from scraper import ...`) with a package-style one (`from src.ticker_data_retrieval import ...`). Both happen to resolve when invoked from `src/` because `src/` is on `sys.path` as the script dir and the repo root is the parent, but this is fragile — prefer flat imports (`from ticker_data_retrieval import ...`) for consistency.
- **Duplicated `ticker_map.txt`.** Copies exist at both `data/ticker_map.txt` and `src/ticker_map.txt`. The code reads `../data/ticker_map.txt`; the `src/` copy is stale/unused. Avoid editing the `src/` copy.
- **`update_tickers_number` appends.** It opens `../data/ticker_map.txt` in `"a"` mode and never dedupes; the existing file already contains duplicate lines (e.g. `3A : 0012` twice). Truncate first if regenerating.
- **Regex fallback code `4715`.** When `get_ticker_code` can't parse the stock code from i3investor HTML, it silently returns `4715` (Genting Malaysia's code). Any ticker mapped to `4715` in `ticker_map.txt` other than `GENM` itself is almost certainly a scrape failure that needs manual fixing — see the README note.
- **Date range is hardcoded.** `process_ema` fetches `2018-01-01` → `2023-09-29`. Update both endpoints when refreshing; there is no config layer.
- **Silent exception swallowing.** `process_ema` returns `None` on any exception (network, yfinance, parsing). When debugging why a stock is missing from the output, add logging inside the `except` before assuming it failed the EMA filter.
- **Empty `src/.env`.** Present but unused; no env vars are read anywhere.
