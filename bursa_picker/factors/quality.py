"""Quality factor: ROE + gross-profitability proxy.

Raw = 0.5 * ROE + 0.5 * GrossProfProxy
where GrossProfProxy ≈ profitMargins * (totalRevenue / assets_proxy)
and assets_proxy ≈ marketCap / priceToBook * (1 + debtToEquity/100 if >5 else debtToEquity).

yfinance returns `debtToEquity` as a *percentage* for Bursa tickers (e.g. 74
means 74%), so we scale when needed. Fallback to operatingMargins when
profitMargins is null.

Citations: Novy-Marx (2013); Gordon (2013); Fama-French (2015).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bursa_picker.factors.citations import (
    FAMA_FRENCH_2015,
    GORDON_2013_EM_QUALITY,
    NOVY_MARX_2013,
)

CITATIONS = (NOVY_MARX_2013, GORDON_2013_EM_QUALITY, FAMA_FRENCH_2015)


def _assets_proxy(mcap: pd.Series, p_b: pd.Series, d_e: pd.Series) -> pd.Series:
    de = d_e.copy()
    # yfinance sometimes returns % (e.g. 74) and sometimes ratio (e.g. 0.74)
    de = de.where(de.abs() <= 5, de / 100.0)
    de = de.fillna(0.0)
    book = mcap / p_b.replace(0, np.nan)
    return book * (1.0 + de.clip(lower=-0.9))


def compute(df: pd.DataFrame) -> pd.Series:
    """Given fundamentals frame, return raw Quality score per ticker."""
    roe = pd.to_numeric(df.get("returnOnEquity"), errors="coerce")
    margin = pd.to_numeric(df.get("profitMargins"), errors="coerce").fillna(
        pd.to_numeric(df.get("operatingMargins"), errors="coerce")
    )
    mcap = pd.to_numeric(df.get("marketCap"), errors="coerce")
    pb = pd.to_numeric(df.get("priceToBook"), errors="coerce")
    de = pd.to_numeric(df.get("debtToEquity"), errors="coerce")
    rev = pd.to_numeric(df.get("totalRevenue"), errors="coerce")

    assets = _assets_proxy(mcap, pb, de)
    gp_proxy = margin * (rev / assets.replace(0, np.nan))

    return 0.5 * roe.fillna(0.0) + 0.5 * gp_proxy.fillna(0.0).where(
        gp_proxy.notna() | roe.notna()
    )
