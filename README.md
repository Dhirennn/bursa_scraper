# bursa-picker

A research-backed, explainable factor-based stock picker for Bursa Malaysia equities.

**This is not investment advice.** The tool produces a systematic ranking
based on publicly available data and academic factor-investing literature. Every
pick comes with a factor-by-factor contribution breakdown and a plain-English
narrative citing the underlying papers. No forecast language is used.

## Features

- Six literature-weighted factors: quality, value, dividend, momentum,
  size, analyst sentiment.
- Cross-sectional winsorization → z-score → sector-neutralization → weighted
  composite (row-sum invariant: sum of per-factor contributions == score).
- Honest backtest: price-only factors over 10+ years vs FTSE-KLCI, with
  50bps roundtrip costs + per-trade MYR floor. Fundamentals point-in-time
  are not available for KLSE on yfinance, so the fundamentals overlay of
  the live ranker is literature-supported but not Bursa-walk-forward-validated.
- SQLite caches for prices and `.info` snapshots. Polite token-bucket throttle
  + tenacity retry. First full universe refresh: 20-40 min; subsequent runs
  are seconds.

## Install

```bash
pip install -e .
```

Requires Python 3.10+.

## Usage

```bash
# Filtered tradable universe (liquidity + min market cap + min price)
bursa-picker universe --min-mcap 100m --min-adv 500k

# Top-20 picks today with per-factor contributions
bursa-picker rank --top 20

# Plain-English narrative paragraph per pick, with citations footer
bursa-picker rank --top 10 --narrative

# JSON output for downstream tooling
bursa-picker rank --top 20 --output json > picks.json

# Walk-forward backtest vs ^KLSE (price-only factors)
bursa-picker backtest --start 2014-01-01 --end today --top 20 --costs 50

# Force a cache bust (skip TTL, re-download)
bursa-picker rank --refresh
```

## Factors and academic evidence

| Factor              | Weight | Key citation                                              |
|---------------------|-------:|-----------------------------------------------------------|
| Quality/Profit.     | 0.35   | Novy-Marx (2013); Gordon (2013) EM profitability          |
| Value               | 0.30   | Fama-French (1992); Asness-Moskowitz-Pedersen (2013)      |
| Dividend yield      | 0.10   | Arnott-Asness (2003)                                      |
| Momentum (12-1)     | 0.10   | Jegadeesh-Titman (1993); kept soft — weak Bursa evidence  |
| Size tilt           | 0.05   | Fama-French (1992); universe filter first                 |
| Analyst sentiment   | 0.10   | Womack (1996); applied only when ≥3 analysts              |

Weights committed, not tuned to past performance. Hou-Xue-Zhang (2020) showed
64-85% of 447 published anomalies are insignificant at t>3; this is a 6-factor
design, not a factor zoo.

Skipped by design (no EM-like-Malaysia evidence): low-volatility /
Betting-Against-Beta (Sehgal et al. 2022 finds it not significant in
Indonesia / Korea / Japan).

## Configuration

All weights, paths, TTLs, and backtest parameters live in `config.toml` at
the project root. Override per run with CLI flags; programmatic callers can
load `bursa_picker.config.load_settings()` directly.

## Data caveats

- `yfinance` historical financial statements return empty for KLSE tickers,
  so fundamentals cannot be backtested point-in-time. The live ranker uses
  today's `.info` snapshot (7-day cache TTL).
- `data/ticker_map.txt` ships with some duplicates and a handful of "4715"
  regex fallbacks from the legacy scraper. `load_ticker_map` dedupes
  in-memory; `flag_suspicious` reports 4715-mapped non-GENM tickers.
- Mild survivorship bias in the backtest: no delisting feed. Documented.

## License

MIT.
