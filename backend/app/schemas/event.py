from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.venue import VenueRead


class EventCreate(BaseModel):
    city_slug: str = "glasgow"
    venue_slug: str
    title: str
    slug: str
    starts_at: datetime
    ticket_url: str | None = None
    genre: str | None = None


class EventAdminEdit(BaseModel):
    title: str | None = None
    starts_at: datetime | None = None
    ticket_url: str | None = None
    genre: str | None = None
    editorial_note: str | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None


class EventCsvImport(BaseModel):
    city_slug: str = "glasgow"
    csv_text: str


class EventRead(BaseModel):
    id: int
    city_id: int
    title: str
    slug: str
    starts_at: datetime
    ends_at: datetime | None
    ticket_url: str | None
    source_url: str | None
    image_url: str | None
    price_min: Decimal | None
    price_max: Decimal | None
    currency: str
    genre: str | None
    status: str
    confidence_score: float
    source_attribution: str
    needs_review: bool
    venue: VenueRead | None = None

    model_config = ConfigDict(from_attributes=True)
