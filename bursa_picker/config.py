from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore

from pydantic import BaseModel, Field


class Paths(BaseModel):
    ticker_map: Path = Path("data/ticker_map.txt")
    cache_dir: Path = Path("cache")
    logs_dir: Path = Path("logs")
    fixtures_dir: Path = Path("data/fixtures")


class Universe(BaseModel):
    min_mcap_myr: float = 100_000_000
    min_adv_myr: float = 500_000
    min_price_myr: float = 0.20
    exclude_sectors: list[str] = Field(default_factory=list)


class FactorWeights(BaseModel):
    quality: float = 0.35
    value: float = 0.30
    dividend: float = 0.10
    momentum: float = 0.10
    size: float = 0.05
    sentiment: float = 0.10

    def as_dict(self) -> dict[str, float]:
        return self.model_dump()

    def check_sum(self, tol: float = 1e-9) -> None:
        total = sum(self.as_dict().values())
        if abs(total - 1.0) > tol:
            raise ValueError(f"Factor weights must sum to 1.0, got {total:.6f}")


class Winsorize(BaseModel):
    lower: float = 0.01
    upper: float = 0.99


class Factors(BaseModel):
    weights: FactorWeights = Field(default_factory=FactorWeights)
    winsorize: Winsorize = Field(default_factory=Winsorize)


class Backtest(BaseModel):
    start: str = "2014-01-01"
    rebalance: str = "monthly"
    top_n: int = 20
    costs_bps: float = 50.0
    min_fee_myr: float = 8.0
    benchmark: str = "^KLSE"
    risk_free: float = 0.03


class RateLimit(BaseModel):
    rps: float = 2.0
    max_retries: int = 4
    backoff_base: float = 1.5


class Cache(BaseModel):
    prices_ttl_hours: float = 18.0
    fundamentals_ttl_hours: float = 168.0


class Settings(BaseModel):
    paths: Paths = Field(default_factory=Paths)
    universe: Universe = Field(default_factory=Universe)
    factors: Factors = Field(default_factory=Factors)
    backtest: Backtest = Field(default_factory=Backtest)
    ratelimit: RateLimit = Field(default_factory=RateLimit)
    cache: Cache = Field(default_factory=Cache)


def _find_project_root() -> Path:
    here = Path(__file__).resolve().parent
    for parent in (here, *here.parents):
        if (parent / "config.toml").exists() and (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def load_settings(config_path: Path | None = None) -> Settings:
    root = _find_project_root()
    path = Path(config_path) if config_path else root / "config.toml"
    if not path.exists():
        return Settings()
    with path.open("rb") as f:
        raw = tomllib.load(f)
    settings = Settings.model_validate(raw)
    settings.factors.weights.check_sum()

    def _resolve(p: Path) -> Path:
        return p if p.is_absolute() else (root / p)

    settings.paths.ticker_map = _resolve(settings.paths.ticker_map)
    settings.paths.cache_dir = _resolve(settings.paths.cache_dir)
    settings.paths.logs_dir = _resolve(settings.paths.logs_dir)
    settings.paths.fixtures_dir = _resolve(settings.paths.fixtures_dir)
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
