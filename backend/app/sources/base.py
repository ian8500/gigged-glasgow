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
    description: str | None = None
    ends_at: datetime | None = None
    ticket_url: str | None = None
    source_url: str | None = None
    image_url: str | None = None
    venue_address: str | None = None
    venue_postcode: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
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
    slug: str
    kind: str
    requires_credentials: bool
    required_settings: list[str]

    def fetch(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        """Fetch and normalise source-specific events into the shared source event shape."""

    def fetch_events(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        """Fetch source-specific events."""

    def normalize_event(self, item: dict) -> NormalizedSourceEvent | None:
        """Normalize a source-specific event payload."""

    def is_configured(self) -> bool:
        """Return whether required credentials/settings are present on the adapter."""

    def test_connection(self) -> tuple[bool, str]:
        """Run a lightweight source health check."""

    def source_status(self) -> str:
        """Return a high-level source status."""

    def source_notes(self) -> str:
        """Return source limitations and setup notes."""


EventSourceAdapter = SourceAdapter


class SourceAdapterBase:
    name = "Unknown"
    slug = "unknown"
    kind = "placeholder"
    requires_credentials = False
    required_settings: list[str] = []
    base_url: str | None = None
    terms_url: str | None = None
    limitations = ""
    official_api_available = "unknown"
    automation_allowed = "unknown"
    terms_reviewed = False
    current_mode = "placeholder"

    def fetch(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        return self.fetch_events(city, start, end)

    def fetch_events(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        return SourceFetchResult(
            source_name=self.name,
            warnings=[self.source_notes() or f"{self.name} source has no fetch implementation."],
        )

    def normalize_event(self, item: dict) -> NormalizedSourceEvent | None:
        return None

    def is_configured(self) -> bool:
        return not self.requires_credentials

    def test_connection(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, f"{self.name} credentials are not configured."
        return True, f"{self.name} is configured."

    def source_status(self) -> str:
        if self.current_mode in {"manual_only", "partner_access_required", "placeholder"}:
            return self.current_mode
        if self.requires_credentials and not self.is_configured():
            return "api_key_missing"
        return "untested"

    def source_notes(self) -> str:
        return self.limitations
