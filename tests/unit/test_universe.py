from __future__ import annotations

import pandas as pd
import pytest

from bursa_picker.data import fundamentals as fm
from bursa_picker.data import prices as px
from bursa_picker.data import universe as un


@pytest.fixture(autouse=True)
def _sandbox(tmp_path, monkeypatch):
    from bursa_picker import config as cfg

    cfg.get_settings.cache_clear()  # type: ignore[attr-defined]
    real = cfg.load_settings()
    real.paths.cache_dir = tmp_path
    monkeypatch.setattr(cfg, "get_settings", lambda: real)
    monkeypatch.setattr(fm, "get_settings", lambda: real)
    monkeypatch.setattr(px, "get_settings", lambda: real)
    monkeypatch.setattr(un, "get_settings", lambda: real)
    yield


def test_load_ticker_map_dedups(tmp_path):
    p = tmp_path / "tm.txt"
    p.write_text("A : 1\nA : 1\nB : 2\nBAD LINE\nC : 3\n")
    m = un.load_ticker_map(p)
    assert m == {"A": "1", "B": "2", "C": "3"}


def test_flag_suspicious():
    m = {"GENM": "4715", "OTHER": "4715", "OK": "1234"}
    assert un.flag_suspicious(m) == ["OTHER"]


def _mk_info(mcap, sector, price=10.0):
    return {
        "marketCap": mcap,
        "regularMarketPrice": price,
        "previousClose": price,
        "sector": sector,
    }


def _mk_hist(price=10.0, volume=1_000_000, days=60):
    idx = pd.bdate_range(end=pd.Timestamp.today(), periods=days)
    df = pd.DataFrame(
        {
            "Open": [price] * days,
            "High": [price * 1.01] * days,
            "Low": [price * 0.99] * days,
            "Close": [price] * days,
            "Adj Close": [price] * days,
            "Volume": [volume] * days,
        },
        index=idx,
    )
    return df


def test_filter_universe_applies_all_gates(monkeypatch):
    infos = {
        "BIG": _mk_info(mcap=500_000_000, sector="Financial Services", price=10.0),
        "MID": _mk_info(mcap=150_000_000, sector="Industrials", price=2.0),
        "SMALL": _mk_info(mcap=50_000_000, sector="Industrials", price=1.0),  # under mcap
        "PENNY": _mk_info(mcap=200_000_000, sector="Industrials", price=0.10),  # under min_price
        "ILLIQ": _mk_info(mcap=200_000_000, sector="Industrials", price=2.0),  # low volume
        "EXCL": _mk_info(mcap=200_000_000, sector="BannedSector", price=2.0),  # excluded sector
    }
    volumes = {
        "BIG": 5_000_000,
        "MID": 1_000_000,
        "SMALL": 500_000,
        "PENNY": 5_000_000,
        "ILLIQ": 100,  # way under 500k MYR ADV
        "EXCL": 5_000_000,
    }

    class _FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        @property
        def info(self):
            code_to_ticker = {"1": "BIG", "2": "MID", "3": "SMALL", "4": "PENNY", "5": "ILLIQ", "6": "EXCL"}
            t = code_to_ticker[self.symbol.split(".")[0]]
            return infos[t]

        def history(self, **kwargs):
            code_to_ticker = {"1": "BIG", "2": "MID", "3": "SMALL", "4": "PENNY", "5": "ILLIQ", "6": "EXCL"}
            t = code_to_ticker[self.symbol.split(".")[0]]
            return _mk_hist(price=infos[t]["regularMarketPrice"], volume=volumes[t])

    monkeypatch.setattr(fm.yf, "Ticker", _FakeTicker)
    monkeypatch.setattr(px.yf, "Ticker", _FakeTicker)

    mapping = {"BIG": "1", "MID": "2", "SMALL": "3", "PENNY": "4", "ILLIQ": "5", "EXCL": "6"}

    df = un.filter_universe(
        mapping,
        min_mcap_myr=100_000_000,
        min_adv_myr=500_000,
        min_price_myr=0.20,
        exclude_sectors=["BannedSector"],
    )

    assert set(df.index) == {"BIG", "MID"}
    assert df.loc["BIG", "sector"] == "Financial Services"
    assert df.loc["MID", "mcap"] == 150_000_000
