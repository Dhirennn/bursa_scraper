from __future__ import annotations

import pandas as pd

from bursa_picker.portfolio.sector_caps import apply_sector_cap


def test_cap_limits_per_sector():
    ranked = pd.Series(
        {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1, "F": 0}
    ).sort_values(ascending=False)
    sectors = pd.Series({"A": "X", "B": "X", "C": "X", "D": "Y", "E": "Z", "F": "W"})
    # Top 3 picks with max 1 per sector when 30% of 3 = 1 (floor behaviour)
    picks = apply_sector_cap(ranked, sectors, top_n=3, max_share=0.34)
    # X caps at 1 → A. Then D (Y), E (Z) fill the remaining slots.
    assert picks[0] == "A"
    assert len(picks) == 3


def test_cap_soft_fills_when_not_enough_sectors():
    ranked = pd.Series({"A": 5, "B": 4, "C": 3, "D": 2}).sort_values(ascending=False)
    sectors = pd.Series({"A": "X", "B": "X", "C": "X", "D": "X"})
    # Everyone in sector X; cap 0.30 with top_n=4 should still return 4 picks
    picks = apply_sector_cap(ranked, sectors, top_n=4, max_share=0.30)
    assert set(picks) == {"A", "B", "C", "D"}
    assert len(picks) == 4
