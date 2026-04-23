# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`bursa-picker` — a research-backed, explainable factor-based stock picker for
Bursa Malaysia. Six literature-weighted factors (quality, value, dividend,
momentum, size, analyst sentiment) feed a cross-sectional ranker with
plain-English per-pick narratives and citations. A price-only walk-forward
backtest validates the strategy vs `^KLSE`.

## Commands

```bash
pip install -e .                   # installs the `bursa-picker` CLI
pytest                             # full test suite (unit + integration)
pytest tests/unit/test_factors.py  # single file
pytest -k quality                  # by substring
bursa-picker universe              # filtered tradable universe
bursa-picker rank --top 20         # top-N picks
bursa-picker rank --top 10 --narrative   # picks + plain-English paragraphs
bursa-picker rank --output json    # JSON for tooling
bursa-picker backtest --start 2014-01-01 --end today --top 20
bursa-picker --refresh             # force cache bust
```

No separate lint/build step — deps are managed via `pyproject.toml` and tests
are the main gate.

## Architecture

```
bursa_picker/
├── config.py              # pydantic-settings loader for config.toml
├── constants.py           # BENCHMARK, FACTOR_NAMES, UNKNOWN_SECTOR
├── logging_setup.py       # rotating file + console, in-proc metrics
├── data/
│   ├── ratelimit.py       # token-bucket @throttle + tenacity @with_retry
│   ├── prices.py          # SQLite-cached OHLCV fetcher + bulk parallel
│   ├── fundamentals.py    # SQLite-cached .info snapshots (7d TTL)
│   ├── universe.py        # load+dedup ticker_map, liquidity filter
│   └── scraper.py         # LEGACY i3investor/malaysiastock helpers (off critical path)
├── factors/
│   ├── base.py            # winsorize, zscore, sector_neutralize(min_sector_size=3)
│   ├── citations.py       # Citation dataclass + committed paper metadata
│   ├── quality.py, value.py, dividend.py, momentum.py, size.py, sentiment.py
│   └── composite.py       # winsorize → z → sector-neutralize → weighted sum
├── portfolio/
│   └── construction.py    # rank_universe(): universe → funds → prices → score → top-N
├── backtest/
│   ├── engine.py          # monthly walk-forward, price-only factors
│   ├── costs.py           # cost_fraction(turnover, bps) + per-trade MYR floor
│   ├── metrics.py         # CAGR, Sharpe, MaxDD, HitRate
│   └── runner.py          # glues engine to the real data layer
├── explain/
│   └── narrative.py       # template-assembled per-pick paragraphs + citations footer
└── cli/
    ├── main.py            # Typer root: `bursa-picker`
    ├── universe.py        # `bursa-picker universe`
    ├── rank.py            # `bursa-picker rank [--narrative] [--output json]`
    └── backtest.py        # `bursa-picker backtest`
```

Data flow for `rank`:
1. `universe.load_ticker_map()` → deduped `{TICKER: STOCK_CODE}`.
2. `universe.filter_universe()` applies min_mcap / min_adv / min_price gates
   using cached fundamentals + cached 30-day ADV from prices.
3. `fetch_fundamentals_bulk()` (parallel, cached) + `fetch_prices_bulk()`
   (parallel, cached, ~14mo for 12-1 momentum).
4. `factors.composite.score()` runs each factor: raw → winsorize → z-score →
   sector-neutralize (min_sector_size=3, else global fallback) → weighted.
5. `portfolio.construction.rank_universe()` returns `PicksResult(picks,
   contributions, fundamentals, universe_stats, warnings)`.
6. `cli/rank.py` renders rich table + optional narrative paragraphs via
   `explain.narrative.render_pick()` + citations footer.

Invariant: contributions DataFrame excluding `_n_missing` column, row-summed,
equals the score Series (unit-tested).

## Factor design (committed, not tuned)

| Factor              | Weight | Raw formula                                                                 | Citation              |
|---------------------|-------:|-----------------------------------------------------------------------------|-----------------------|
| quality             | 0.35   | 0.5·ROE + 0.5·(profitMargins · totalRevenue / assets_proxy)                 | Novy-Marx (2013)      |
| value               | 0.30   | mean of z(1/P/B), z(1/P/E), z(1/P/S)                                        | Fama-French (1992)    |
| dividend            | 0.10   | dividendYield · min(1, (1−payoutRatio)+0.5)                                 | Arnott-Asness (2003)  |
| momentum            | 0.10   | close(t−21)/close(t−252) − 1, sector-neutralized                            | Jegadeesh-Titman (1993) |
| size                | 0.05   | −log(marketCap), winsorized at 20th pct                                     | Fama-French (1992)    |
| sentiment           | 0.10   | 0.5·z(−recMean) + 0.5·z(upside), only when numberOfAnalystOpinions ≥ 3      | Womack (1996)         |

Notes:
- Momentum is kept *soft* — Bursa Carhart 4F study (2011-2021) found it not
  significant on size-sorted portfolios. The narrative always says so.
- Low-volatility / BAB is deliberately **not** a factor: Sehgal et al. (2022)
  found it not significant in Indonesia/Korea/Japan-like EMs. Don't add it.
- Universe liquidity filter (min RM 100m mcap, min RM 500k ADV, min RM 0.20
  price) runs *before* the size factor so size-tilt doesn't load onto shell
  companies.

## Gotchas for future agents

- **Always** pass `-c user.name=Dhiren -c user.email=mandhirensingh@gmail.com`
  on `git commit` in this session until a fresh Claude Code session picks up
  the global env vars from `~/.claude/settings.json`. The user confirmed this
  in conversation after an earlier author-attribution regression.
- Tests sandbox `config.get_settings()` via monkeypatch — when writing new
  modules that read settings, always call `get_settings()` lazily (inside
  functions), never bind the result at import time, or tests cannot override
  the cache directory.
- yfinance rate-limits aggressively; rely on `data.ratelimit.throttle` +
  `with_retry` decorators on every outbound call, never call `yf.Ticker`
  directly in new code.
- `.info['dividendYield']` switched between fraction and percent across
  yfinance versions; `factors/dividend.py` coerces values >1 by /100.
- `debtToEquity` from yfinance is in *percent* for KLSE (e.g. 74 means 74%),
  not a ratio; `factors/quality.py` divides by 100 when the raw value
  exceeds 5.
- Historical financial statements (`Ticker.financials`, `.balance_sheet`,
  `.cashflow`, and their quarterly variants) are **empty** for `<code>.KL`
  tickers on free yfinance. Do not assume they'll ever populate. The
  backtest uses price-only factors for this reason.
- `data/scraper.py` is the old i3investor/malaysiastock.biz scraper, kept
  but OFF the critical path. It has known regex-fallback bugs (returns
  "4715" for GENM when parsing fails) and `malaysiastock.biz` 503s
  intermittently. Only used as a manual `ticker_map.txt` refresh tool.
- Integration test `test_rank_e2e.py` uses a fake `yf.Ticker`; never allow
  tests to touch the real network. If you add a new fetch path, sandbox it
  the same way (see `tests/integration/conftest`-style fixtures).
- The `scripts/` directory contains deprecation shims for the old flat-file
  entry points (`main.py`, `run_screener.py`). New entry points go through
  Typer in `bursa_picker/cli/`.
