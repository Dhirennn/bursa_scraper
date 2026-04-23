from __future__ import annotations

from unittest.mock import patch
import pandas as pd
import pytest

from bursa_picker.data import prices as prices_mod


@pytest.fixture(autouse=True)
def _sandbox_cache(tmp_path, monkeypatch):
    from bursa_picker import config as cfg

    cfg.get_settings.cache_clear()  # type: ignore[attr-defined]
    # Use a tmp cache dir so tests don't pollute the real cache.
    real = cfg.load_settings()
    real.paths.cache_dir = tmp_path
    monkeypatch.setattr(cfg, "get_settings", lambda: real)
    monkeypatch.setattr(prices_mod, "get_settings", lambda: real)
    yield


def _fake_history(dates, closes):
    idx = pd.to_datetime(dates)
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [c * 1.01 for c in closes],
            "Low": [c * 0.99 for c in closes],
            "Close": closes,
            "Adj Close": closes,
            "Volume": [1_000_000] * len(closes),
        },
        index=idx,
    )
    return df


class _FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, **kwargs):
        return _fake_history(
            ["2024-01-02", "2024-01-03", "2024-01-04"],
            [10.0, 10.5, 10.2],
        )


def test_fetch_prices_cache_miss_then_hit(monkeypatch):
    monkeypatch.setattr(prices_mod.yf, "Ticker", _FakeTicker)
    df1 = prices_mod.fetch_prices("T", "2024-01-01", "2024-01-10", stock_code="1234")
    assert not df1.empty
    assert list(df1.columns) == ["open", "high", "low", "close", "adj_close", "volume"]

    calls = {"n": 0}

    class _CountingTicker(_FakeTicker):
        def history(self, **kwargs):
            calls["n"] += 1
            return super().history(**kwargs)

    monkeypatch.setattr(prices_mod.yf, "Ticker", _CountingTicker)
    df2 = prices_mod.fetch_prices("T", "2024-01-01", "2024-01-10", stock_code="1234")
    assert df2.equals(df1)
    assert calls["n"] == 0, "TTL-fresh cache should not re-download"


def test_fetch_prices_refresh_forces_redownload(monkeypatch):
    monkeypatch.setattr(prices_mod.yf, "Ticker", _FakeTicker)
    prices_mod.fetch_prices("T", "2024-01-01", "2024-01-10", stock_code="1234")

    hit = {"n": 0}

    class _CountingTicker(_FakeTicker):
        def history(self, **kwargs):
            hit["n"] += 1
            return super().history(**kwargs)

    monkeypatch.setattr(prices_mod.yf, "Ticker", _CountingTicker)
    prices_mod.fetch_prices(
        "T", "2024-01-01", "2024-01-10", stock_code="1234", refresh=True
    )
    assert hit["n"] == 1


def test_yf_symbol_benchmark_passthrough():
    assert prices_mod._yf_symbol("^KLSE") == "^KLSE"
    assert prices_mod._yf_symbol("MAYBANK", "1155") == "1155.KL"
    with pytest.raises(ValueError):
        prices_mod._yf_symbol("MAYBANK")
