from __future__ import annotations

from app.cities.base import CityConfig
from app.cities.examples import EDINBURGH_CONFIG, LIVERPOOL_CONFIG, MANCHESTER_CONFIG
from app.cities.glasgow import GLASGOW_CONFIG

CITY_CONFIGS: dict[str, CityConfig] = {
    config.slug: config
    for config in [GLASGOW_CONFIG, EDINBURGH_CONFIG, MANCHESTER_CONFIG, LIVERPOOL_CONFIG]
}


def get_city_config(slug: str) -> CityConfig:
    try:
        return CITY_CONFIGS[slug]
    except KeyError as exc:
        raise ValueError(f"Unsupported city '{slug}'.") from exc


def list_city_configs() -> list[CityConfig]:
    return list(CITY_CONFIGS.values())
