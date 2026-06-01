from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from dateutil.parser import isoparse

from app.cities.base import CityConfig
from app.core.settings import settings
from app.services.normalization import ensure_aware
from app.sources.base import NormalizedSourceEvent, SourceAdapterBase, SourceFetchResult


class ManualCsvAdapter(SourceAdapterBase):
    name = "Manual CSV import"
    slug = "manual-csv"
    kind = "csv"
    current_mode = "manual_only"
    official_api_available = "no"
    automation_allowed = "yes"
    limitations = "Manual CSV import; only as complete as supplied rows."

    def __init__(self, csv_path: str | None = None) -> None:
        self.csv_path = csv_path or settings.manual_events_csv_path

    def is_configured(self) -> bool:
        return bool(self.csv_path)

    def fetch_events(self, city: CityConfig, start: datetime, end: datetime) -> SourceFetchResult:
        if not self.csv_path:
            return SourceFetchResult(
                source_name=self.name,
                warnings=["MANUAL_EVENTS_CSV_PATH is not set; manual CSV import skipped."],
            )

        path = Path(self.csv_path)
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.exists():
            return SourceFetchResult(
                source_name=self.name,
                warnings=[f"Manual CSV file not found at {path}; import skipped."],
            )

        events: list[NormalizedSourceEvent] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                event = self._normalise_row(row)
                if event:
                    event.starts_at = ensure_aware(event.starts_at)
                if event and start <= event.starts_at <= end:
                    events.append(event)

        return SourceFetchResult(source_name=self.name, events=events)

    def _normalise_row(self, row: dict[str, str]) -> NormalizedSourceEvent | None:
        title = row.get("title")
        venue_name = row.get("venue_name")
        starts_at = row.get("starts_at")
        if not title or not venue_name or not starts_at:
            return None

        return NormalizedSourceEvent(
            title=title,
            artist_name=row.get("artist_name") or title,
            venue_name=venue_name,
            starts_at=isoparse(starts_at),
            ticket_url=row.get("ticket_url") or None,
            source_url=row.get("source_url") or row.get("ticket_url") or None,
            image_url=row.get("image_url") or None,
            price_min=_decimal_from_row(row.get("price_min")),
            price_max=_decimal_from_row(row.get("price_max")),
            currency=row.get("currency") or "GBP",
            genre=row.get("genre") or None,
            source_name=self.name,
            source_kind=self.kind,
            source_event_id=row.get("source_event_id") or None,
            source_attribution=row.get("source_attribution") or "Manual CSV import",
            raw_payload=row,
            confidence_hints={
                "has_artist": bool(row.get("artist_name")),
                "has_venue": True,
                "has_datetime": True,
                "has_ticket_url": bool(row.get("ticket_url")),
                "has_source_id": bool(row.get("source_event_id")),
            },
        )

    def normalize_event(self, item: dict) -> NormalizedSourceEvent | None:
        return self._normalise_row({key: str(value) for key, value in item.items()})


def _decimal_from_row(value: str | None) -> Decimal | None:
    return Decimal(value) if value else None
