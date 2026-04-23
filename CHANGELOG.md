# Changelog

## 0.1.0 — 2026-04-23

Initial production-grade release. Replaces the legacy EMA18/50 crossover
screener with a research-backed factor model.

### Added

- `bursa-picker` CLI with `rank`, `backtest`, `universe` subcommands (Typer).
- Six literature-weighted factors (quality 0.35 / value 0.30 / dividend 0.10 /
  momentum 0.10 / size 0.05 / sentiment 0.10) with citations:
  Novy-Marx (2013), Gordon (2013), Fama-French (1992, 2015), Asness-Moskowitz-
  Pedersen (2013), Jegadeesh-Titman (1993), Arnott-Asness (2003), Womack (1996),
  Hou-Xue-Zhang (2020).
- Cross-sectional ranker: winsorize → z-score → sector-neutralize (with
  min_sector_size fallback to global demean) → weighted composite.
- SQLite caches for prices (18h TTL) and `.info` fundamentals (7d TTL) with
  polite token-bucket throttle + tenacity retry-with-backoff.
- Universe loader: dedupes `ticker_map.txt`, flags suspicious "4715" fallbacks,
  applies liquidity + min-mcap + min-price gates.
- Monthly walk-forward backtest engine (price-only factors) vs `^KLSE`
  benchmark with realistic 50bps roundtrip cost and per-trade MYR floor.
  Metrics: CAGR, Sharpe, MaxDD, HitRate, Turnover, ExcessCAGR.
- Explainability module: per-pick plain-English paragraph with factor-by-
  factor contribution narrative and deduplicated citations footer.
- Soft sector cap (max share per sector) and `--factors` subset toggle.
- 45 tests (unit + integration) — determinism, row-sum invariants, cache
  hit/miss, CLI round-trip against a fake yfinance fixture.

### Changed

- Package layout: `src/` flat scripts → `bursa_picker/` importable package
  with `data/`, `factors/`, `portfolio/`, `backtest/`, `explain/`, `cli/`.
- `ticker_map.txt` is now read once and deduped in memory; legacy duplicate
  entries are tolerated.

### Deprecated

- `scripts/main.py`, `scripts/run_screener.py` — kept as shims that emit
  `DeprecationWarning` and forward to `bursa-picker rank`.

### Removed

- `src/main.py`, `src/run_screener.py`, `src/exponential_moving_average.py`,
  `src/rsi.py`, `src/ticker_data_retrieval.py`, `src/ticker_map.txt`,
  `src/.env` — replaced by the new package.

### Known limitations

- yfinance historical financial statements are empty for KLSE tickers, so
  fundamentals cannot be backtested point-in-time. The live ranker's
  fundamentals overlay is literature-supported but not Bursa-walk-forward-
  validated.
- Mild survivorship bias in the backtest — no delisting feed.
- `malaysiastock.biz` / `i3investor` scrapers (`bursa_picker/data/scraper.py`)
  are fragile and off the critical path; used only for manual
  `ticker_map.txt` refresh.
