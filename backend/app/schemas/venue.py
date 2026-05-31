from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VenueCreate(BaseModel):
    city_slug: str = "glasgow"
    name: str
    slug: str
    address: str | None = None
    postcode: str | None = None
    capacity: int | None = None
    website_url: str | None = None
    event_listings_url: str | None = None
    ticketing_url: str | None = None
    instagram_handle: str | None = None
    source_discovered_from: str | None = None
    status: str = "active"
    coverage_status: str = "manual_only"
    notes: str | None = None
    is_whitelisted: bool = True


class VenueUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    address: str | None = None
    postcode: str | None = None
    capacity: int | None = None
    website_url: str | None = None
    event_listings_url: str | None = None
    ticketing_url: str | None = None
    instagram_handle: str | None = None
    source_discovered_from: str | None = None
    status: str | None = None
    coverage_status: str | None = None
    notes: str | None = None
    is_whitelisted: bool | None = None


class VenueRead(BaseModel):
    id: int
    city_id: int
    name: str
    slug: str
    address: str | None
    postcode: str | None
    capacity: int | None
    website_url: str | None
    event_listings_url: str | None
    ticketing_url: str | None
    instagram_handle: str | None
    source_discovered_from: str | None
    last_checked_at: datetime | None
    last_event_found_at: datetime | None
    status: str
    coverage_status: str
    notes: str | None
    is_whitelisted: bool

    model_config = ConfigDict(from_attributes=True)
