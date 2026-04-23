"""Top-N portfolio construction from composite scores."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from bursa_picker.config import get_settings
from bursa_picker.data.fundamentals import fetch_fundamentals_bulk, fundamentals_frame
from bursa_picker.data.prices import fetch_prices_bulk
from bursa_picker.data.universe import load_ticker_map, filter_universe
from bursa_picker.factors import composite, momentum
from bursa_picker.logging_setup import get_logger

log = get_logger(__name__)


@dataclass
class PicksResult:
    as_of: pd.Timestamp
    picks: pd.DataFrame
    contributions: pd.DataFrame
    fundamentals: pd.DataFrame  # full fundamentals frame for explain/ module
    universe_stats: dict
    warnings: list[str] = field(default_factory=list)


def rank_universe(
    *,
    as_of: Optional[str] = None,
    top_n: int = 20,
    weights: Optional[dict[str, float]] = None,
    refresh: bool = False,
    sector_concentration_warn: float = 0.30,
    min_universe_warn: int = 100,
    max_workers: int = 8,
) -> PicksResult:
    """End-to-end: universe -> fundamentals -> prices (for momentum) -> composite -> top-N.

    Returns a PicksResult with picks (top-N DataFrame), per-factor
    contributions for those picks, universe statistics, and non-fatal warnings.
    """
    settings = get_settings()
    as_of_ts = (
        pd.Timestamp(as_of) if as_of not in (None, "today") else pd.Timestamp.today().normalize()
    )

    # 1. Universe filter
    mapping = load_ticker_map()
    uni = filter_universe(mapping, as_of=as_of_ts.strftime("%Y-%m-%d"), refresh=refresh,
                         max_workers=max_workers)
    log.info("universe: %d tickers after filter", len(uni))

    warnings: list[str] = []
    if len(uni) < min_universe_warn:
        warnings.append(f"universe_small: {len(uni)} < {min_universe_warn}")

    # 2. Fundamentals for the filtered universe (cached from step 1)
    sub_map = {t: mapping[t] for t in uni.index if t in mapping}
    payloads = fetch_fundamentals_bulk(sub_map, refresh=False, max_workers=max_workers)
    fund = fundamentals_frame(payloads).reindex(uni.index)
    fund["sector"] = uni["sector"]  # keep universe's cleaned sectors
    fund["regularMarketPrice"] = uni["last_close"]

    # 3. Prices (for momentum) over ~14 months ending as_of
    start = (as_of_ts - pd.Timedelta(days=420)).strftime("%Y-%m-%d")
    end = as_of_ts.strftime("%Y-%m-%d")
    prices = fetch_prices_bulk(sub_map, start=start, end=end, refresh=refresh,
                               max_workers=max_workers)
    mom_raw = momentum.compute_from_prices(prices, as_of_ts)

    # 4. Composite
    scores, contribs = composite.score(fund, momentum_raw=mom_raw, weights=weights)

    ranked = scores.sort_values(ascending=False).dropna()
    picks_idx = ranked.head(top_n).index
    picks = uni.loc[picks_idx].copy()
    picks["score"] = ranked.loc[picks_idx]
    picks["rank"] = range(1, len(picks_idx) + 1)

    # 5. Sector concentration warning
    sector_share = (picks["sector"].value_counts() / len(picks)).to_dict()
    over = {s: v for s, v in sector_share.items() if v > sector_concentration_warn}
    if over:
        warnings.append(
            "sector_concentration: " + ", ".join(f"{s}={v:.0%}" for s, v in over.items())
        )

    return PicksResult(
        as_of=as_of_ts,
        picks=picks,
        contributions=contribs.loc[picks_idx],
        fundamentals=fund.loc[picks_idx],
        universe_stats={
            "universe_size": int(len(uni)),
            "scored": int(scores.dropna().shape[0]),
            "top_n": int(len(picks_idx)),
        },
        warnings=warnings,
    )
