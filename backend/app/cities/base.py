from __future__ import annotations

from pydantic import BaseModel, Field


class CityCoordinates(BaseModel):
    latitude: float
    longitude: float


class CityColours(BaseModel):
    ink: str = "#0e0e10"
    paper: str = "#f3efe4"
    primary: str
    secondary: str
    accent: str


class PostingSchedule(BaseModel):
    weekly_roundup_day: str = "thursday"
    weekly_roundup_time: str = "18:00"
    tonight_post_time: str = "12:00"
    weekend_post_day: str = "friday"
    weekend_post_time: str = "11:00"


class VenueTemplate(BaseModel):
    name: str
    slug: str
    address: str | None = None
    postcode: str | None = None
    capacity: int | None = None
    website_url: str | None = None
    instagram_handle: str | None = None


class CityConfig(BaseModel):
    slug: str
    city_name: str
    brand_name: str
    handle: str
    tagline: str
    country: str
    timezone: str
    colours: CityColours
    venues: list[VenueTemplate]
    coordinates: CityCoordinates
    radius_km: int = Field(ge=1)
    hashtags: list[str]
    voice_notes: list[str]
    default_posting_schedule: PostingSchedule
    venue_whitelist: list[str]
    genre_filters: list[str]
    minimum_date_range_days: int = Field(default=14, ge=1)
    weekly_roundup_start: str = "friday"
    weekly_roundup_end: str = "thursday"

    @property
    def name(self) -> str:
        return self.city_name

    @property
    def search_radius_km(self) -> int:
        return self.radius_km
