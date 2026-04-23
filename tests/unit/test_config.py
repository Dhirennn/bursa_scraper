from bursa_picker.config import FactorWeights, Settings, load_settings


def test_default_factor_weights_sum_to_one() -> None:
    FactorWeights().check_sum()


def test_settings_defaults_roundtrip() -> None:
    s = Settings()
    assert s.factors.weights.quality == 0.35
    assert s.backtest.costs_bps == 50.0
    assert s.universe.min_mcap_myr == 100_000_000


def test_load_settings_from_project_root() -> None:
    s = load_settings()
    assert s.paths.ticker_map.name == "ticker_map.txt"
    s.factors.weights.check_sum()
