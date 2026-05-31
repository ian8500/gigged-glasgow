from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.cities.base import CityConfig


@dataclass(slots=True)
class NormalizedSourceEvent:
    title: str
    starts_at: datetime
    venue_name: str
    artist_name: str | None = None
    ends_at: datetime | None = None
    ticket_url: str | None = None
    source_url: str | None = None
    image_url: str | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    currency: str = "GBP"
    genre: str | None = None
    status: str = "scheduled"
    source_name: str = "Unknown"
    source_kind: str = "unknown"
    source_event_id: str | None = None
    source_attribution: str = "Unknown source"
    raw_payload: dict | None = None
    confidence_hints: dict[str, bool] = field(default_factory=dict)


@dataclass(slots=True)
class SourceFetchResult:
    source_name: str
    events: list[NormalizedSourceEvent] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


class SourceAdapter(Protocol):
    name: str
    kind: str

    def fetch(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        """Fetch and normalise source-specific events into the shared source event shape."""


EventSourceAdapter = SourceAdapter
