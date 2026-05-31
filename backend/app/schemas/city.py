from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CityRead(BaseModel):
    id: int
    slug: str
    name: str
    country: str
    timezone: str
    default_radius_km: int
    weekly_window_start: str
    weekly_window_end: str

    model_config = ConfigDict(from_attributes=True)

