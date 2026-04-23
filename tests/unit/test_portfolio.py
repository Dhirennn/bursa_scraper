from __future__ import annotations

import pandas as pd
import pytest

from bursa_picker.data import fundamentals as fm
from bursa_picker.data import prices as px
from bursa_picker.data import universe as un
from bursa_picker.portfolio import construction


@pytest.fixture(autouse=True)
def _sandbox(tmp_path, monkeypatch):
    from bursa_picker import config as cfg

    cfg.get_settings.cache_clear()  # type: ignore[attr-defined]
    real = cfg.load_settings()
    real.paths.cache_dir = tmp_path
    real.paths.ticker_map = tmp_path / "ticker_map.txt"
    monkeypatch.setattr(cfg, "get_settings", lambda: real)
    monkeypatch.setattr(fm, "get_settings", lambda: real)
    monkeypatch.setattr(px, "get_settings", lambda: real)
    monkeypatch.setattr(un, "get_settings", lambda: real)
    monkeypatch.setattr(construction, "get_settings", lambda: real)
    yield


def _mk_hist(price=10.0, volume=1_000_000, days=500):
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    vals = [price * (1 + 0.001 * i) for i in range(days)]
    return pd.DataFrame(
        {
            "Open": vals,
            "High": [v * 1.01 for v in vals],
            "Low": [v * 0.99 for v in vals],
            "Close": vals,
            "Adj Close": vals,
            "Volume": [volume] * days,
        },
        index=idx,
    )


def _info(**over):
    base = {
        "marketCap": 1_000_000_000,
        "priceToBook": 1.5,
        "trailingPE": 12.0,
        "priceToSalesTrailing12Months": 1.2,
        "returnOnEquity": 0.12,
        "profitMargins": 0.15,
        "operatingMargins": 0.18,
        "debtToEquity": 50.0,
        "totalRevenue": 5e8,
        "dividendYield": 0.04,
        "payoutRatio": 0.5,
        "numberOfAnalystOpinions": 5,
        "recommendationMean": 2.0,
        "targetMeanPrice": 11.0,
        "regularMarketPrice": 10.0,
        "previousClose": 10.0,
        "sector": "Financial Services",
    }
    base.update(over)
    return base


def test_rank_universe_end_to_end(monkeypatch, tmp_path):
    # 4 tickers. A is the "best": high quality, cheap, moderate size
    infos = {
        "A": _info(returnOnEquity=0.25, priceToBook=0.8, trailingPE=6.0, dividendYield=0.06),
        "B": _info(returnOnEquity=0.05, priceToBook=3.0, trailingPE=40.0, dividendYield=0.01),
        "C": _info(sector="Industrials", returnOnEquity=0.15, priceToBook=1.2, trailingPE=10.0),
        "D": _info(sector="Industrials", returnOnEquity=0.02, priceToBook=4.0, trailingPE=50.0),
    }
    # ticker_map
    (tmp_path / "ticker_map.txt").write_text(
        "\n".join(f"{t} : {i+1}" for i, t in enumerate(infos)) + "\n"
    )

    class _FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol
            code_to_t = {str(i + 1): t for i, t in enumerate(infos)}
            self.t = code_to_t[self.symbol.split(".")[0]]

        @property
        def info(self):
            return infos[self.t]

        def history(self, **kwargs):
            return _mk_hist()

    monkeypatch.setattr(fm.yf, "Ticker", _FakeTicker)
    monkeypatch.setattr(px.yf, "Ticker", _FakeTicker)

    res = construction.rank_universe(top_n=3, refresh=True)

    assert res.universe_stats["universe_size"] >= 3
    assert len(res.picks) == 3
    # A should rank high (top 2)
    assert "A" in res.picks.index[:2]
    # Contribution row-sum equals score (subset excluding _n_missing)
    for t in res.picks.index:
        contrib_sum = res.contributions.drop(columns=["_n_missing"]).loc[t].sum()
        assert abs(contrib_sum - res.picks.loc[t, "score"]) < 1e-9
