"""Transaction cost model: basis-point roundtrip + per-trade floor."""

from __future__ import annotations


def cost_fraction(turnover: float, costs_bps: float) -> float:
    """Return cost as a fraction of portfolio equity at a rebalance.

    ``turnover`` is the one-sided turnover fraction (e.g. 0.25 means 25%
    of the portfolio value changed hands). ``costs_bps`` is the all-in
    round-trip cost in basis points applied to full two-sided turnover.
    """
    return float(turnover) * float(costs_bps) / 10_000.0


def clamp_fee_floor(equity_myr: float, top_n: int, min_fee_myr: float) -> float:
    """Lower-bound dollar fee: ``min_fee_myr`` per trade at each rebalance.

    For small portfolios the broker's min-commission floor dominates.
    Returns the fee as a fraction of equity.
    """
    if equity_myr <= 0 or top_n <= 0 or min_fee_myr <= 0:
        return 0.0
    return (top_n * 2 * min_fee_myr) / equity_myr  # buy + sell legs
