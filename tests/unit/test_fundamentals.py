from __future__ import annotations

import pytest

from bursa_picker.data import fundamentals as fm


@pytest.fixture(autouse=True)
def _sandbox_cache(tmp_path, monkeypatch):
    from bursa_picker import config as cfg

    cfg.get_settings.cache_clear()  # type: ignore[attr-defined]
    real = cfg.load_settings()
    real.paths.cache_dir = tmp_path
    monkeypatch.setattr(cfg, "get_settings", lambda: real)
    monkeypatch.setattr(fm, "get_settings", lambda: real)
    yield


class _FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    @property
    def info(self):
        return {
            "trailingPE": 12.5,
            "priceToBook": 1.3,
            "returnOnEquity": 0.11,
            "marketCap": 1_000_000_000,
            "sector": "Financial Services",
            "industry": "Banks—Regional",
            "dividendYield": 0.05,
            "numberOfAnalystOpinions": 10,
            "targetMeanPrice": 15.0,
            "recommendationMean": 2.1,
        }


def test_fundamentals_cache_hit_on_second_call(monkeypatch):
    monkeypatch.setattr(fm.yf, "Ticker", _FakeTicker)
    a = fm.fetch_fundamentals("T", "1234")
    assert a["trailingPE"] == 12.5
    assert a["sector"] == "Financial Services"

    calls = {"n": 0}

    class _Counting(_FakeTicker):
        @property
        def info(self):
            calls["n"] += 1
            return super().info

    monkeypatch.setattr(fm.yf, "Ticker", _Counting)
    b = fm.fetch_fundamentals("T", "1234")
    assert b == a
    assert calls["n"] == 0


def test_fundamentals_frame_shape(monkeypatch):
    monkeypatch.setattr(fm.yf, "Ticker", _FakeTicker)
    payloads = fm.fetch_fundamentals_bulk({"A": "1", "B": "2"})
    df = fm.fundamentals_frame(payloads)
    assert set(df.index) == {"A", "B"}
    assert "marketCap" in df.columns
    assert "sector" in df.columns


def test_fundamentals_frame_sector_fallback_unknown():
    df = fm.fundamentals_frame({"X": {"trailingPE": 1.0}})
    assert df.loc["X", "sector"] == "Unknown"
