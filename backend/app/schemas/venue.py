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
    official_website_url: str | None = None
    event_listings_url: str | None = None
    ticketing_url: str | None = None
    official_events_url: str | None = None
    feed_url: str | None = None
    source_mode: str = "manual_only"
    selector_config: dict | None = None
    scraper_selector_config: dict | None = None
    scraper_status: str = "not_checked"
    scraper_notes: str | None = None
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
    official_website_url: str | None = None
    event_listings_url: str | None = None
    ticketing_url: str | None = None
    official_events_url: str | None = None
    feed_url: str | None = None
    source_mode: str | None = None
    selector_config: dict | None = None
    scraper_selector_config: dict | None = None
    scraper_status: str | None = None
    scraper_notes: str | None = None
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
    official_website_url: str | None
    event_listings_url: str | None
    ticketing_url: str | None
    official_events_url: str | None
    feed_url: str | None
    source_mode: str
    robots_allowed: bool | None
    scraper_status: str | None
    scraper_notes: str | None
    scraper_selector_config: dict | None
    last_success_at: datetime | None
    last_error: str | None
    structure_changed: bool
    confidence_score: float
    selector_config: dict | None
    instagram_handle: str | None
    source_discovered_from: str | None
    last_checked_at: datetime | None
    last_event_found_at: datetime | None
    status: str
    coverage_status: str
    notes: str | None
    is_whitelisted: bool

    model_config = ConfigDict(from_attributes=True)
