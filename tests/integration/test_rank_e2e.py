"""End-to-end rank test using a pinned synthetic universe.

Asserts stable top-N ordering and that the JSON CLI output contains the
expected structure. Uses a fake yf.Ticker so the test does NOT touch the
network; fully reproducible.
"""

from __future__ import annotations

import json
from typer.testing import CliRunner

import pandas as pd
import pytest

from bursa_picker.cli.main import app
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
    real.paths.logs_dir = tmp_path / "logs"
    monkeypatch.setattr(cfg, "get_settings", lambda: real)
    monkeypatch.setattr(fm, "get_settings", lambda: real)
    monkeypatch.setattr(px, "get_settings", lambda: real)
    monkeypatch.setattr(un, "get_settings", lambda: real)
    monkeypatch.setattr(construction, "get_settings", lambda: real)
    yield


def _info(**over):
    base = {
        "marketCap": 2_000_000_000,
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
        "numberOfAnalystOpinions": 6,
        "recommendationMean": 2.0,
        "targetMeanPrice": 11.0,
        "regularMarketPrice": 10.0,
        "previousClose": 10.0,
        "sector": "Financial Services",
    }
    base.update(over)
    return base


def _hist(price=10.0, days=500):
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    vals = [price * (1 + 0.0008 * i) for i in range(days)]
    return pd.DataFrame(
        {
            "Open": vals,
            "High": [v * 1.01 for v in vals],
            "Low": [v * 0.99 for v in vals],
            "Close": vals,
            "Adj Close": vals,
            "Volume": [3_000_000] * days,
        },
        index=idx,
    )


PINNED_INFOS = {
    "STRONG": _info(
        returnOnEquity=0.25,
        profitMargins=0.30,
        priceToBook=0.7,
        trailingPE=6.5,
        dividendYield=0.055,
        payoutRatio=0.45,
    ),
    "GOOD": _info(
        returnOnEquity=0.18,
        profitMargins=0.22,
        priceToBook=1.0,
        trailingPE=9.0,
        sector="Industrials",
    ),
    "AVERAGE": _info(
        sector="Healthcare",
        returnOnEquity=0.10,
        priceToBook=1.8,
        trailingPE=15.0,
    ),
    "WEAK": _info(
        sector="Consumer",
        returnOnEquity=0.03,
        priceToBook=3.5,
        trailingPE=40.0,
        dividendYield=0.01,
    ),
    "POOR": _info(
        sector="Consumer",
        returnOnEquity=-0.05,
        profitMargins=-0.1,
        priceToBook=4.5,
        trailingPE=-20.0,
        dividendYield=0.0,
    ),
}


def _install_fake_yf(monkeypatch, tmp_path):
    (tmp_path / "ticker_map.txt").write_text(
        "\n".join(f"{t} : {i+1}" for i, t in enumerate(PINNED_INFOS)) + "\n"
    )

    class _FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol
            code_to_t = {str(i + 1): t for i, t in enumerate(PINNED_INFOS)}
            self.t = code_to_t[self.symbol.split(".")[0]]

        @property
        def info(self):
            return PINNED_INFOS[self.t]

        def history(self, **kwargs):
            return _hist()

    monkeypatch.setattr(fm.yf, "Ticker", _FakeTicker)
    monkeypatch.setattr(px.yf, "Ticker", _FakeTicker)


def test_rank_cli_json_end_to_end(tmp_path, monkeypatch):
    _install_fake_yf(monkeypatch, tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["rank", "--top", "3", "--output", "json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["universe_stats"]["universe_size"] == 5
    assert len(payload["picks"]) == 3
    # STRONG should be ranked #1
    assert payload["picks"][0]["ticker"] == "STRONG"
    # Every pick has per-factor contributions
    for p in payload["picks"]:
        assert set(p["contributions"]) >= {"quality", "value", "dividend", "momentum", "size", "sentiment"}


def test_rank_cli_narrative_text_contains_disclaimer(tmp_path, monkeypatch):
    _install_fake_yf(monkeypatch, tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["rank", "--top", "2", "--narrative"])
    assert result.exit_code == 0
    # Narrative-specific content
    assert "STRONG" in result.stdout
    assert "Why this factor mix" in result.stdout
    assert "not a forecast" in result.stdout
    # Replication-crisis citation
    assert "Hou" in result.stdout
