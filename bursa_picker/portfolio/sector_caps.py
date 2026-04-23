"""Soft sector-concentration cap for the top-N picks.

If any sector exceeds ``max_share`` of the portfolio, drop the lowest-scoring
names in that sector and promote the next best from other sectors until
the cap holds. Greedy and deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


def apply_sector_cap(
    ranked_scores: pd.Series,
    sectors: pd.Series,
    *,
    top_n: int,
    max_share: float = 0.30,
) -> list[str]:
    """Return a list of ticker IDs honouring the sector cap.

    ``ranked_scores`` must be sorted descending. ``sectors`` is a Series
    mapping every ticker in the universe to its sector label.
    """
    if top_n <= 0:
        return []

    max_per_sector = max(1, int(top_n * max_share + 1e-9))
    picks: list[str] = []
    per_sector: dict[str, int] = {}
    for ticker in ranked_scores.index:
        if len(picks) >= top_n:
            break
        s = sectors.get(ticker, "Unknown")
        if per_sector.get(s, 0) >= max_per_sector:
            continue
        picks.append(ticker)
        per_sector[s] = per_sector.get(s, 0) + 1

    # If we couldn't fill top_n because too many stocks got skipped, fill
    # the gap with next-best regardless of sector (the cap is *soft*).
    if len(picks) < top_n:
        remaining = [t for t in ranked_scores.index if t not in picks]
        picks.extend(remaining[: top_n - len(picks)])

    return picks
